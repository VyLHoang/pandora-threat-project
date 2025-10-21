"""
History Routes
Scan history and statistics
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database.database import get_db
from models.user import User
from models.scan import Scan, ScanResult
from api.routes.auth import get_current_user

router = APIRouter()


# Pydantic schemas
class ScanHistoryItem(BaseModel):
    id: int
    scan_type: str
    target: str
    status: str
    is_malicious: Optional[bool] = None
    detection_count: Optional[int] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class HistoryResponse(BaseModel):
    total: int
    scans: List[ScanHistoryItem]


class StatsResponse(BaseModel):
    total_scans: int
    ip_scans: int
    hash_scans: int
    malicious_found: int
    pending_scans: int
    completed_scans: int
    failed_scans: int
    scans_today: int
    quota_remaining: int


class DailyScanCount(BaseModel):
    date: str
    count: int


class DashboardStatsResponse(BaseModel):
    total_scans: int
    malicious_count: int
    clean_count: int
    suspicious_count: int
    daily_scans: List[DailyScanCount]


@router.get("", response_model=HistoryResponse)
async def get_scan_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    scan_type: Optional[str] = Query(None, regex="^(ip|hash)$"),
    status: Optional[str] = Query(None, regex="^(pending|processing|completed|failed)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's scan history"""
    
    # Build query
    query = db.query(Scan).filter(Scan.user_id == current_user.id)
    
    # Apply filters
    if scan_type:
        query = query.filter(Scan.scan_type == scan_type)
    
    if status:
        query = query.filter(Scan.status == status)
    
    # Get total count
    total = query.count()
    
    # Get scans with pagination
    scans = query.order_by(desc(Scan.created_at)).offset(skip).limit(limit).all()
    
    # Build response
    scan_items = []
    for scan in scans:
        item_data = {
            'id': scan.id,
            'scan_type': scan.scan_type,
            'target': scan.target,
            'status': scan.status,
            'created_at': scan.created_at,
            'completed_at': scan.completed_at
        }
        
        # Add result data if available
        if scan.result:
            item_data['is_malicious'] = scan.result.is_malicious
            item_data['detection_count'] = scan.result.detection_count
        
        scan_items.append(ScanHistoryItem(**item_data))
    
    return HistoryResponse(
        total=total,
        scans=scan_items
    )


@router.get("/stats", response_model=StatsResponse)
async def get_statistics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's scanning statistics"""
    
    # Total scans
    total_scans = db.query(Scan).filter(Scan.user_id == current_user.id).count()
    
    # By type
    ip_scans = db.query(Scan).filter(
        Scan.user_id == current_user.id,
        Scan.scan_type == 'ip'
    ).count()
    
    hash_scans = db.query(Scan).filter(
        Scan.user_id == current_user.id,
        Scan.scan_type == 'hash'
    ).count()
    
    # By status
    pending_scans = db.query(Scan).filter(
        Scan.user_id == current_user.id,
        Scan.status.in_(['pending', 'processing'])
    ).count()
    
    completed_scans = db.query(Scan).filter(
        Scan.user_id == current_user.id,
        Scan.status == 'completed'
    ).count()
    
    failed_scans = db.query(Scan).filter(
        Scan.user_id == current_user.id,
        Scan.status == 'failed'
    ).count()
    
    # Malicious found
    malicious_found = db.query(ScanResult).join(Scan).filter(
        Scan.user_id == current_user.id,
        ScanResult.is_malicious == True
    ).count()
    
    # Scans today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    scans_today = db.query(Scan).filter(
        Scan.user_id == current_user.id,
        Scan.created_at >= today_start
    ).count()
    
    # Quota remaining
    quota_remaining = max(0, current_user.daily_quota - scans_today)
    
    return StatsResponse(
        total_scans=total_scans,
        ip_scans=ip_scans,
        hash_scans=hash_scans,
        malicious_found=malicious_found,
        pending_scans=pending_scans,
        completed_scans=completed_scans,
        failed_scans=failed_scans,
        scans_today=scans_today,
        quota_remaining=quota_remaining
    )


@router.get("/dashboard-stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get dashboard statistics with daily scan data for charts"""
    
    # Total scans
    total_scans = db.query(Scan).filter(Scan.user_id == current_user.id).count()
    
    # Malicious vs clean vs suspicious
    malicious = db.query(ScanResult).join(Scan).filter(
        Scan.user_id == current_user.id,
        ScanResult.is_malicious == True
    ).count()
    
    # Clean = completed scans minus malicious
    completed_total = db.query(Scan).filter(
        Scan.user_id == current_user.id,
        Scan.status == 'completed'
    ).count()
    
    clean = completed_total - malicious
    
    # For now, suspicious = 0 (we can add logic later based on detection ratio)
    suspicious = 0
    
    # Daily scans (last 7 days)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    daily_data = db.query(
        func.date(Scan.created_at).label('scan_date'),
        func.count(Scan.id).label('scan_count')
    ).filter(
        Scan.user_id == current_user.id,
        Scan.created_at >= seven_days_ago
    ).group_by(func.date(Scan.created_at)).all()
    
    daily_scans = [
        DailyScanCount(date=str(row.scan_date), count=row.scan_count)
        for row in daily_data
    ]
    
    return DashboardStatsResponse(
        total_scans=total_scans,
        malicious_count=malicious,
        clean_count=clean,
        suspicious_count=suspicious,
        daily_scans=daily_scans
    )


@router.delete("/{scan_id}")
async def delete_scan(
    scan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a scan record"""
    
    scan = db.query(Scan).filter(
        Scan.id == scan_id,
        Scan.user_id == current_user.id
    ).first()
    
    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan not found"
        )
    
    db.delete(scan)
    db.commit()
    
    return {"message": "Scan deleted successfully", "scan_id": scan_id}


@router.delete("/clear/all")
async def clear_all_scans(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Clear all scan history (use with caution)"""
    
    deleted_count = db.query(Scan).filter(
        Scan.user_id == current_user.id
    ).delete()
    
    db.commit()
    
    return {
        "message": f"Deleted {deleted_count} scans",
        "deleted_count": deleted_count
    }

