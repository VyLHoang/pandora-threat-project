"""
Authentication Routes
Login, Register, Token Management
"""

from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from datetime import datetime
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database.database import get_db
from models.user import User
from utils.auth import hash_password, verify_password, create_access_token, create_refresh_token, verify_token

router = APIRouter()
security = HTTPBearer()


# Pydantic schemas
class RegisterRequest(BaseModel):
    email: EmailStr
    username: str
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    plan: str
    daily_quota: int
    is_active: bool
    is_admin: bool
    created_at: datetime


# Dependency: Get current user from HTTPOnly cookie
async def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from HTTPOnly cookie"""
    # Try to get token from cookie first
    token = request.cookies.get("access_token")
    token_source = "cookie"

    # Fallback to Authorization header (for API clients)
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[len("Bearer "):].strip()
            token_source = "Authorization header"

    # Debug logging for troubleshooting
    try:
        masked = (token[:12] + "...") if token else "None"
        print(f"[auth.debug] token_source={token_source} token={masked}")
    except Exception:
        print("[auth.debug] token debug failed")

    if not token:
        print("[auth.debug] no token found -> 401")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated - No token found"
        )

    payload = verify_token(token)
    print(f"[auth.debug] verify_token payload={payload}")

    if not payload:
        print("[auth.debug] token invalid/expired -> 401")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    user_id = payload.get("sub")
    if not user_id:
        print("[auth.debug] payload missing sub -> 401")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )

    # Convert user_id to int (it's stored as string in JWT)
    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        print(f"[auth.debug] user_id conversion failed: {user_id} -> 401")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user id in token"
        )

    user = db.query(User).filter(User.id == user_id).first()
    print(f"[auth.debug] db user lookup id={user_id} found={bool(user)}")
    if not user:
        print("[auth.debug] user not found -> 401")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    if not user.is_active:
        print("[auth.debug] user inactive -> 403")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive"
        )

    print(f"[auth.debug] auth success user_id={user.id}")
    return user


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(register_request: RegisterRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    """Register new user - Returns user info and sets HTTPOnly cookie"""
    
    try:
        # Check if email exists
        if db.query(User).filter(User.email == register_request.email).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Check if username exists
        if db.query(User).filter(User.username == register_request.username).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
        
        # Create user
        user = User(
            email=register_request.email,
            username=register_request.username,
            password_hash=hash_password(register_request.password)
        )
        
        # Generate API key
        user.generate_api_key()
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Registration failed: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )
    
    # Create tokens
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    
    # Set HTTPOnly cookies 
    # Auto-detect if running on HTTPS (production) or HTTP (development)
    is_secure = request.url.scheme == "https"
    
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,      # JavaScript không thể đọc
        secure=is_secure,   # True for HTTPS, False for HTTP development
        samesite="lax",     # Bảo vệ CSRF
        max_age=1800        # 30 phút
    )
    
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=is_secure,   # True for HTTPS, False for HTTP development
        samesite="lax",
        max_age=604800      # 7 ngày
    )
    
    # Return user info (NO TOKENS in response body!)
    return {
        "message": "Registration successful",
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "plan": user.plan,
            "daily_quota": user.daily_quota,
            "is_active": user.is_active,
            "is_admin": user.is_admin,
            "created_at": user.created_at
        }
    }


@router.post("/login")
async def login(login_request: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    """Login user - Returns user info and sets HTTPOnly cookie"""
    
    # Find user
    user = db.query(User).filter(User.email == login_request.email).first()
    
    if not user or not verify_password(login_request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Create tokens
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    
    # Set HTTPOnly cookies (SECURE!)
    # Auto-detect if running on HTTPS (production) or HTTP (development)
    is_secure = request.url.scheme == "https"
    
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=is_secure,  # True for HTTPS, False for HTTP development
        samesite="lax",
        max_age=1800
    )
    
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=is_secure,  # True for HTTPS, False for HTTP development
        samesite="lax",
        max_age=604800
    )
    
    # Return user info (NO TOKENS in response body!)
    return {
        "message": "Login successful",
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "plan": user.plan,
            "daily_quota": user.daily_quota,
            "is_active": user.is_active,
            "is_admin": user.is_admin
        }
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return current_user


@router.post("/logout")
async def logout(response: Response, current_user: User = Depends(get_current_user)):
    """Logout user - Delete HTTPOnly cookies"""
    # Delete cookies by setting max_age=0
    response.delete_cookie(key="access_token")
    response.delete_cookie(key="refresh_token")
    
    return {"message": "Logged out successfully"}


@router.post("/refresh")
async def refresh_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Refresh access token using refresh token"""
    
    token = credentials.credentials
    payload = verify_token(token)
    
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user"
        )
    
    # Create new access token
    new_access_token = create_access_token({"sub": str(user.id)})
    
    return {
        "access_token": new_access_token,
        "token_type": "bearer"
    }

