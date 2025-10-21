"""
Scanner Routes
IP and File Hash Scanning with VirusTotal
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime
import re
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database.database import get_db
from models.user import User
from models.scan import Scan, ScanResult
from services.virustotal_service import vt_service
from services.geoip_service import geoip_service
from services.whois_service import whois_service

from config import settings
from utils.rate_limiter import rate_limiter
from api.routes.auth import get_current_user

router = APIRouter()


# ========================================
# PYDANTIC SCHEMAS (Define first!)
# ========================================

class IPScanRequest(BaseModel):
    ip_address: str
    
    @validator('ip_address')
    def validate_ip(cls, v):
        # Simple IP validation
        pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if not re.match(pattern, v):
            raise ValueError('Invalid IP address format')
        # Check range
        parts = v.split('.')
        if not all(0 <= int(part) <= 255 for part in parts):
            raise ValueError('Invalid IP address range')
        return v


class HashScanRequest(BaseModel):
    file_hash: str
    
    @validator('file_hash')
    def validate_hash(cls, v):
        # Accept MD5 (32), SHA1 (40), SHA256 (64)
        v = v.lower().strip()
        if len(v) not in [32, 40, 64]:
            raise ValueError('Invalid hash length. Must be MD5 (32), SHA1 (40), or SHA256 (64)')
        if not re.match(r'^[a-f0-9]+$', v):
            raise ValueError('Invalid hash format. Must be hexadecimal')
        return v


class ScanResponse(BaseModel):
    scan_id: int
    scan_type: str
    target: str
    status: str
    created_at: datetime
    result: Optional[dict] = None
    error: Optional[str] = None


@router.post("/ip", response_model=ScanResponse)
async def scan_ip(
    request_data: IPScanRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Scan IP address with VirusTotal"""
    
    print(f"[SCAN] User: {current_user.username} (ID: {current_user.id})")
    print(f"[SCAN] Request IP: {request_data.ip_address}")
    
    # Check daily quota - TEMPORARILY DISABLED FOR DEBUG
    # has_quota, remaining = rate_limiter.check_daily_quota(
    #     current_user.id,
    #     current_user.daily_quota
    # )
    # 
    # if not has_quota:
    #     raise HTTPException(
    #         status_code=status.HTTP_429_TOO_MANY_REQUESTS,
    #         detail=f"Daily quota exceeded. Limit: {current_user.daily_quota}/day"
    #     )
    
    # Get user's IP and GeoIP info
    client_ip = request.client.host
    geoip_info = geoip_service.lookup(client_ip)

    # Get WHOIS info for scanner's IP (admin only view)
    scanner_whois = whois_service.lookup_whois(client_ip)

    # Initialize scan variable (in case of error)
    scan = None

    # Create scan record
    try:
        print(f"[SCAN] Creating scan record...")
        print(f"[SCAN] GeoIP info: {geoip_info}")
        print(f"[SCAN] Scanner WHOIS: {scanner_whois.get('success', 'Failed')}")

        scan = Scan(
            user_id=current_user.id,
            scan_type='ip',
            target=request_data.ip_address,
            status='processing',
            ip_address=client_ip,
            user_agent=request.headers.get('User-Agent', 'Unknown'),
            geoip_country=geoip_info.get('country'),
            geoip_city=geoip_info.get('city'),
            geoip_lat=geoip_info.get('latitude'),
            geoip_lon=geoip_info.get('longitude'),
            whois_data=scanner_whois if scanner_whois.get('success') else None
        )
        
        db.add(scan)
        db.commit()
        db.refresh(scan)
        print(f"[SCAN] Scan record created: ID={scan.id}")
    except Exception as e:
        print(f"[ERROR] Failed to create scan record: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create scan record: {str(e)}"
        )
    
    # Scan with VirusTotal
    try:
        print(f"[SCAN] Starting IP scan: {request_data.ip_address}")
        vt_result = vt_service.scan_ip(request_data.ip_address)
        print(f"[SCAN] VT Result: {vt_result}")
        
        if vt_result and 'error' not in vt_result:
            # Get WHOIS info for target IP (visible to user)
            target_whois = whois_service.lookup_whois(request_data.ip_address)

            # Create scan result
            scan_result = ScanResult(
                scan_id=scan.id,
                vt_response=vt_result.get('raw_response'),
                is_malicious=vt_result.get('is_malicious', False),
                detection_count=vt_result.get('detection_count', 0),
                total_engines=vt_result.get('total_engines', 0),
                threat_names=vt_result.get('threat_names', []),  # Empty list for IP scans
                scan_date=datetime.utcnow(),
                whois_data=target_whois if target_whois.get('success') else None
            )
            
            db.add(scan_result)
            scan.status = 'completed'
            scan.completed_at = datetime.utcnow()
            db.commit()
            
            return ScanResponse(
                scan_id=scan.id,
                scan_type=scan.scan_type,
                target=scan.target,
                status=scan.status,
                created_at=scan.created_at,
                result=vt_result
            )
        else:
            # VT API returned error
            print(f"[SCAN] VT returned error or no result")
            scan.status = 'failed'
            db.commit()
            
            error_msg = vt_result.get('error', 'VirusTotal scan failed') if vt_result else 'No response from VirusTotal'
            
            return ScanResponse(
                scan_id=scan.id,
                scan_type=scan.scan_type,
                target=scan.target,
                status='failed',
                created_at=scan.created_at,
                result=None,
                error=error_msg
            )
        
    except Exception as e:
        print(f"[ERROR] IP scan failed: {e}")
        import traceback
        traceback.print_exc()
        if scan:
            scan.status = 'failed'
            db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Scan failed: {str(e)}"
        )


@router.post("/hash", response_model=ScanResponse)
async def scan_hash(
    request_data: HashScanRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Scan file hash with VirusTotal"""
    
    # Check daily quota
    has_quota, remaining = rate_limiter.check_daily_quota(
        current_user.id,
        current_user.daily_quota
    )
    
    if not has_quota:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily quota exceeded. Limit: {current_user.daily_quota}/day"
        )
    
    # Get user's IP and GeoIP info
    client_ip = request.client.host
    geoip_info = geoip_service.lookup(client_ip)

    # Get WHOIS info for scanner's IP (admin only view)
    scanner_whois = whois_service.lookup_whois(client_ip)

    # Create scan record
    scan = Scan(
        user_id=current_user.id,
        scan_type='hash',
        target=request_data.file_hash,
        status='processing',
        ip_address=client_ip,
        user_agent=request.headers.get('User-Agent', 'Unknown'),
        geoip_country=geoip_info.get('country'),
        geoip_city=geoip_info.get('city'),
        geoip_lat=geoip_info.get('latitude'),
        geoip_lon=geoip_info.get('longitude'),
        whois_data=scanner_whois if scanner_whois.get('success') else None
    )
    
    db.add(scan)
    db.commit()
    db.refresh(scan)
    
    # Scan with VirusTotal
    try:
        vt_result = vt_service.scan_file_hash(request_data.file_hash)
        
        if vt_result and 'error' not in vt_result:
            # Create scan result
            scan_result = ScanResult(
                scan_id=scan.id,
                vt_response=vt_result.get('raw_response'),
                is_malicious=vt_result.get('is_malicious', False),
                detection_count=vt_result.get('detection_count', 0),
                total_engines=vt_result.get('total_engines', 0),
                threat_names=vt_result.get('threat_names', []),
                scan_date=datetime.utcnow()
            )
            
            db.add(scan_result)
            scan.status = 'completed'
            scan.completed_at = datetime.utcnow()
        else:
            scan.status = 'failed'
            scan_result = None
        
        db.commit()
        
        return ScanResponse(
            scan_id=scan.id,
            scan_type=scan.scan_type,
            target=scan.target,
            status=scan.status,
            created_at=scan.created_at,
            result=vt_result if scan_result else None
        )
        
    except Exception as e:
        scan.status = 'failed'
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Scan failed: {str(e)}"
        )


@router.get("/{scan_id}", response_model=ScanResponse)
async def get_scan_result(
    scan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get scan result by ID"""
    
    scan = db.query(Scan).filter(
        Scan.id == scan_id,
        Scan.user_id == current_user.id
    ).first()
    
    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan not found"
        )
    
    # Get scan result if exists
    result_data = None
    if scan.result:
        result_data = {
            'is_malicious': scan.result.is_malicious,
            'detection_count': scan.result.detection_count,
            'total_engines': scan.result.total_engines,
            'threat_names': scan.result.threat_names,
            'vt_response': scan.result.vt_response
        }
    
    return ScanResponse(
        scan_id=scan.id,
        scan_type=scan.scan_type,
        target=scan.target,
        status=scan.status,
        created_at=scan.created_at,
        result=result_data
    )

