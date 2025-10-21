"""
Attack Log Model
Store detected network attacks and intrusion attempts
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ARRAY, func
from sqlalchemy.dialects.postgresql import JSONB, INET
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database import Base


class AttackLog(Base):
    """Attack detection log"""
    __tablename__ = "attack_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Attacker Info
    source_ip = Column(INET, nullable=False, index=True)
    source_port = Column(Integer)
    
    # Target Info
    target_ip = Column(INET, nullable=False)
    target_port = Column(Integer, index=True)
    
    # Attack Classification
    attack_type = Column(String(50), index=True)  # 'port_scan', 'syn_flood', 'nmap', 'telnet_probe'
    severity = Column(String(20), default='medium')  # 'low', 'medium', 'high', 'critical'
    
    # Detection Details
    packet_count = Column(Integer, default=1)
    protocol = Column(String(10))  # 'TCP', 'UDP', 'ICMP'
    flags = Column(String(20))  # TCP flags: SYN, ACK, FIN, etc.
    payload_sample = Column(Text)  # First 200 bytes of payload
    
    # GeoIP Info
    country = Column(String(100))
    city = Column(String(100))
    latitude = Column(String(20))
    longitude = Column(String(20))
    
    # Tool Detection
    detected_tool = Column(String(50))  # 'nmap', 'masscan', 'telnet', 'unknown'
    confidence = Column(Integer, default=0)  # 0-100%
    
    # Metadata
    raw_packet_info = Column(JSONB)
    email_sent = Column(Boolean, default=False)
    blocked = Column(Boolean, default=False)
    
    # Timestamps
    first_seen = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    last_seen = Column(DateTime(timezone=True), server_default=func.now())
    detected_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<AttackLog {self.attack_type} from {self.source_ip}>"

