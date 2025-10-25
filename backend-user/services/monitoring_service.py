"""
Central Monitoring Integration Service
Forward logs to central monitoring port
"""

import requests
import threading
from datetime import datetime
from typing import Dict, Optional
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings


class MonitoringService:
    """Service to forward logs to central monitoring"""
    
    def __init__(self):
        self.enabled = settings.ENABLE_MONITORING
        self.central_url = settings.CENTRAL_MONITOR_URL
        
    def log_request(self, data: Dict) -> None:
        """
        Forward request log to central monitoring
        
        Args:
            data: Request data including method, path, ip, etc.
        """
        if not self.enabled:
            return
        
        try:
            # Enhance data with platform info
            log_entry = {
                **data,
                'platform': 'pandora',
                'service': data.get('service', 'backend'),
                'timestamp': data.get('timestamp', datetime.utcnow().isoformat())
            }
            
            # Send to central monitor (non-blocking in thread)
            thread = threading.Thread(target=self._send_sync, args=(log_entry,), daemon=True)
            thread.start()
            
        except Exception as e:
            # Fail silently - monitoring should not break main app
            print(f"[MONITOR] Failed to send log: {e}")
    
    def _send_sync(self, data: Dict) -> None:
        """Send log in background thread"""
        try:
            # Add API key header
            headers = {
                'Content-Type': 'application/json',
                'X-API-Key': settings.CENTRAL_MONITOR_API_KEY
            }
            
            response = requests.post(
                self.central_url,
                json=data,
                headers=headers,
                timeout=5  # Longer timeout for reliability
            )
            if response.status_code == 200:
                print(f"[MONITOR] Logged: {data.get('method')} {data.get('path')}")
            else:
                print(f"[MONITOR] Failed to log: {response.status_code}")
        except requests.exceptions.RequestException as e:
            # Central monitor might be down - that's ok
            print(f"[MONITOR] Connection failed: {e}")
            pass
    
    def log_scan(self, scan_data: Dict) -> None:
        """Log scan activity"""
        self.log_request({
            'service': 'scanner',
            'action': 'scan',
            'scan_type': scan_data.get('scan_type'),
            'target': scan_data.get('target'),
            'user_id': scan_data.get('user_id'),
            'result': scan_data.get('result'),
            'method': 'POST',
            'path': f"/scan/{scan_data.get('scan_type')}"
        })
    
    def log_auth(self, auth_data: Dict) -> None:
        """Log authentication activity"""
        self.log_request({
            'service': 'auth',
            'action': auth_data.get('action'),  # login, register, logout
            'user_id': auth_data.get('user_id'),
            'email': auth_data.get('email'),
            'success': auth_data.get('success'),
            'method': 'POST',
            'path': f"/auth/{auth_data.get('action')}"
        })
    
    def log_database(self, db_data: Dict) -> None:
        """Log database operations"""
        self.log_request({
            'service': 'database',
            'action': db_data.get('action'),
            'table': db_data.get('table'),
            'query_time': db_data.get('query_time'),
            'method': 'DB',
            'path': f"/db/{db_data.get('table')}"
        })


# Global monitoring service instance
monitoring_service = MonitoringService()

