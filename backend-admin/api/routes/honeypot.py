"""
Honeypot Routes
API endpoints for honeypot logging and monitoring
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, func
from pydantic import BaseModel, validator
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import json
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database.database import get_db
from models.user import User
from models.honeypot import HoneypotLog, HoneypotSession
from services.geoip_service import geoip_service
from services.whois_service import whois_service
from api.routes.auth import get_current_user

from config import settings

router = APIRouter()


# ========================================
# PYDANTIC SCHEMAS
# ========================================

class HoneypotLogRequest(BaseModel):
    """Request schema for honeypot log submission"""
    client_ip: str  # From Honeypot Server
    user_agent: Optional[str] = ""
    session_id: Optional[str] = None
    user_id: Optional[int] = None
    is_authenticated: bool = False
    request_method: str
    request_path: str
    request_headers: Dict
    request_body: Optional[str] = None
    response_status: Optional[int] = None
    response_size: Optional[int] = None
    activity_type: str  # scan, login_attempt, failed_login, page_view, api_call, fake_probe
    scan_target: Optional[str] = None
    scan_hash: Optional[str] = None
    suspicious_score: Optional[int] = 0
    suspicious_reasons: Optional[List[str]] = []
    is_fake_path: bool = False
    timestamp: Optional[str] = None

    @validator('activity_type')
    def validate_activity_type(cls, v):
        valid_types = ['scan', 'login_attempt', 'failed_login', 'page_view', 'api_call', 'fake_probe', 'legitimate_access']
        if v not in valid_types:
            raise ValueError(f'activity_type must be one of: {valid_types}')
        return v

class HoneypotLogResponse(BaseModel):
    """Response schema for honeypot log"""
    id: int
    session_id: Optional[str]
    user_id: Optional[int]
    is_authenticated: bool
    ip_address: str
    user_agent: Optional[str]
    request_method: str
    request_path: str
    response_status: Optional[int]
    activity_type: str
    suspicious_score: int
    suspicious_reasons: List[str]
    timestamp: datetime
    geoip_country: Optional[str]
    geoip_city: Optional[str]
    scan_target: Optional[str]
    scan_hash: Optional[str]

    class Config:
        from_attributes = True

class HoneypotStatsResponse(BaseModel):
    """Response schema for honeypot statistics"""
    total_logs: int
    unique_ips: int
    authenticated_users: int
    anonymous_users: int
    top_activities: Dict[str, int]
    suspicious_activities: int
    activity_by_hour: Dict[str, int]
    top_suspicious_ips: List[Dict]


# ========================================
# ROUTES
# ========================================

@router.post("/log", response_model=dict)
async def log_honeypot_activity(
    log_data: HoneypotLogRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Log honeypot activity from Honeypot Server (remote)"""
    try:
        # Validate API Key
        api_key = request.headers.get('X-API-Key')
        expected_key = settings.CENTRAL_MONITOR_API_KEY if hasattr(settings, 'CENTRAL_MONITOR_API_KEY') else 'your-secret-key'
        
        if api_key != expected_key:
            raise HTTPException(status_code=403, detail="Invalid API Key")
        
        # Use client info from log_data (not from request, because it's proxied)
        client_ip = log_data.client_ip
        user_agent = log_data.user_agent or 'Unknown'

        # Get GeoIP info
        geoip_info = geoip_service.lookup(client_ip)

        # Get WHOIS info
        whois_info = whois_service.lookup_whois(client_ip)

        # Use authentication status from log_data (from Honeypot Server)
        is_authenticated = log_data.is_authenticated
        user_id = log_data.user_id

        # Determine activity type if not provided
        if log_data.activity_type == 'auto_detect':
            activity_type = _detect_activity_type(log_data.request_path, log_data.request_method)
        else:
            activity_type = log_data.activity_type

        # Calculate suspicious score if not provided
        suspicious_score = log_data.suspicious_score
        suspicious_reasons = log_data.suspicious_reasons or []

        if suspicious_score == 0:
            suspicious_score, suspicious_reasons = _calculate_suspicious_score(
                log_data, geoip_info, whois_info
            )

        # Create honeypot log
        honeypot_log = HoneypotLog(
            session_id=log_data.session_id,
            user_id=user_id,
            is_authenticated=is_authenticated,
            ip_address=client_ip,
            user_agent=user_agent,
            request_method=log_data.request_method,
            request_path=log_data.request_path,
            request_headers=log_data.request_headers,
            request_body=log_data.request_body[:5000] if log_data.request_body else None,  # Limit size
            response_status=log_data.response_status,
            response_size=log_data.response_size,
            geoip_country=geoip_info.get('country'),
            geoip_city=geoip_info.get('city'),
            geoip_lat=geoip_info.get('latitude'),
            geoip_lon=geoip_info.get('longitude'),
            whois_data=whois_info if whois_info.get('success') else None,
            activity_type=activity_type,
            scan_target=log_data.scan_target,
            scan_hash=log_data.scan_hash,
            suspicious_score=suspicious_score,
            suspicious_reasons=suspicious_reasons
        )

        db.add(honeypot_log)
        db.commit()
        db.refresh(honeypot_log)

        return {"success": True, "log_id": honeypot_log.id}

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to log honeypot activity: {str(e)}"
        )


@router.get("/logs", response_model=List[HoneypotLogResponse])
async def get_honeypot_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user_id: Optional[int] = Query(None),
    activity_type: Optional[str] = Query(None),
    suspicious_only: bool = Query(False),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get honeypot logs with filtering"""
    query = db.query(HoneypotLog)

    # Apply filters
    if user_id:
        query = query.filter(HoneypotLog.user_id == user_id)

    if activity_type:
        query = query.filter(HoneypotLog.activity_type == activity_type)

    if suspicious_only:
        query = query.filter(HoneypotLog.suspicious_score >= 50)

    if start_date:
        query = query.filter(HoneypotLog.timestamp >= start_date)

    if end_date:
        query = query.filter(HoneypotLog.timestamp <= end_date)

    # Order by timestamp desc
    query = query.order_by(desc(HoneypotLog.timestamp))

    # Pagination
    logs = query.offset(skip).limit(limit).all()

    return logs


@router.get("/stats", response_model=HoneypotStatsResponse)
async def get_honeypot_stats(
    hours: int = Query(24, ge=1, le=168),  # Last N hours
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get honeypot statistics"""
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)

    # Base query for time range
    query = db.query(HoneypotLog).filter(HoneypotLog.timestamp >= cutoff_time)

    # Basic counts
    total_logs = query.count()
    unique_ips = query.with_entities(HoneypotLog.ip_address).distinct().count()
    authenticated_users = query.filter(HoneypotLog.is_authenticated == True).count()
    anonymous_users = query.filter(HoneypotLog.is_authenticated == False).count()

    # Activity breakdown
    activity_counts = db.query(
        HoneypotLog.activity_type,
        func.count(HoneypotLog.id).label('count')
    ).filter(HoneypotLog.timestamp >= cutoff_time).group_by(HoneypotLog.activity_type).all()

    top_activities = {activity: count for activity, count in activity_counts}

    # Suspicious activities
    suspicious_activities = query.filter(HoneypotLog.suspicious_score >= 50).count()

    # Activity by hour (last 24 hours)
    hour_counts = db.query(
        func.strftime('%Y-%m-%d %H:00:00', HoneypotLog.timestamp).label('hour'),
        func.count(HoneypotLog.id).label('count')
    ).filter(HoneypotLog.timestamp >= cutoff_time).group_by('hour').all()

    activity_by_hour = {hour: count for hour, count in hour_counts}

    # Top suspicious IPs
    top_suspicious = db.query(
        HoneypotLog.ip_address,
        func.count(HoneypotLog.id).label('activity_count'),
        func.max(HoneypotLog.suspicious_score).label('max_suspicious_score'),
        func.max(HoneypotLog.timestamp).label('last_seen')
    ).filter(
        HoneypotLog.timestamp >= cutoff_time,
        HoneypotLog.suspicious_score >= 30
    ).group_by(HoneypotLog.ip_address).order_by(desc('max_suspicious_score')).limit(10).all()

    top_suspicious_ips = [
        {
            'ip': ip,
            'activity_count': count,
            'max_suspicious_score': max_score,
            'last_seen': last_seen.isoformat()
        }
        for ip, count, max_score, last_seen in top_suspicious
    ]

    return HoneypotStatsResponse(
        total_logs=total_logs,
        unique_ips=unique_ips,
        authenticated_users=authenticated_users,
        anonymous_users=anonymous_users,
        top_activities=top_activities,
        suspicious_activities=suspicious_activities,
        activity_by_hour=activity_by_hour,
        top_suspicious_ips=top_suspicious_ips
    )


@router.get("/suspicious")
async def get_suspicious_activities(
    threshold: int = Query(70, ge=0, le=100),
    limit: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get high-risk honeypot activities"""
    suspicious_logs = db.query(HoneypotLog).filter(
        HoneypotLog.suspicious_score >= threshold
    ).order_by(desc(HoneypotLog.suspicious_score)).limit(limit).all()

    return {
        "suspicious_logs": suspicious_logs,
        "count": len(suspicious_logs),
        "threshold": threshold
    }


# ========================================
# HELPER FUNCTIONS
# ========================================

def _detect_activity_type(path: str, method: str) -> str:
    """Auto-detect activity type from request"""
    path_lower = path.lower()

    if '/api/v1/scanner/' in path_lower:
        return 'scan'
    elif '/api/v1/auth/login' in path_lower:
        return 'login_attempt'
    elif '/api/v1/auth/register' in path_lower:
        return 'login_attempt'
    elif path_lower.startswith('/api/'):
        return 'api_call'
    elif method == 'GET' and not path.startswith('/api/'):
        return 'page_view'
    else:
        return 'api_call'


def _calculate_suspicious_score(log_data: HoneypotLogRequest, geoip_info: dict, whois_info: dict) -> tuple:
    """Calculate suspicious score and reasons"""
    score = 0
    reasons = []

    # Check for suspicious patterns in request
    path_lower = log_data.request_path.lower()

    # SQL injection patterns
    sql_patterns = ["'", '"', ';', 'union', 'select', 'drop', 'insert', 'update', 'delete']
    for pattern in sql_patterns:
        if pattern in path_lower:
            score += 20
            reasons.append(f"Potential SQL injection: {pattern}")
            break

    # Path traversal attempts
    if '../' in path_lower or '..\\' in path_lower:
        score += 30
        reasons.append("Path traversal attempt")

    # Scanner activity
    if '/api/v1/scanner/' in path_lower:
        score += 15
        reasons.append("Scanner activity detected")

    # Unusual user agents
    user_agent = log_data.request_headers.get('User-Agent', '').lower()
    suspicious_uas = ['sqlmap', 'nmap', 'nessus', 'openvas', 'nikto', 'w3af', 'burp']
    for ua in suspicious_uas:
        if ua in user_agent:
            score += 25
            reasons.append(f"Suspicious user agent: {ua}")
            break

    # Rapid requests (would need session tracking for this)
    # For now, we'll rely on activity type

    # GeoIP based suspicion (high-risk countries, but this is controversial)
    # country = geoip_info.get('country', '').lower()
    # risky_countries = ['cn', 'ru', 'ir', 'kp', 'sy']  # Example list
    # if country in risky_countries:
    #     score += 10
    #     reasons.append(f"High-risk country: {country}")

    # WHOIS based suspicion
    if whois_info.get('success') and whois_info.get('country'):
        # Can add logic here if needed
        pass

    # Activity type based scoring
    if log_data.activity_type == 'failed_login':
        score += 10
        reasons.append("Failed login attempt")

    if log_data.activity_type == 'scan':
        score += 5
        reasons.append("Scanning activity")

    # Ensure minimum score of 0 and maximum of 100
    score = max(0, min(100, score))

    return score, reasons

