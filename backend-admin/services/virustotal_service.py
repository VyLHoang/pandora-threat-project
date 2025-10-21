"""
VirusTotal API Service
IP and File Hash scanning
"""

import requests
from typing import Optional, Dict
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from database.redis_client import redis_client


class VirusTotalService:
    """VirusTotal API integration"""
    
    def __init__(self):
        self.api_key = settings.VIRUSTOTAL_API_KEY
        self.base_url = settings.VIRUSTOTAL_API_URL
        self.headers = {
            "x-apikey": self.api_key
        }
    
    def scan_ip(self, ip_address: str, use_cache: bool = True) -> Optional[Dict]:
        """
        Scan IP address using VirusTotal
        
        Args:
            ip_address: IP address to scan
            use_cache: Whether to use cached results
        
        Returns:
            Dict with scan results or None
        """
        # Check cache first
        if use_cache:
            cache_key = f"vt:ip:{ip_address}"
            cached = redis_client.get_json(cache_key)
            if cached:
                print(f"[CACHE] Cache hit for IP: {ip_address}")
                return cached
        
        # Make API request
        try:
            url = f"{self.base_url}/ip_addresses/{ip_address}"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                result = self._parse_ip_response(data)
                
                # Cache result for 1 hour
                if use_cache:
                    cache_key = f"vt:ip:{ip_address}"
                    redis_client.set_json(cache_key, result, expire=3600)
                
                print(f"[OK] VirusTotal IP scan: {ip_address}")
                return result
            elif response.status_code == 404:
                print(f"[WARNING] IP not found in VirusTotal: {ip_address}")
                return {"error": "IP not found", "status": 404}
            else:
                print(f"[ERROR] VirusTotal API error: {response.status_code}")
                return {"error": f"API error: {response.status_code}"}
        
        except Exception as e:
            print(f"[ERROR] VirusTotal request error: {e}")
            return {"error": str(e)}
    
    def scan_file_hash(self, file_hash: str, use_cache: bool = True) -> Optional[Dict]:
        """
        Scan file hash using VirusTotal
        
        Args:
            file_hash: MD5, SHA1, or SHA256 hash
            use_cache: Whether to use cached results
        
        Returns:
            Dict with scan results or None
        """
        # Check cache first
        if use_cache:
            cache_key = f"vt:hash:{file_hash}"
            cached = redis_client.get_json(cache_key)
            if cached:
                print(f"[CACHE] Cache hit for hash: {file_hash}")
                return cached
        
        # Make API request
        try:
            url = f"{self.base_url}/files/{file_hash}"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                result = self._parse_file_response(data)
                
                # Cache result for 24 hours
                if use_cache:
                    cache_key = f"vt:hash:{file_hash}"
                    redis_client.set_json(cache_key, result, expire=86400)
                
                print(f"[OK] VirusTotal hash scan: {file_hash}")
                return result
            elif response.status_code == 404:
                print(f"[WARNING] Hash not found in VirusTotal: {file_hash}")
                return {"error": "Hash not found", "status": 404}
            else:
                print(f"[ERROR] VirusTotal API error: {response.status_code}")
                return {"error": f"API error: {response.status_code}"}
        
        except Exception as e:
            print(f"[ERROR] VirusTotal request error: {e}")
            return {"error": str(e)}
    
    def _parse_ip_response(self, data: Dict) -> Dict:
        """Parse VirusTotal IP response"""
        attributes = data.get("data", {}).get("attributes", {})
        stats = attributes.get("last_analysis_stats", {})
        results = attributes.get("last_analysis_results", {})
        
        malicious = stats.get("malicious", 0)
        suspicious = stats.get("suspicious", 0)
        total = sum(stats.values())
        
        # Parse individual engine results
        engine_results = []
        for engine_name, result in results.items():
            engine_results.append({
                "engine": engine_name,
                "category": result.get("category", "undetected"),
                "result": result.get("result", "clean"),
                "method": result.get("method", ""),
                "engine_version": result.get("engine_version", "")
            })
        
        # Sort by category (malicious first, then suspicious, then undetected)
        category_order = {"malicious": 0, "suspicious": 1, "undetected": 2, "harmless": 3, "timeout": 4}
        engine_results.sort(key=lambda x: category_order.get(x['category'], 999))
        
        return {
            "target": data.get("data", {}).get("id"),
            "is_malicious": malicious > 0 or suspicious > 0,
            "detection_count": malicious + suspicious,
            "total_engines": total,
            "stats": stats,
            "country": attributes.get("country"),
            "asn": attributes.get("asn"),
            "as_owner": attributes.get("as_owner"),
            "reputation": attributes.get("reputation", 0),
            "engine_results": engine_results[:50],  # Top 50 engines
            "raw_response": data
        }
    
    def _parse_file_response(self, data: Dict) -> Dict:
        """Parse VirusTotal file response"""
        attributes = data.get("data", {}).get("attributes", {})
        stats = attributes.get("last_analysis_stats", {})
        results = attributes.get("last_analysis_results", {})
        
        malicious = stats.get("malicious", 0)
        suspicious = stats.get("suspicious", 0)
        total = sum(stats.values())
        
        # Extract threat names
        threat_names = []
        engine_results = []
        for engine_name, result in results.items():
            if result.get("category") in ["malicious", "suspicious"]:
                if result.get("result"):
                    threat_names.append(result["result"])
            
            # Add all engine results
            engine_results.append({
                "engine": engine_name,
                "category": result.get("category", "undetected"),
                "result": result.get("result", "clean"),
                "method": result.get("method", ""),
                "engine_version": result.get("engine_version", "")
            })
        
        # Sort by category
        category_order = {"malicious": 0, "suspicious": 1, "undetected": 2, "harmless": 3, "timeout": 4}
        engine_results.sort(key=lambda x: category_order.get(x['category'], 999))
        
        return {
            "target": data.get("data", {}).get("id"),
            "is_malicious": malicious > 0 or suspicious > 0,
            "detection_count": malicious + suspicious,
            "total_engines": total,
            "stats": stats,
            "threat_names": list(set(threat_names))[:10],  # Unique, max 10
            "file_type": attributes.get("type_description"),
            "size": attributes.get("size"),
            "md5": attributes.get("md5"),
            "sha1": attributes.get("sha1"),
            "sha256": attributes.get("sha256"),
            "scan_date": attributes.get("last_analysis_date"),
            "engine_results": engine_results[:50],  # Top 50 engines
            "raw_response": data
        }


# Global instance
vt_service = VirusTotalService()

