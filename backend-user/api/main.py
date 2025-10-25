"""
User Backend API - Port 8000
Handles user-facing features: Authentication, Scanning, History
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import sys
import os
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from database.database import init_db, engine
from api.routes import auth, scanner, history, user


# Lifespan context manager (thay thế on_event)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("="*70)
    print("[USER BACKEND] Starting Pandora User API")
    print("="*70)
    print(f"[OK] Port: 8000")
    print(f"[OK] Environment: {settings.APP_ENV}")
    print(f"[OK] Debug: {settings.DEBUG}")
    print("="*70)
    print("[INFO] Features:")
    print("  - User Authentication (Login/Register)")
    print("  - VirusTotal Scanning (IP/Hash)")
    print("  - Scan History")
    print("  - User Profile Management")
    print("="*70)
    print("[INFO] Initializing database...")
    
    try:
        init_db()
        print("[OK] Database initialized successfully")
    except Exception as e:
        print(f"[ERROR] Database initialization failed: {e}")
    
    print("="*70)
    
    yield  # Server is running
    
    # Shutdown
    print("[INFO] Shutting down User Backend API...")


# Create FastAPI app with lifespan
app = FastAPI(
    title=f"{settings.APP_NAME} - User API",
    version=settings.APP_VERSION,
    description="User-facing API for threat intelligence platform",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.DEBUG else "An error occurred"
        }
    )

# Suspicious activity logging middleware
@app.middleware("http")
async def log_suspicious_activities(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    # Only log suspicious activities (not all requests)
    if is_suspicious_activity(request, response):
        try:
            client_ip = request.headers.get("X-Real-IP", request.client.host)
            log_data = {
                "client_ip": client_ip,
                "user_agent": request.headers.get("User-Agent", ""),
                "request_method": request.method,
                "request_path": request.url.path,
                "request_headers": dict(request.headers),
                "response_status": response.status_code,
                "is_fake_path": False,
                "activity_type": "suspicious_user_activity",
                "timestamp": datetime.now().isoformat()
            }
            
            # Send to Central Monitor
            import httpx
            async with httpx.AsyncClient(verify=False) as client:
                await client.post(
                    settings.CENTRAL_MONITOR_URL,
                    json=log_data,
                    headers={"X-API-Key": settings.CENTRAL_MONITOR_API_KEY},
                    timeout=5
                )
        except Exception as e:
            print(f"[ERROR] Failed to log suspicious activity: {e}")
    
    return response

def is_suspicious_activity(request: Request, response) -> bool:
    """Check if request/response indicates suspicious activity"""
    # Failed authentication attempts
    if response.status_code == 401 or response.status_code == 403:
        return True
    
    # Rate limiting violations
    if response.status_code == 429:
        return True
    
    # Unusual user agents
    user_agent = request.headers.get("User-Agent", "").lower()
    suspicious_agents = ['sqlmap', 'nmap', 'nessus', 'nikto', 'burp', 'w3af']
    if any(agent in user_agent for agent in suspicious_agents):
        return True
    
    # Suspicious paths
    path = request.url.path.lower()
    suspicious_paths = ['/admin', '/phpmyadmin', '/wp-admin', '/.env', '/config.php']
    if any(susp_path in path for susp_path in suspicious_paths):
        return True
    
    # Multiple failed requests from same IP (would need session tracking)
    # For now, just check for obvious suspicious patterns
    
    return False

# Health check
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "user-api",
        "version": settings.APP_VERSION,
        "database": "connected"
    }

# Root endpoint
@app.get("/")
async def root():
    return {
        "service": "Pandora User API",
        "version": settings.APP_VERSION,
        "endpoints": {
            "auth": "/api/v1/auth",
            "scanner": "/api/v1/scan",
            "history": "/api/v1/history",
            "user": "/api/v1/user"
        }
    }

# Register routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(scanner.router, prefix="/api/v1/scan", tags=["Scanner"])
app.include_router(history.router, prefix="/api/v1/history", tags=["History"])
app.include_router(user.router, prefix="/api/v1/user", tags=["User"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="127.0.0.1",  # Localhost only (Nginx proxy)
        port=8001,  # New port for User Backend
        reload=settings.DEBUG
    )

