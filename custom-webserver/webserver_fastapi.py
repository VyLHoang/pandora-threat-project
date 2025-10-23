#!/usr/bin/env python3
"""
Pandora Honeypot Webserver - FastAPI (Simplified)
==================================================
Chạy trên port nội bộ 8443 (HTTP, không SSL)
Nginx sẽ xử lý SSL và proxy request đến đây

Chức năng:
1. Serve Vue.js Static Files (SPA)
2. Honeypot Logging (ghi lại MỌI request)
3. Suspicious Request Detection

LƯU Ý: Script này KHÔNG proxy API nữa (Nginx đã xử lý)
"""

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
import sys
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import jwt

# ========================================================================
# Import Elasticsearch Service
# ========================================================================
backend_admin_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend-admin'))
if backend_admin_dir not in sys.path:
    sys.path.insert(0, backend_admin_dir)

try:
    from services.elasticsearch_service import elasticsearch_service
    ELASTICSEARCH_AVAILABLE = True
except ImportError:
    ELASTICSEARCH_AVAILABLE = False
    print("[WARNING] Elasticsearch service not available")

# ========================================================================
# Configuration
# ========================================================================
class Config:
    """Webserver Configuration"""
    HOST = "127.0.0.1"
    PORT = 8443
    ADMIN_BACKEND_URL = "http://127.0.0.1:8002"
    
    @staticmethod
    def get_frontend_dir() -> Path:
        """Tìm thư mục frontend (dist)"""
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
    print("[PANDORA HONEYPOT] FastAPI Webserver")
    print("="*70)
    print(f"[OK] Host: {config.HOST}:{config.PORT}")
    print(f"[OK] Protocol: HTTP (Nginx xử lý SSL)")
    print(f"[OK] Frontend: {config.get_frontend_dir()}")
    print("="*70)
    print("[FEATURES]")
    print("  ✓ Vue.js SPA Serving")
    print("  ✓ Honeypot Logging (MỌI request)")
    print("  ✓ Suspicious Detection")
    print("  ✓ Real IP Tracking")
    print("="*70)
    yield
    print("\n[SHUTDOWN] Honeypot stopped")

# ========================================================================
# FastAPI App
# ========================================================================
app = FastAPI(
    title="Pandora Honeypot",
    version="2.0.0",
    description="Production honeypot với FastAPI",
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
    """Lấy IP thật từ Nginx headers"""
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    return request.client.host if request.client else "unknown"

def extract_user_from_token(request: Request) -> Optional[Dict[str, Any]]:
    """Extract user info từ JWT token"""
    try:
        access_token = request.cookies.get("access_token")
        if not access_token:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                access_token = auth_header.split(" ")[1]
        
        if not access_token:
            return None
        
        decoded = jwt.decode(access_token, options={"verify_signature": False})
        return {
            "user_id": decoded.get("sub"),
            "is_authenticated": True
        }
    except:
        return None

def calculate_suspicious_score(request: Request, path: str, body: Optional[str] = None) -> tuple[int, list[str]]:
    """Tính điểm nghi ngờ"""
    score = 0
    reasons = []
    path_lower = path.lower()
    
    # SQL Injection
    sql_patterns = ["'", '"', ";", "union", "select", "drop", "insert", "update", "delete", "--"]
    for pattern in sql_patterns:
        if pattern in path_lower:
            score += 20
            reasons.append(f"SQL injection: {pattern}")
            break
    
    # Path Traversal
    if "../" in path_lower or "..\\" in path_lower:
        score += 30
        reasons.append("Path traversal")
    
    # XSS
    xss_patterns = ["<script", "javascript:", "onerror=", "onload="]
    for pattern in xss_patterns:
        if pattern in path_lower:
            score += 25
            reasons.append(f"XSS: {pattern}")
            break
    
    # Suspicious User Agent
    user_agent = request.headers.get("User-Agent", "").lower()
    suspicious_uas = ["sqlmap", "nmap", "nessus", "openvas", "nikto", "w3af", "burp", "metasploit"]
    for ua in suspicious_uas:
        if ua in user_agent:
            score += 30
            reasons.append(f"Suspicious UA: {ua}")
            break
    
    # Exploit paths
    exploit_paths = ["/admin", "/phpmyadmin", "/.env", "/config", "/wp-admin", "/.git", "/api/"]
    for exp_path in exploit_paths:
        if exp_path in path_lower:
            score += 15
            reasons.append(f"Exploit path: {exp_path}")
            break
    
    # Body analysis
    if body:
        body_lower = body.lower()
        if any(p in body_lower for p in sql_patterns + xss_patterns):
            score += 20
            reasons.append("Suspicious payload")
    
    return min(100, score), reasons

async def log_honeypot_activity(
    request: Request,
    method: str,
    path: str,
    headers: Dict[str, str],
    body: Optional[str] = None,
    response_status: Optional[int] = None,
    response_size: Optional[int] = None
):
    """Log activity (async, non-blocking)"""
    try:
        user_info = extract_user_from_token(request)
        user_id = user_info.get("user_id") if user_info else None
        is_authenticated = user_info.get("is_authenticated", False) if user_info else False
        
        activity_type = "page_view"
        if method != "GET":
            activity_type = "api_call"
        if "/api/" in path:
            activity_type = "api_probe"
        
        suspicious_score, suspicious_reasons = calculate_suspicious_score(request, path, body)
        client_ip = get_client_ip(request)
        
        log_data = {
            "user_id": int(user_id) if user_id else None,
            "is_authenticated": is_authenticated,
            "session_id": request.cookies.get("session_id"),
            "request_method": method,
            "request_path": path,
            "request_headers": dict(headers),
            "request_body": body[:5000] if body else None,
            "response_status": response_status,
            "response_size": response_size,
            "activity_type": activity_type,
            "suspicious_score": suspicious_score,
            "suspicious_reasons": suspicious_reasons,
            "client_ip": client_ip,
            "user_agent": headers.get("user-agent", "")
        }
        
        # Send to Admin Backend (async)
        def send_log():
            try:
                import requests
                requests.post(
                    f"{config.ADMIN_BACKEND_URL}/honeypot/log",
                    json=log_data,
                    timeout=5
                )
            except Exception as e:
                print(f"[HONEYPOT] Failed to send log: {e}")
        
        threading.Thread(target=send_log, daemon=True).start()
        
        # Elasticsearch
        if ELASTICSEARCH_AVAILABLE:
            def send_to_es():
                try:
                    es_data = {**log_data, "timestamp": datetime.now().isoformat()}
                    elasticsearch_service.log_honeypot_activity(es_data)
                except:
                    pass
            threading.Thread(target=send_to_es, daemon=True).start()
        
        # Console log cho suspicious
        if suspicious_score > 50:
            print(f"[HONEYPOT] 🚨 Suspicious: {client_ip} | {method} {path} | Score: {suspicious_score}")
            print(f"  Reasons: {', '.join(suspicious_reasons)}")
    
    except Exception as e:
        print(f"[HONEYPOT ERROR] {e}")

# ========================================================================
# Middleware: Log All Requests
# ========================================================================
@app.middleware("http")
async def log_all_requests(request: Request, call_next):
    """Log MỌI request (honeypot core)"""
    start_time = time.time()
    
    # Read body
    body = None
    if request.method in ["POST", "PUT", "PATCH"]:
        try:
            body_bytes = await request.body()
            body = body_bytes.decode("utf-8", errors="ignore")
        except:
            body = None
    
    # Process
    response = await call_next(request)
    process_time = time.time() - start_time
    
    # Log
    try:
        response_size = int(response.headers.get("content-length", 0))
        await log_honeypot_activity(
            request=request,
            method=request.method,
            path=str(request.url.path),
            headers=dict(request.headers),
            body=body,
            response_status=response.status_code,
            response_size=response_size
        )
    except Exception as e:
        print(f"[MIDDLEWARE ERROR] {e}")
    
    # Headers
    response.headers["X-Process-Time"] = f"{process_time:.3f}s"
    response.headers["X-Served-By"] = "Pandora-Honeypot"
    
    # Console
    client_ip = get_client_ip(request)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {client_ip} | {request.method} {request.url.path} -> {response.status_code} ({process_time:.3f}s)")
    
    return response

# ========================================================================
# API Endpoints (Local)
# ========================================================================
@app.get("/api/status")
async def status():
    """Server status"""
    return {
        "status": "online",
        "server": "Pandora Honeypot",
        "version": "2.0.0",
        "port": config.PORT,
        "protocol": "HTTP",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/health")
async def health():
    """Health check"""
    return {"health": "ok", "port": config.PORT}

# ========================================================================
# Static Files: Vue.js Frontend
# ========================================================================
frontend_dir = config.get_frontend_dir()

if (frontend_dir / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dir / "assets")), name="assets")

@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    """
    Serve Vue.js SPA
    - Nếu file tồn tại -> serve file
    - Nếu không -> serve index.html (Vue Router)
    """
    file_path = frontend_dir / full_path
    
    if file_path.is_file():
        return FileResponse(file_path)
    
    index_path = frontend_dir / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    else:
        return HTMLResponse(
            content="<h1>Pandora Platform</h1><p>Frontend not built. Run: cd frontend && npm run build</p>",
            status_code=404
        )

# ========================================================================
# Main
# ========================================================================
if __name__ == "__main__":
    import uvicorn
    
    print("[STARTUP] Starting Pandora Honeypot...")
    
    uvicorn.run(
        "webserver_fastapi:app",
        host=config.HOST,
        port=config.PORT,
        log_level="info",
        access_log=True
    )
