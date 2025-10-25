#!/usr/bin/env python3
"""
Pandora Honeypot Server - Production Ready
===========================================
Fake website để dụ hacker + Real Vue.js app ẩn sau

Architecture:
- Fake paths (nhiều): /admin, /phpmyadmin, /wp-admin, /.env, etc → Fake HTML
- Real paths (ẩn): /app/*, /api/user/* → Vue.js + Backend proxy
- All logs → Central Monitor Server (remote)
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
import sys
import time
import httpx
from datetime import datetime
from pathlib import Path
from typing import Optional
import jwt

# ========================================================================
# Configuration
# ========================================================================
class Config:
    HOST = "127.0.0.1"
    PORT = 8443
    
    # Central Monitor Server URL (where all logs go)
    CENTRAL_MONITOR_URL = os.getenv("CENTRAL_MONITOR_URL", "https://central-monitor.local")
    CENTRAL_MONITOR_API_KEY = os.getenv("CENTRAL_MONITOR_API_KEY", "your-secret-key")
    
    # No backend user API on honeypot server (pure honeypot)

config = Config()

# ========================================================================
# Lifespan
# ========================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("="*70)
    print("[HONEYPOT SERVER] Production Ready")
    print("="*70)
    print(f"[OK] Host: {config.HOST}:{config.PORT}")
    print(f"[OK] Mode: Pure Honeypot")
    print(f"[OK] Central Monitor: {config.CENTRAL_MONITOR_URL}")
    print("="*70)
    print("[FEATURES]")
    print("  Fake paths: /admin, /phpmyadmin, /wp-admin, /.env, /api/v1/*, etc")
    print("  Pure honeypot: NO real user app")
    print("  All logs → Central Monitor")
    print("="*70)
    yield
    print("\n[SHUTDOWN] Honeypot stopped")

# ========================================================================
# FastAPI App
# ========================================================================
app = FastAPI(
    title="Pandora Honeypot",
    version="3.0.0",
    description="Fake + Real hybrid honeypot",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========================================================================
# Helper Functions
# ========================================================================
def get_client_ip(request: Request) -> str:
    """Get real IP from Nginx headers"""
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

async def log_to_central_monitor(
    request: Request,
    path: str,
    response_status: int,
    is_fake: bool = False
):
    """Send log to Central Monitor Server"""
    try:
        client_ip = get_client_ip(request)
        
        # Calculate suspicious score based on path and request
        suspicious_score = calculate_suspicious_score(path, request, is_fake)
        activity_type = detect_activity_type(path, request, is_fake)
        
        # Read request body for POST requests
        request_body = None
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body_bytes = await request.body()
                request_body = body_bytes.decode('utf-8')[:1000]  # Limit size
            except:
                request_body = None
        
        log_data = {
            "client_ip": client_ip,
            "user_agent": request.headers.get("User-Agent", ""),
            "request_method": request.method,
            "request_path": path,
            "request_headers": dict(request.headers),
            "request_body": request_body,
            "response_status": response_status,
            "is_fake_path": is_fake,
            "suspicious_score": suspicious_score,
            "activity_type": activity_type,
            "timestamp": datetime.now().isoformat()
        }
        
        async with httpx.AsyncClient(verify=False) as client:
            await client.post(
                f"{config.CENTRAL_MONITOR_URL}/api/admin/honeypot/log",
                json=log_data,
                headers={"X-API-Key": config.CENTRAL_MONITOR_API_KEY},
                timeout=5
            )
            
        print(f"[HONEYPOT] {client_ip} → {path} (score: {suspicious_score}, type: {activity_type})")
    except Exception as e:
        print(f"[ERROR] Failed to log to Central Monitor: {e}")

def calculate_suspicious_score(path: str, request: Request, is_fake: bool) -> int:
    """Calculate suspicious score based on request characteristics"""
    score = 0
    path_lower = path.lower()
    
    # Base score for fake paths
    if is_fake:
        score += 50
    
    # High-risk paths
    high_risk_paths = ['/admin', '/phpmyadmin', '/wp-admin', '/.env', '/config.php', '/.git', '/.htaccess']
    for risk_path in high_risk_paths:
        if risk_path in path_lower:
            score += 30
            break
    
    # API endpoints
    if '/api/' in path_lower:
        score += 20
    
    # File extensions
    dangerous_extensions = ['.php', '.asp', '.jsp', '.sql', '.bak', '.backup']
    for ext in dangerous_extensions:
        if path_lower.endswith(ext):
            score += 25
            break
    
    # User agent analysis
    user_agent = request.headers.get("User-Agent", "").lower()
    suspicious_agents = ['sqlmap', 'nmap', 'nessus', 'nikto', 'burp', 'w3af', 'curl', 'wget']
    for agent in suspicious_agents:
        if agent in user_agent:
            score += 40
            break
    
    # Request method
    if request.method == "POST" and is_fake:
        score += 15
    
    # Ensure score is between 0-100
    return min(100, max(0, score))

def detect_activity_type(path: str, request: Request, is_fake: bool) -> str:
    """Detect activity type based on request"""
    path_lower = path.lower()
    
    if not is_fake:
        return "legitimate_access"
    
    # Admin panel attempts
    if any(admin_path in path_lower for admin_path in ['/admin', '/administrator', '/cpanel']):
        return "admin_probe"
    
    # Database attempts
    if any(db_path in path_lower for db_path in ['/phpmyadmin', '/pma', '/mysql', '/database']):
        return "database_probe"
    
    # WordPress attempts
    if any(wp_path in path_lower for wp_path in ['/wp-admin', '/wp-login', '/wp-content']):
        return "wordpress_probe"
    
    # File access attempts
    if any(file_path in path_lower for file_path in ['/.env', '/config.php', '/.htaccess', '/.git']):
        return "file_access_probe"
    
    # API attempts
    if '/api/' in path_lower:
        return "api_probe"
    
    # Generic fake path
    return "fake_probe"

# ========================================================================
# Middleware: Log All Requests
# ========================================================================
@app.middleware("http")
async def log_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    client_ip = get_client_ip(request)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {client_ip} | {request.method} {request.url.path} -> {response.status_code} ({process_time:.3f}s)")
    
    return response

# ========================================================================
# FAKE PATHS (Đứng trước - để dụ hacker)
# ========================================================================

@app.get("/admin")
@app.post("/admin")
async def fake_admin_panel(request: Request):
    """Fake admin login page"""
    await log_to_central_monitor(request, "/admin", 200, is_fake=True)
    
    return HTMLResponse("""
<!DOCTYPE html>
<html>
<head>
    <title>Admin Panel - Login</title>
    <style>
        body { font-family: Arial; background: #f0f0f0; padding: 50px; }
        .login-box { max-width: 400px; margin: 0 auto; background: white; padding: 30px; border: 1px solid #ccc; }
        input { width: 100%; padding: 10px; margin: 10px 0; }
        button { width: 100%; padding: 10px; background: #007bff; color: white; border: none; cursor: pointer; }
    </style>
</head>
<body>
    <div class="login-box">
        <h2>Admin Panel</h2>
        <form method="post">
            <input type="text" name="username" placeholder="Username" required>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit">Login</button>
        </form>
        <p style="color: #666; font-size: 12px;">Version 2.4.1 | &copy; 2024</p>
    </div>
</body>
</html>
    """)

@app.get("/phpmyadmin")
@app.get("/phpMyAdmin")
@app.get("/pma")
async def fake_phpmyadmin(request: Request):
    """Fake phpMyAdmin"""
    await log_to_central_monitor(request, "/phpmyadmin", 200, is_fake=True)
    
    return HTMLResponse("""
<!DOCTYPE html>
<html>
<head>
    <title>phpMyAdmin</title>
    <style>
        body { font-family: Arial; margin: 0; }
        .header { background: #465457; color: white; padding: 10px; }
        .content { padding: 20px; }
        input { padding: 5px; margin: 5px 0; }
        button { padding: 5px 15px; background: #0099cc; color: white; border: none; }
    </style>
</head>
<body>
    <div class="header">
        <h1>phpMyAdmin 4.9.5</h1>
    </div>
    <div class="content">
        <h3>Database server</h3>
        <form>
            <input type="text" name="pma_username" placeholder="Username" /><br>
            <input type="password" name="pma_password" placeholder="Password" /><br>
            <button type="submit">Go</button>
        </form>
        <p style="color: #666; font-size: 11px;">MySQL 5.7.34 - localhost via TCP/IP</p>
    </div>
</body>
</html>
    """)

@app.get("/wp-admin")
@app.get("/wp-admin/")
@app.get("/wp-login.php")
async def fake_wordpress(request: Request):
    """Fake WordPress admin"""
    await log_to_central_monitor(request, "/wp-admin", 200, is_fake=True)
    
    return HTMLResponse("""
<!DOCTYPE html>
<html>
<head>
    <title>Log In ‹ My Site — WordPress</title>
    <style>
        body { background: #f1f1f1; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto; }
        #loginform { background: white; padding: 26px 24px; margin: 100px auto; max-width: 320px; box-shadow: 0 1px 3px rgba(0,0,0,.13); }
        input { width: 100%; padding: 8px; margin: 5px 0; border: 1px solid #ddd; }
        .button { background: #2271b1; color: white; border: none; padding: 10px; cursor: pointer; width: 100%; }
    </style>
</head>
<body>
    <form id="loginform">
        <h1 style="text-align: center;">My Site</h1>
        <p><label>Username or Email Address<br><input type="text" name="log" /></label></p>
        <p><label>Password<br><input type="password" name="pwd" /></label></p>
        <p><button type="submit" class="button">Log In</button></p>
        <p style="font-size: 13px;"><a href="#">Lost your password?</a></p>
    </form>
</body>
</html>
    """)

@app.get("/.env")
async def fake_env_file(request: Request):
    """Fake .env file"""
    await log_to_central_monitor(request, "/.env", 200, is_fake=True)
    
    return PlainTextResponse("""
APP_NAME=ProductionApp
APP_ENV=production
APP_KEY=base64:fake_key_here_12345678901234567890
APP_DEBUG=false
APP_URL=http://localhost

DB_CONNECTION=mysql
DB_HOST=127.0.0.1
DB_PORT=3306
DB_DATABASE=production_db
DB_USERNAME=root
DB_PASSWORD=fake_password_123

CACHE_DRIVER=redis
QUEUE_CONNECTION=redis
SESSION_DRIVER=redis
""")

@app.get("/config.php")
@app.get("/configuration.php")
async def fake_config(request: Request):
    """Fake config file"""
    await log_to_central_monitor(request, "/config.php", 200, is_fake=True)
    
    return PlainTextResponse("""
<?php
define('DB_HOST', 'localhost');
define('DB_USER', 'admin');
define('DB_PASS', 'fake_pass_123');
define('DB_NAME', 'production');
define('SECRET_KEY', 'fake_secret_key_12345');
?>
""")

@app.get("/administrator")
@app.get("/cpanel")
@app.get("/backup")
@app.get("/backup.sql")
@app.get("/database.sql")
@app.get("/wp-content/uploads/")
@app.get("/wp-includes/")
@app.get("/wp-config.php")
@app.get("/robots.txt")
@app.get("/sitemap.xml")
@app.get("/.git/")
@app.get("/.svn/")
@app.get("/.htaccess")
@app.get("/web.config")
@app.get("/crossdomain.xml")
@app.get("/clientaccesspolicy.xml")
async def fake_generic_paths(request: Request):
    """Generic fake paths - lure various attack vectors"""
    await log_to_central_monitor(request, request.url.path, 404, is_fake=True)
    return HTMLResponse("<h1>404 Not Found</h1><p>The requested resource was not found on this server.</p>", status_code=404)

@app.get("/login.php")
@app.get("/admin.php")
@app.get("/index.php")
@app.get("/test.php")
async def fake_php_files(request: Request):
    """Fake PHP files"""
    await log_to_central_monitor(request, request.url.path, 200, is_fake=True)
    return HTMLResponse("""
<!DOCTYPE html>
<html>
<head>
    <title>PHP Error</title>
    <style>
        body { font-family: Arial; background: #f0f0f0; padding: 50px; }
        .error { background: white; padding: 20px; border: 1px solid #ccc; }
    </style>
</head>
<body>
    <div class="error">
        <h2>PHP Fatal Error</h2>
        <p>Call to undefined function mysql_connect() in /var/www/html/index.php on line 15</p>
        <p>Please check your database configuration.</p>
    </div>
</body>
</html>
    """)

@app.get("/api/")
@app.get("/api/v1/")
@app.get("/api/v2/")
async def fake_api_root(request: Request):
    """Fake API root endpoints"""
    await log_to_central_monitor(request, request.url.path, 200, is_fake=True)
    return JSONResponse({
        "version": "1.0.0",
        "status": "active",
        "endpoints": [
            "/api/v1/auth/login",
            "/api/v1/users",
            "/api/v1/config",
            "/api/v1/database"
        ]
    })

# ========================================================================
# ROOT PATH (Fake landing page)
# ========================================================================

@app.get("/")
async def fake_homepage(request: Request):
    """Fake homepage - lure attackers"""
    await log_to_central_monitor(request, "/", 200, is_fake=True)
    
    return HTMLResponse("""
<!DOCTYPE html>
<html>
<head>
    <title>Welcome to Our Server</title>
    <style>
        body { font-family: Arial; background: #f0f0f0; padding: 50px; text-align: center; }
        .container { max-width: 600px; margin: 0 auto; background: white; padding: 30px; border: 1px solid #ccc; }
        h1 { color: #333; }
        p { color: #666; line-height: 1.6; }
        .links { margin: 20px 0; }
        .links a { display: inline-block; margin: 10px; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; }
        .links a:hover { background: #0056b3; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Welcome to Our Server</h1>
        <p>This is a production server running various services.</p>
        <p>Please use the links below to access different areas:</p>
        <div class="links">
            <a href="/admin">Admin Panel</a>
            <a href="/phpmyadmin">Database</a>
            <a href="/wp-admin">WordPress</a>
        </div>
        <p style="font-size: 12px; color: #999;">Server v2.4.1 | Last updated: 2024-10-23</p>
    </div>
</body>
</html>
    """)

# ========================================================================
# FAKE API ENDPOINTS (Lure attackers)
# ========================================================================

@app.get("/api/v1/auth/login")
@app.post("/api/v1/auth/login")
async def fake_api_login(request: Request):
    """Fake API login endpoint"""
    await log_to_central_monitor(request, "/api/v1/auth/login", 200, is_fake=True)
    
    return JSONResponse({
        "success": True,
        "message": "Login successful",
        "token": "fake_jwt_token_12345",
        "user": {
            "id": 1,
            "email": "admin@example.com",
            "role": "admin"
        }
    })

@app.get("/api/v1/users")
async def fake_api_users(request: Request):
    """Fake API users endpoint"""
    await log_to_central_monitor(request, "/api/v1/users", 200, is_fake=True)
    
    return JSONResponse({
        "users": [
            {"id": 1, "email": "admin@example.com", "role": "admin"},
            {"id": 2, "email": "user@example.com", "role": "user"}
        ]
    })

@app.get("/api/v1/config")
async def fake_api_config(request: Request):
    """Fake API config endpoint"""
    await log_to_central_monitor(request, "/api/v1/config", 200, is_fake=True)
    
    return JSONResponse({
        "database": {
            "host": "localhost",
            "port": 3306,
            "username": "root",
            "password": "admin123"
        },
        "redis": {
            "host": "localhost",
            "port": 6379,
            "password": "redis123"
        }
    })

# ========================================================================
# Health Check
# ========================================================================
@app.get("/health")
async def health():
    return {"status": "ok", "server": "honeypot", "version": "3.0.0"}

# ========================================================================
# Main
# ========================================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "honeypot_server:app",
        host=config.HOST,
        port=config.PORT,
        log_level="info"
    )

