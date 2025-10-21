"""
Scan Model
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, DECIMAL, ARRAY, func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database import Base


class Scan(Base):
    """Scan model for IP and hash scans"""
    
    __tablename__ = "scans"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Key
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # Scan Info
    scan_type = Column(String(20), nullable=False)  # 'ip' or 'hash'
    target = Column(String(255), nullable=False, index=True)  # IP address or file hash
    status = Column(String(20), default='pending')  # pending, processing, completed, failed
    
    # Request Info
    ip_address = Column(String(45))  # User's IP who made the scan
    user_agent = Column(Text)
    
    # GeoIP Info
    geoip_country = Column(String(100))
    geoip_city = Column(String(100))
    geoip_lat = Column(DECIMAL(10, 8))
    geoip_lon = Column(DECIMAL(11, 8))
    
    # WHOIS Info (scanner's IP WHOIS - admin only)
    whois_data = Column(JSONB)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    completed_at = Column(DateTime(timezone=True))
    
    # Relationships
    user = relationship("User", back_populates="scans")
    result = relationship("ScanResult", back_populates="scan", uselist=False, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Scan {self.scan_type}:{self.target}>"


class ScanResult(Base):
    """Scan result model"""
    
    __tablename__ = "scan_results"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Key
    scan_id = Column(Integer, ForeignKey('scans.id'), nullable=False, unique=True, index=True)
    
    # VirusTotal Response
    vt_response = Column(JSONB)  # Full VirusTotal response
    
    # Summary
    is_malicious = Column(Boolean)
    detection_count = Column(Integer, default=0)
    total_engines = Column(Integer, default=0)
    threat_names = Column(ARRAY(Text))  # Array of threat names detected
    
    # WHOIS Info (target IP WHOIS - visible to user)
    whois_data = Column(JSONB)
    
    # Timestamps
    scan_date = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    scan = relationship("Scan", back_populates="result")
    
    def __repr__(self):
        return f"<ScanResult scan_id={self.scan_id} malicious={self.is_malicious}>"

