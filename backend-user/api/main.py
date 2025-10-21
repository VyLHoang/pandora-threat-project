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

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    print(f"[USER-API] {request.method} {request.url.path} - {response.status_code} ({process_time:.2f}s)")
    
    return response

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
        host=settings.HOST,
        port=8000,
        reload=settings.DEBUG
    )

