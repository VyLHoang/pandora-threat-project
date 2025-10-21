"""
Email Alert Service
Send email notifications for security events
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings

def send_attack_alert(attack_log):
    """Send email alert for detected attack"""
    
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        print("[WARNING] SMTP not configured, skipping email")
        return False
    
    try:
        # Email content
        subject = f"[SECURITY ALERT] {attack_log.attack_type.upper()} detected from {attack_log.source_ip}"
        
        body = f"""
PANDORA SECURITY PLATFORM - INTRUSION ALERT

Attack Detected: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

ATTACKER INFORMATION:
- IP Address: {attack_log.source_ip}
- Port: {attack_log.source_port}
- Country: {attack_log.country}
- City: {attack_log.city}
- Location: {attack_log.latitude}, {attack_log.longitude}

ATTACK DETAILS:
- Type: {attack_log.attack_type}
- Severity: {attack_log.severity.upper()}
- Tool Detected: {attack_log.detected_tool}
- Confidence: {attack_log.confidence}%
- Protocol: {attack_log.protocol}
- Flags: {attack_log.flags}

TARGET:
- IP: {attack_log.target_ip}
- Port: {attack_log.target_port}

PACKET INFO:
- Count: {attack_log.packet_count}
- Payload Sample: {attack_log.payload_sample[:100] if attack_log.payload_sample else 'N/A'}...

TIME:
- First Seen: {attack_log.first_seen}
- Last Seen: {attack_log.last_seen}

---
This is an automated alert from Pandora IDS
Dashboard: http://localhost:3000/attacks
        """
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = settings.EMAIL_FROM
        msg['To'] = settings.SMTP_USER  # Send to yourself
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        
        print(f"[EMAIL] Alert sent for {attack_log.attack_type} from {attack_log.source_ip}")
        
        # Update log
        from database.database import SessionLocal
        db = SessionLocal()
        try:
            attack_log.email_sent = True
            db.commit()
        finally:
            db.close()
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to send email: {e}")
        return False

