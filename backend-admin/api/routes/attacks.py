"""
Attack Log Routes
View detected attacks and security events
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database.database import get_db
from models.attack import AttackLog
from models.user import User
from api.routes.auth import get_current_user

router = APIRouter()


# Pydantic schemas
class AttackResponse(BaseModel):
    id: int
    source_ip: str
    source_port: Optional[int] = None
    target_port: Optional[int] = None
    attack_type: str
    severity: str
    packet_count: int
    country: Optional[str] = None
    city: Optional[str] = None
    detected_tool: str
    confidence: int
    detected_at: datetime
    
    class Config:
        from_attributes = True


class AttackStatsResponse(BaseModel):
    total_attacks: int
    attacks_today: int
    unique_attackers: int
    attack_types: dict
    severity_breakdown: dict
    top_countries: List[dict]


@router.get("", response_model=List[AttackResponse])
async def get_attacks(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    severity: Optional[str] = Query(None),
    attack_type: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get attack logs"""
    
    query = db.query(AttackLog)
    
    if severity:
        query = query.filter(AttackLog.severity == severity)
    if attack_type:
        query = query.filter(AttackLog.attack_type == attack_type)
    
    attacks = query.order_by(desc(AttackLog.detected_at)).offset(skip).limit(limit).all()
    
    return attacks


@router.get("/stats", response_model=AttackStatsResponse)
async def get_attack_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get attack statistics"""
    
    # Total attacks
    total = db.query(AttackLog).count()
    
    # Attacks today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0)
    today_attacks = db.query(AttackLog).filter(AttackLog.detected_at >= today_start).count()
    
    # Unique attackers
    unique_ips = db.query(func.count(func.distinct(AttackLog.source_ip))).scalar() or 0
    
    # Attack types breakdown
    attack_types = {}
    type_results = db.query(
        AttackLog.attack_type,
        func.count(AttackLog.id)
    ).group_by(AttackLog.attack_type).all()
    
    for atype, count in type_results:
        attack_types[atype] = count
    
    # Severity breakdown
    severity_breakdown = {}
    sev_results = db.query(
        AttackLog.severity,
        func.count(AttackLog.id)
    ).group_by(AttackLog.severity).all()
    
    for sev, count in sev_results:
        severity_breakdown[sev] = count
    
    # Top countries
    top_countries = []
    country_results = db.query(
        AttackLog.country,
        func.count(AttackLog.id).label('count')
    ).filter(AttackLog.country.isnot(None)).group_by(AttackLog.country).order_by(desc('count')).limit(10).all()
    
    for country, count in country_results:
        top_countries.append({"country": country, "count": count})
    
    return AttackStatsResponse(
        total_attacks=total,
        attacks_today=today_attacks,
        unique_attackers=unique_ips,
        attack_types=attack_types,
        severity_breakdown=severity_breakdown,
        top_countries=top_countries
    )

