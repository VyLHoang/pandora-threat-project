"""
Honeypot Models
Track all activities on port 443 webserver
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, DECIMAL, ARRAY, func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database import Base


class HoneypotLog(Base):
    """Honeypot activity log - tracks all requests to port 443"""
    
    __tablename__ = "honeypot_logs"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Session tracking
    session_id = Column(String(255), index=True)  # Session identifier for tracking
    
    # User Info
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)  # NULL if not authenticated
    is_authenticated = Column(Boolean, default=False, index=True)
    
    # Request Info
    ip_address = Column(String(45), index=True)
    user_agent = Column(Text)
    request_method = Column(String(10))  # GET, POST, PUT, DELETE
    request_path = Column(String(500), index=True)
    request_headers = Column(JSONB)
    request_body = Column(Text)  # Limited to first 5000 chars
    
    # Response Info
    response_status = Column(Integer)  # HTTP status code
    response_size = Column(Integer)  # Response size in bytes
    
    # GeoIP Info
    geoip_country = Column(String(100))
    geoip_city = Column(String(100))
    geoip_lat = Column(DECIMAL(10, 8))
    geoip_lon = Column(DECIMAL(11, 8))
    
    # WHOIS Info
    whois_data = Column(JSONB)
    
    # Activity Classification
    activity_type = Column(String(50), index=True)  # scan, login_attempt, failed_login, page_view, api_call
    scan_target = Column(String(255), nullable=True)  # IP or domain scanned (if activity_type = scan)
    scan_hash = Column(String(255), nullable=True)  # File hash scanned (if activity_type = scan)
    
    # Security Analysis
    suspicious_score = Column(Integer, default=0, index=True)  # 0-100
    suspicious_reasons = Column(ARRAY(Text))  # List of reasons for suspicion
    
    # Timestamps
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    user = relationship("User", backref="honeypot_logs")
    
    def __repr__(self):
        user_info = f"User {self.user_id}" if self.is_authenticated else "Anonymous"
        return f"<HoneypotLog {user_info} {self.request_method} {self.request_path}>"


class HoneypotSession(Base):
    """Honeypot session tracking - for future expansion"""
    
    __tablename__ = "honeypot_sessions"
    
    # Primary Key
    session_id = Column(String(255), primary_key=True)
    
    # Session Info
    ip_address = Column(String(45), index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    is_authenticated = Column(Boolean, default=False)
    
    # Browser Fingerprinting
    user_fingerprint = Column(JSONB)  # Browser fingerprint data
    
    # Activity Tracking
    request_count = Column(Integer, default=0)
    first_seen = Column(DateTime(timezone=True), server_default=func.now())
    last_seen = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", backref="honeypot_sessions")
    
    def __repr__(self):
        return f"<HoneypotSession {self.session_id} requests={self.request_count}>"

