"""
User Routes
User profile and management
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database.database import get_db
from models.user import User
from utils.auth import hash_password
from utils.rate_limiter import rate_limiter
from api.routes.auth import get_current_user

router = APIRouter()


# Pydantic schemas
class ProfileResponse(BaseModel):
    id: int
    email: str
    username: str
    plan: str
    daily_quota: int
    is_active: bool
    is_admin: bool
    is_verified: bool
    created_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UpdateProfileRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class QuotaResponse(BaseModel):
    daily_limit: int
    used_today: int
    remaining: int
    reset_at: datetime


class APIKeyResponse(BaseModel):
    api_key: str
    created_at: datetime


@router.get("/profile", response_model=ProfileResponse)
async def get_profile(current_user: User = Depends(get_current_user)):
    """Get user profile"""
    return current_user


@router.put("/profile", response_model=ProfileResponse)
async def update_profile(
    request_data: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user profile"""
    
    # Update username if provided
    if request_data.username:
        # Check if username already exists
        existing = db.query(User).filter(
            User.username == request_data.username,
            User.id != current_user.id
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
        
        current_user.username = request_data.username
    
    # Update email if provided
    if request_data.email:
        # Check if email already exists
        existing = db.query(User).filter(
            User.email == request_data.email,
            User.id != current_user.id
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        current_user.email = request_data.email
        current_user.is_verified = False  # Need to verify new email
    
    db.commit()
    db.refresh(current_user)
    
    return current_user


@router.post("/change-password")
async def change_password(
    request_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change user password"""
    
    from utils.auth import verify_password
    
    # Verify current password
    if not verify_password(request_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Update password
    current_user.password_hash = hash_password(request_data.new_password)
    db.commit()
    
    return {"message": "Password changed successfully"}


@router.get("/quota", response_model=QuotaResponse)
async def get_quota(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get quota information"""
    
    quota_info = rate_limiter.get_quota_info(
        current_user.id,
        current_user.daily_quota
    )
    
    return QuotaResponse(**quota_info)


@router.get("/api-key", response_model=APIKeyResponse)
async def get_api_key(current_user: User = Depends(get_current_user)):
    """Get user's API key"""
    
    if not current_user.api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    return APIKeyResponse(
        api_key=current_user.api_key,
        created_at=current_user.created_at
    )


@router.post("/api-key/regenerate", response_model=APIKeyResponse)
async def regenerate_api_key(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Regenerate API key"""
    
    # Generate new API key
    new_key = current_user.generate_api_key()
    
    db.commit()
    db.refresh(current_user)
    
    return APIKeyResponse(
        api_key=new_key,
        created_at=datetime.utcnow()
    )


@router.delete("/account")
async def delete_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete user account (soft delete - mark as inactive)"""
    
    current_user.is_active = False
    db.commit()
    
    return {"message": "Account deactivated successfully"}

