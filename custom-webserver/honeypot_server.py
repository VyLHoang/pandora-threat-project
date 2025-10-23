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
    
    # Backend User API (local)
    USER_BACKEND_URL = "http://127.0.0.1:8001"
    
    @staticmethod
    def get_frontend_dir() -> Path:
        base_dir = Path(__file__).parent.parent
        dist_path = base_dir / "frontend" / "dist"
        if dist_path.exists():
            return dist_path
        return Path.cwd()

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
    print(f"[OK] Mode: Fake + Real hybrid")
    print(f"[OK] Central Monitor: {config.CENTRAL_MONITOR_URL}")
    print("="*70)
    print("[FEATURES]")
    print("  Fake paths: /admin, /phpmyadmin, /wp-admin, /.env, etc")
    print("  Real paths: /app/*, /api/user/*")
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
        log_data = {
            "client_ip": client_ip,
            "user_agent": request.headers.get("User-Agent", ""),
            "request_method": request.method,
            "request_path": path,
            "request_headers": dict(request.headers),
            "response_status": response_status,
            "is_fake_path": is_fake,
            "suspicious_score": 80 if is_fake else 10,
            "activity_type": "fake_probe" if is_fake else "legitimate_access",
            "timestamp": datetime.now().isoformat()
        }
        
        async with httpx.AsyncClient(verify=False) as client:
            await client.post(
                f"{config.CENTRAL_MONITOR_URL}/api/admin/honeypot/log",
                json=log_data,
                headers={"X-API-Key": config.CENTRAL_MONITOR_API_KEY},
                timeout=5
            )
            
        if is_fake:
            print(f"[FAKE] {client_ip} → {path} (logged to Central)")
    except Exception as e:
        print(f"[ERROR] Failed to log to Central Monitor: {e}")

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
async def fake_generic_paths(request: Request):
    """Generic fake paths"""
    await log_to_central_monitor(request, request.url.path, 404, is_fake=True)
    return HTMLResponse("<h1>404 Not Found</h1><p>The requested resource was not found on this server.</p>", status_code=404)

# ========================================================================
# REAL PATHS (Ẩn sau - Vue.js App)
# ========================================================================

frontend_dir = config.get_frontend_dir()

# Mount static assets
if (frontend_dir / "assets").exists():
    app.mount("/app/assets", StaticFiles(directory=str(frontend_dir / "assets")), name="assets")

@app.get("/app/{full_path:path}")
async def serve_real_app(request: Request, full_path: str):
    """Serve real Vue.js app (ẩn ở /app/*)"""
    await log_to_central_monitor(request, f"/app/{full_path}", 200, is_fake=False)
    
    file_path = frontend_dir / full_path
    if file_path.is_file():
        return FileResponse(file_path)
    
    # SPA: serve index.html
    index_path = frontend_dir / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    else:
        return HTMLResponse("<h1>Frontend not built</h1><p>Run: cd frontend && npm run build</p>", status_code=404)

# Root redirect to /app/
@app.get("/")
async def root_redirect(request: Request):
    """Redirect root to real app"""
    await log_to_central_monitor(request, "/", 302, is_fake=False)
    return HTMLResponse('<meta http-equiv="refresh" content="0; url=/app/">', status_code=302)

# ========================================================================
# API PROXY (to Backend-user)
# ========================================================================
@app.api_route("/api/user/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
async def proxy_to_backend(request: Request, path: str):
    """Proxy API requests to Backend-user"""
    await log_to_central_monitor(request, f"/api/user/{path}", 0, is_fake=False)
    
    try:
        # Read body
        body = None
        if request.method in ["POST", "PUT", "PATCH"]:
            body = await request.body()
        
        # Build backend URL
        backend_url = f"{config.USER_BACKEND_URL}/api/v1/{path}"
        
        # Proxy request
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=request.method,
                url=backend_url,
                headers=dict(request.headers),
                content=body,
                timeout=30
            )
            
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
    except Exception as e:
        print(f"[ERROR] Proxy failed: {e}")
        return JSONResponse({"error": "Backend unavailable"}, status_code=502)

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

