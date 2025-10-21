"""
GeoIP Service
IP geolocation lookup
"""

import geoip2.database
import geoip2.errors
from typing import Optional, Dict
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings


class GeoIPService:
    """GeoIP lookup service"""
    
    def __init__(self):
        self.reader = None
        if os.path.exists(settings.GEOIP_DB_PATH):
            try:
                self.reader = geoip2.database.Reader(settings.GEOIP_DB_PATH)
                print(f"[OK] GeoIP database loaded: {settings.GEOIP_DB_PATH}")
            except Exception as e:
                print(f"[ERROR] Error loading GeoIP database: {e}")
        else:
            print(f"[WARNING] GeoIP database not found: {settings.GEOIP_DB_PATH}")
            print("   Download from: https://dev.maxmind.com/geoip/geolite2-free-geolocation-data")
    
    def lookup(self, ip_address: str) -> Optional[Dict]:
        """
        Lookup IP address geolocation
        
        Returns:
            Dict with location info or None
        """
        if not self.reader:
            return self._get_default_location(ip_address)
        
        try:
            response = self.reader.city(ip_address)
            return {
                "country": response.country.name or "Unknown",
                "country_code": response.country.iso_code or "XX",
                "region": response.subdivisions.most_specific.name if response.subdivisions else "Unknown",
                "city": response.city.name or "Unknown",
                "postal_code": response.postal.code or "",
                "latitude": response.location.latitude or 0.0,
                "longitude": response.location.longitude or 0.0,
                "timezone": response.location.time_zone or "UTC",
                "accuracy_radius": response.location.accuracy_radius
            }
        except geoip2.errors.AddressNotFoundError:
            return self._get_default_location(ip_address)
        except Exception as e:
            print(f"❌ GeoIP lookup error: {e}")
            return self._get_default_location(ip_address)
    
    def _get_default_location(self, ip_address: str) -> Dict:
        """Return default location for private/local IPs"""
        # Check if private IP
        if ip_address.startswith(('192.168.', '10.', '172.')) or ip_address == '127.0.0.1':
            return {
                "country": "Vietnam",
                "country_code": "VN",
                "region": "Ho Chi Minh",
                "city": "Ho Chi Minh City",
                "postal_code": "",
                "latitude": 10.8231,
                "longitude": 106.6297,
                "timezone": "Asia/Ho_Chi_Minh",
                "accuracy_radius": 0
            }
        
        return {
            "country": "Unknown",
            "country_code": "XX",
            "region": "Unknown",
            "city": "Unknown",
            "postal_code": "",
            "latitude": 0.0,
            "longitude": 0.0,
            "timezone": "UTC",
            "accuracy_radius": 0
        }


# Global instance
geoip_service = GeoIPService()

