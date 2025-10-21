"""
User Monitoring Routes for Admin
Admin có thể xem dữ liệu của User để monitoring và analytics
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from pydantic import BaseModel
from typing import List, Optional, Union
from datetime import datetime, timedelta

from database.user_db_client import (
    get_user_db,
    UserModel,
    Scan,
    ScanResult
)

try:
    from api.routes.auth import get_current_user
    from models.user import User as AdminUser
except ImportError:
    # Fallback nếu không có auth
    get_current_user = None
    AdminUser = None


router = APIRouter()


# Dependency để bypass auth khi request từ localhost (Central Monitor)
async def get_current_user_or_bypass(request: Request) -> Optional[object]:
    """
    Allow bypass authentication for localhost requests (from Central Monitor)
    This is safe because Admin Backend only binds to 127.0.0.1
    """
    client_host = request.client.host if request.client else None
    
    # Allow localhost bypass
    if client_host in ['127.0.0.1', 'localhost', '::1']:
        # Create a dummy user object for localhost requests
        class LocalhostAdmin:
            id = 0
            username = "central_monitor"
            is_admin = True
        return LocalhostAdmin()
    
    # For other requests, require authentication
    if get_current_user:
        return await get_current_user(request)
    else:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Authentication not configured"
        )


# ================== Pydantic Schemas ==================

class UserStats(BaseModel):
    """Thống kê về user"""
    total_users: int
    active_users_today: int
    new_users_this_week: int
    total_scans: int
    scans_today: int


class UserDetail(BaseModel):
    """Chi tiết user (không bao gồm password)"""
    id: int
    username: str
    email: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]
    total_scans: int
    
    class Config:
        from_attributes = True


class ScanDetail(BaseModel):
    """Chi tiết scan của user"""
    id: int
    user_id: int
    scan_type: str
    ip_address: Optional[str]
    file_hash: Optional[str]
    created_at: datetime
    geoip_country: Optional[str]
    geoip_city: Optional[str]
    
    class Config:
        from_attributes = True


# ================== API Endpoints ==================

@router.get("/stats", response_model=UserStats)
async def get_user_stats(
    request: Request,
    db: Session = Depends(get_user_db),
    current_admin = Depends(get_current_user_or_bypass)
):
    """
    Lấy thống kê tổng quan về users
    Chỉ Admin mới được truy cập
    """
    try:
        # Total users
        total_users = db.query(UserModel).count() if UserModel else 0
        
        # Active users today
        today = datetime.utcnow().date()
        active_today = 0
        if UserModel:
            active_today = db.query(UserModel).filter(
                func.date(UserModel.last_login) == today
            ).count()
        
        # New users this week
        week_ago = datetime.utcnow() - timedelta(days=7)
        new_users = 0
        if UserModel:
            new_users = db.query(UserModel).filter(
                UserModel.created_at >= week_ago
            ).count()
        
        # Total scans
        total_scans = db.query(Scan).count() if Scan else 0
        
        # Scans today
        scans_today = 0
        if Scan:
            scans_today = db.query(Scan).filter(
                func.date(Scan.created_at) == today
            ).count()
        
        return UserStats(
            total_users=total_users,
            active_users_today=active_today,
            new_users_this_week=new_users,
            total_scans=total_scans,
            scans_today=scans_today
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cannot get user stats: {str(e)}"
        )


@router.get("/users", response_model=List[UserDetail])
async def get_all_users(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_user_db),
    current_admin = Depends(get_current_user_or_bypass)
):
    """
    Lấy danh sách tất cả users
    Chỉ Admin mới được xem
    """
    if not UserModel:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="User models not available"
        )
    
    try:
        users = db.query(UserModel).offset(skip).limit(limit).all()
        
        # Add scan count for each user
        result = []
        for user in users:
            user_dict = {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_active': user.is_active,
                'created_at': user.created_at,
                'last_login': user.last_login,
                'total_scans': db.query(Scan).filter(Scan.user_id == user.id).count() if Scan else 0
            }
            result.append(UserDetail(**user_dict))
        
        return result
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cannot get users: {str(e)}"
        )


@router.get("/users/{user_id}", response_model=UserDetail)
async def get_user_by_id(
    user_id: int,
    request: Request,
    db: Session = Depends(get_user_db),
    current_admin = Depends(get_current_user_or_bypass)
):
    """
    Lấy chi tiết một user cụ thể
    """
    if not UserModel:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="User models not available"
        )
    
    try:
        user = db.query(UserModel).filter(UserModel.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )
        
        user_dict = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'is_active': user.is_active,
            'created_at': user.created_at,
            'last_login': user.last_login,
            'total_scans': db.query(Scan).filter(Scan.user_id == user.id).count() if Scan else 0
        }
        
        return UserDetail(**user_dict)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cannot get user: {str(e)}"
        )


@router.get("/users/{user_id}/scans", response_model=List[ScanDetail])
async def get_user_scans(
    user_id: int,
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_user_db),
    current_admin = Depends(get_current_user_or_bypass)
):
    """
    Lấy danh sách scans của một user
    """
    if not Scan:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Scan models not available"
        )
    
    try:
        scans = db.query(Scan).filter(
            Scan.user_id == user_id
        ).order_by(
            desc(Scan.created_at)
        ).offset(skip).limit(limit).all()
        
        return [ScanDetail.from_orm(scan) for scan in scans]
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cannot get scans: {str(e)}"
        )


@router.get("/scans/recent", response_model=List[ScanDetail])
async def get_recent_scans(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_user_db),
    current_admin = Depends(get_current_user_or_bypass)
):
    """
    Lấy danh sách scans gần đây nhất (tất cả users)
    """
    if not Scan:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Scan models not available"
        )
    
    try:
        scans = db.query(Scan).order_by(
            desc(Scan.created_at)
        ).limit(limit).all()
        
        return [ScanDetail.from_orm(scan) for scan in scans]
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cannot get recent scans: {str(e)}"
        )


@router.get("/scans/suspicious")
async def get_suspicious_scans(
    request: Request,
    hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_user_db),
    current_admin = Depends(get_current_user_or_bypass)
):
    """
    Lấy các scan đáng ngờ trong N giờ qua
    - Nhiều scan từ cùng 1 IP
    - Scan từ các quốc gia bất thường
    """
    if not Scan:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Scan models not available"
        )
    
    try:
        time_threshold = datetime.utcnow() - timedelta(hours=hours)
        
        # Get scans grouped by IP
        suspicious_ips = db.query(
            Scan.ip_address,
            func.count(Scan.id).label('count'),
            func.max(Scan.geoip_country).label('country')
        ).filter(
            Scan.created_at >= time_threshold,
            Scan.ip_address.isnot(None)
        ).group_by(
            Scan.ip_address
        ).having(
            func.count(Scan.id) > 5  # Nhiều hơn 5 scans trong thời gian ngắn
        ).all()
        
        result = []
        for ip, count, country in suspicious_ips:
            result.append({
                'ip_address': ip,
                'scan_count': count,
                'country': country,
                'time_window': f'{hours} hours'
            })
        
        return {
            'suspicious_ips': result,
            'total_suspicious': len(result)
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cannot get suspicious scans: {str(e)}"
        )

