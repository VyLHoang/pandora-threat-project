"""
WHOIS Service
Lookup WHOIS information for IP addresses and domains
"""

import whois
import ipaddress
from typing import Dict, Optional
from datetime import datetime


class WHOISService:
    """WHOIS lookup service"""
    
    def __init__(self):
        pass
    
    def lookup_whois(self, target: str) -> Dict:
        """
        Lookup WHOIS information for IP or domain
        
        Args:
            target: IP address or domain name
            
        Returns:
            Dictionary with WHOIS data or error information
        """
        try:
            # Check if target is IP address
            is_ip = self._is_ip_address(target)
            
            if is_ip:
                return self._lookup_ip_whois(target)
            else:
                return self._lookup_domain_whois(target)
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'target': target,
                'lookup_time': datetime.utcnow().isoformat()
            }
    
    def _is_ip_address(self, target: str) -> bool:
        """Check if target is a valid IP address"""
        try:
            ipaddress.ip_address(target)
            return True
        except ValueError:
            return False
    
    def _lookup_ip_whois(self, ip: str) -> Dict:
        """
        Lookup WHOIS for IP address
        Note: python-whois may not support all IP WHOIS queries perfectly
        """
        try:
            # For IP addresses, whois library has limited support
            # We'll try to get basic info
            w = whois.whois(ip)
            
            result = {
                'success': True,
                'target': ip,
                'target_type': 'ip',
                'lookup_time': datetime.utcnow().isoformat(),
                'raw_data': {}
            }
            
            # Extract available fields
            if hasattr(w, 'domain_name'):
                result['domain_name'] = w.domain_name
            if hasattr(w, 'registrar'):
                result['registrar'] = w.registrar
            if hasattr(w, 'whois_server'):
                result['whois_server'] = w.whois_server
            if hasattr(w, 'creation_date'):
                result['creation_date'] = str(w.creation_date) if w.creation_date else None
            if hasattr(w, 'expiration_date'):
                result['expiration_date'] = str(w.expiration_date) if w.expiration_date else None
            if hasattr(w, 'updated_date'):
                result['updated_date'] = str(w.updated_date) if w.updated_date else None
            if hasattr(w, 'name_servers'):
                result['name_servers'] = w.name_servers if w.name_servers else []
            if hasattr(w, 'org'):
                result['organization'] = w.org
            if hasattr(w, 'country'):
                result['country'] = w.country
            if hasattr(w, 'state'):
                result['state'] = w.state
            if hasattr(w, 'city'):
                result['city'] = w.city
            if hasattr(w, 'address'):
                result['address'] = w.address
            if hasattr(w, 'emails'):
                result['emails'] = w.emails if w.emails else []
                
            # Store raw text if available
            if hasattr(w, 'text'):
                result['raw_data']['text'] = w.text
                
            return result
            
        except Exception as e:
            # If WHOIS fails for IP, return minimal info
            return {
                'success': False,
                'target': ip,
                'target_type': 'ip',
                'error': f"WHOIS lookup failed: {str(e)}",
                'lookup_time': datetime.utcnow().isoformat(),
                'note': 'IP WHOIS may not be available for all addresses'
            }
    
    def _lookup_domain_whois(self, domain: str) -> Dict:
        """Lookup WHOIS for domain name"""
        try:
            w = whois.whois(domain)
            
            result = {
                'success': True,
                'target': domain,
                'target_type': 'domain',
                'lookup_time': datetime.utcnow().isoformat()
            }
            
            # Extract domain information
            if hasattr(w, 'domain_name'):
                result['domain_name'] = w.domain_name if isinstance(w.domain_name, str) else (w.domain_name[0] if w.domain_name else None)
            if hasattr(w, 'registrar'):
                result['registrar'] = w.registrar
            if hasattr(w, 'whois_server'):
                result['whois_server'] = w.whois_server
            if hasattr(w, 'creation_date'):
                # Handle both single date and list of dates
                creation = w.creation_date
                if isinstance(creation, list):
                    result['creation_date'] = str(creation[0]) if creation else None
                else:
                    result['creation_date'] = str(creation) if creation else None
            if hasattr(w, 'expiration_date'):
                expiration = w.expiration_date
                if isinstance(expiration, list):
                    result['expiration_date'] = str(expiration[0]) if expiration else None
                else:
                    result['expiration_date'] = str(expiration) if expiration else None
            if hasattr(w, 'updated_date'):
                updated = w.updated_date
                if isinstance(updated, list):
                    result['updated_date'] = str(updated[0]) if updated else None
                else:
                    result['updated_date'] = str(updated) if updated else None
            if hasattr(w, 'name_servers'):
                result['name_servers'] = w.name_servers if w.name_servers else []
            if hasattr(w, 'status'):
                result['status'] = w.status if isinstance(w.status, list) else [w.status] if w.status else []
            if hasattr(w, 'org'):
                result['organization'] = w.org
            if hasattr(w, 'country'):
                result['country'] = w.country
            if hasattr(w, 'state'):
                result['state'] = w.state
            if hasattr(w, 'city'):
                result['city'] = w.city
            if hasattr(w, 'address'):
                result['address'] = w.address
            if hasattr(w, 'emails'):
                result['emails'] = w.emails if isinstance(w.emails, list) else [w.emails] if w.emails else []
            if hasattr(w, 'dnssec'):
                result['dnssec'] = w.dnssec
                
            return result
            
        except Exception as e:
            return {
                'success': False,
                'target': domain,
                'target_type': 'domain',
                'error': f"WHOIS lookup failed: {str(e)}",
                'lookup_time': datetime.utcnow().isoformat()
            }


# Global instance
whois_service = WHOISService()

