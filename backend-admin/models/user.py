"""
User Model
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from sqlalchemy.orm import relationship
import secrets
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database import Base


class User(Base):
    """User model for authentication and authorization"""
    
    __tablename__ = "users"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Authentication
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    
    # API Key
    api_key = Column(String(64), unique=True, index=True)
    
    # Subscription
    plan = Column(String(20), default='free')  # free, pro, enterprise
    daily_quota = Column(Integer, default=100)
    scans_used_today = Column(Integer, default=0)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True))
    quota_reset_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    scans = relationship("Scan", back_populates="user", cascade="all, delete-orphan")
    
    def generate_api_key(self):
        """Generate new API key"""
        self.api_key = secrets.token_urlsafe(32)
        return self.api_key
    
    def check_quota(self) -> bool:
        """Check if user has remaining quota"""
        return self.scans_used_today < self.daily_quota
    
    def use_quota(self):
        """Use one scan from quota"""
        self.scans_used_today += 1
    
    def reset_quota(self):
        """Reset daily quota"""
        self.scans_used_today = 0
    
    def __repr__(self):
        return f"<User {self.username}>"

