"""
Admin Backend API - Port 9000
Handles admin-only features: Honeypot Monitoring, Attack Logs
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import sys
import os
import time

# IMPORTANT: Insert backend-admin to the FRONT of sys.path to avoid conflicts with backend-user
backend_admin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_admin_dir in sys.path:
    sys.path.remove(backend_admin_dir)
sys.path.insert(0, backend_admin_dir)

from config import settings
from database.database import init_db, engine
from api.routes import honeypot, attacks, user_monitoring


# Lifespan context manager (thay thế on_event)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("="*70)
    print("[ADMIN BACKEND] Starting Pandora Admin API")
    print("="*70)
    print(f"[OK] Port: 9000")
    print(f"[OK] Environment: {settings.APP_ENV}")
    print(f"[OK] Debug: {settings.DEBUG}")
    print("="*70)
    print("[INFO] Features:")
    print("  - Honeypot Activity Monitoring")
    print("  - IDS Attack Logs")
    print("  - User Monitoring (Read-only access to User DB)")
    print("  - Security Analytics")
    print("="*70)
    print("[SECURITY] Admin API - Restricted to localhost only")
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
    print("[INFO] Shutting down Admin Backend API...")


# Create FastAPI app with lifespan
app = FastAPI(
    title=f"{settings.APP_NAME} - Admin API",
    version=settings.APP_VERSION,
    description="Admin-only API for monitoring and security features",
    lifespan=lifespan
)

# CORS middleware - Only allow localhost for admin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:27009", "http://localhost:27009"],
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

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    print(f"[ADMIN-API] {request.method} {request.url.path} - {response.status_code} ({process_time:.2f}s)")
    
    return response

# Health check
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "admin-api",
        "version": settings.APP_VERSION,
        "database": "connected"
    }

# Root endpoint
@app.get("/")
async def root():
    return {
        "service": "Pandora Admin API",
        "version": settings.APP_VERSION,
        "endpoints": {
            "honeypot": "/api/v1/honeypot",
            "attacks": "/api/v1/attacks"
        }
    }

# Register routers
app.include_router(honeypot.router, prefix="/api/v1/honeypot", tags=["Honeypot"])
app.include_router(attacks.router, prefix="/api/v1/attacks", tags=["Attacks"])
app.include_router(user_monitoring.router, prefix="/api/v1/users", tags=["User Monitoring"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="127.0.0.1",  # Admin API only accessible from localhost
        port=8002,  # New port for Admin Backend
        reload=settings.DEBUG
    )

