"""
Elasticsearch Service
Manage logging to Elasticsearch for IDS attacks and Honeypot activities
"""

from elasticsearch import Elasticsearch, helpers
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings


class ElasticsearchService:
    """Service for managing Elasticsearch logging and indices"""
    
    def __init__(self):
        """Initialize Elasticsearch client"""
        self.enabled = settings.ELASTICSEARCH_ENABLED
        self.retention_days = settings.ELASTICSEARCH_LOG_RETENTION_DAYS
        
        if not self.enabled:
            print("[ELASTICSEARCH] Service disabled in config")
            self.client = None
            return
        
        try:
            # Initialize Elasticsearch client
            if settings.ELASTICSEARCH_USERNAME and settings.ELASTICSEARCH_PASSWORD:
                self.client = Elasticsearch(
                    settings.ELASTICSEARCH_HOSTS,
                    basic_auth=(settings.ELASTICSEARCH_USERNAME, settings.ELASTICSEARCH_PASSWORD),
                    request_timeout=30,
                    max_retries=3,
                    retry_on_timeout=True
                )
            else:
                self.client = Elasticsearch(
                    settings.ELASTICSEARCH_HOSTS,
                    request_timeout=30,
                    max_retries=3,
                    retry_on_timeout=True
                )
            
            # Test connection
            if self.client.ping():
                print(f"[ELASTICSEARCH] ✓ Connected to {settings.ELASTICSEARCH_HOSTS}")
                print(f"[ELASTICSEARCH] Retention policy: {self.retention_days} days")
                
                # Create indices and ILM policies
                self._setup_indices()
            else:
                print("[ELASTICSEARCH] ✗ Failed to ping Elasticsearch")
                self.client = None
                
        except Exception as e:
            print(f"[ELASTICSEARCH] ✗ Connection error: {e}")
            self.client = None
    
    def _setup_indices(self):
        """Setup indices with mappings and ILM policies"""
        try:
            # Create ILM policy for log retention
            self._create_ilm_policy()
            
            # Create index templates
            self._create_honeypot_template()
            self._create_ids_template()
            
            print("[ELASTICSEARCH] ✓ Indices and templates configured")
            
        except Exception as e:
            print(f"[ELASTICSEARCH] Warning: Setup error: {e}")
    
    def _create_ilm_policy(self):
        """Create Index Lifecycle Management policy for log retention"""
        try:
            policy_name = "pandora-log-retention-policy"
            
            policy = {
                    "phases": {
                        "hot": {
                            "min_age": "0ms",
                            "actions": {
                                "rollover": {
                                    "max_age": "1d",
                                    "max_primary_shard_size": "50gb"
                                }
                            }
                        },
                        "delete": {
                            "min_age": f"{self.retention_days}d",
                            "actions": {
                                "delete": {}
                            }
                        }
                    }
                }
            
            # Create or update ILM policy
            self.client.ilm.put_lifecycle(name=policy_name, policy=policy)
            print(f"[ELASTICSEARCH] ✓ ILM policy created: {self.retention_days} days retention")
            
        except Exception as e:
            print(f"[ELASTICSEARCH] Warning: ILM policy creation failed: {e}")
    
    def _create_honeypot_template(self):
        """Create index template for honeypot logs"""
        try:
            template_name = "pandora-honeypot-template"
            index_pattern = f"{settings.ELASTICSEARCH_HONEYPOT_INDEX}-*"
            
            template = {
                "index_patterns": [index_pattern],
                "template": {
                    "settings": {
                        "number_of_shards": 1,
                        "number_of_replicas": 0,
                        "index.lifecycle.name": "pandora-log-retention-policy",
                        "index.lifecycle.rollover_alias": settings.ELASTICSEARCH_HONEYPOT_INDEX
                    },
                    "mappings": {
                        "properties": {
                            "@timestamp": {"type": "date"},
                            "user_id": {"type": "integer"},
                            "is_authenticated": {"type": "boolean"},
                            "session_id": {"type": "keyword"},
                            "ip_address": {"type": "ip"},
                            "user_agent": {"type": "text"},
                            "request_method": {"type": "keyword"},
                            "request_path": {"type": "keyword"},
                            "request_headers": {"type": "object", "enabled": False},
                            "request_body": {"type": "text"},
                            "response_status": {"type": "integer"},
                            "response_size": {"type": "integer"},
                            "activity_type": {"type": "keyword"},
                            "suspicious_score": {"type": "integer"},
                            "suspicious_reasons": {"type": "keyword"},
                            "geoip_country": {"type": "keyword"},
                            "geoip_city": {"type": "keyword"},
                            "geoip_location": {"type": "geo_point"}
                        }
                    }
                }
            }
            
            self.client.indices.put_index_template(name=template_name, body=template)
            print(f"[ELASTICSEARCH] ✓ Honeypot template created")
            
        except Exception as e:
            print(f"[ELASTICSEARCH] Warning: Honeypot template creation failed: {e}")
    
    def _create_ids_template(self):
        """Create index template for IDS attack logs"""
        try:
            template_name = "pandora-ids-template"
            index_pattern = f"{settings.ELASTICSEARCH_IDS_INDEX}-*"
            
            template = {
                "index_patterns": [index_pattern],
                "template": {
                    "settings": {
                        "number_of_shards": 1,
                        "number_of_replicas": 0,
                        "index.lifecycle.name": "pandora-log-retention-policy",
                        "index.lifecycle.rollover_alias": settings.ELASTICSEARCH_IDS_INDEX
                    },
                    "mappings": {
                        "properties": {
                            "@timestamp": {"type": "date"},
                            "source_ip": {"type": "ip"},
                            "source_port": {"type": "integer"},
                            "target_ip": {"type": "ip"},
                            "target_port": {"type": "integer"},
                            "attack_type": {"type": "keyword"},
                            "severity": {"type": "keyword"},
                            "packet_count": {"type": "integer"},
                            "protocol": {"type": "keyword"},
                            "flags": {"type": "keyword"},
                            "payload_sample": {"type": "text"},
                            "country": {"type": "keyword"},
                            "city": {"type": "keyword"},
                            "location": {"type": "geo_point"},
                            "detected_tool": {"type": "keyword"},
                            "confidence": {"type": "integer"},
                            "raw_packet_info": {"type": "object", "enabled": False}
                        }
                    }
                }
            }
            
            self.client.indices.put_index_template(name=template_name, body=template)
            print(f"[ELASTICSEARCH] ✓ IDS template created")
            
        except Exception as e:
            print(f"[ELASTICSEARCH] Warning: IDS template creation failed: {e}")
    
    def log_honeypot_activity(self, activity_data: Dict[str, Any]) -> bool:
        """
        Log honeypot activity to Elasticsearch
        
        Args:
            activity_data: Dictionary containing honeypot activity data
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.enabled or not self.client:
            return False
        
        try:
            # Get current date for index name (daily indices)
            date_suffix = datetime.now().strftime("%Y.%m.%d")
            index_name = f"{settings.ELASTICSEARCH_HONEYPOT_INDEX}-{date_suffix}"
            
            # Prepare document
            doc = {
                "@timestamp": activity_data.get('timestamp', datetime.now().isoformat()),
                "user_id": activity_data.get('user_id'),
                "is_authenticated": activity_data.get('is_authenticated', False),
                "session_id": activity_data.get('session_id'),
                "ip_address": activity_data.get('ip_address'),
                "user_agent": activity_data.get('user_agent'),
                "request_method": activity_data.get('request_method'),
                "request_path": activity_data.get('request_path'),
                "request_headers": activity_data.get('request_headers'),
                "request_body": activity_data.get('request_body'),
                "response_status": activity_data.get('response_status'),
                "response_size": activity_data.get('response_size'),
                "activity_type": activity_data.get('activity_type'),
                "suspicious_score": activity_data.get('suspicious_score', 0),
                "suspicious_reasons": activity_data.get('suspicious_reasons', []),
                "geoip_country": activity_data.get('geoip_country'),
                "geoip_city": activity_data.get('geoip_city'),
            }
            
            # Add geo_point if coordinates available
            if activity_data.get('geoip_lat') and activity_data.get('geoip_lon'):
                doc['geoip_location'] = {
                    "lat": float(activity_data['geoip_lat']),
                    "lon": float(activity_data['geoip_lon'])
                }
            
            # Index document
            self.client.index(index=index_name, document=doc)
            return True
            
        except Exception as e:
            print(f"[ELASTICSEARCH] Error logging honeypot activity: {e}")
            return False
    
    def log_attack(self, attack_data: Dict[str, Any]) -> bool:
        """
        Log IDS attack to Elasticsearch
        
        Args:
            attack_data: Dictionary containing attack data
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.enabled or not self.client:
            return False
        
        try:
            # Get current date for index name (daily indices)
            date_suffix = datetime.now().strftime("%Y.%m.%d")
            index_name = f"{settings.ELASTICSEARCH_IDS_INDEX}-{date_suffix}"
            
            # Prepare document
            doc = {
                "@timestamp": attack_data.get('detected_at', datetime.now().isoformat()),
                "source_ip": attack_data.get('source_ip'),
                "source_port": attack_data.get('source_port'),
                "target_ip": attack_data.get('target_ip'),
                "target_port": attack_data.get('target_port'),
                "attack_type": attack_data.get('attack_type'),
                "severity": attack_data.get('severity'),
                "packet_count": attack_data.get('packet_count', 1),
                "protocol": attack_data.get('protocol'),
                "flags": attack_data.get('flags'),
                "payload_sample": attack_data.get('payload_sample'),
                "country": attack_data.get('country'),
                "city": attack_data.get('city'),
                "detected_tool": attack_data.get('detected_tool'),
                "confidence": attack_data.get('confidence', 0),
                "raw_packet_info": attack_data.get('raw_packet_info'),
            }
            
            # Add geo_point if coordinates available
            if attack_data.get('latitude') and attack_data.get('longitude'):
                try:
                    doc['location'] = {
                        "lat": float(attack_data['latitude']),
                        "lon": float(attack_data['longitude'])
                    }
                except:
                    pass
            
            # Index document
            self.client.index(index=index_name, document=doc)
            return True
            
        except Exception as e:
            print(f"[ELASTICSEARCH] Error logging attack: {e}")
            return False
    
    def search_attacks(self, query: Dict[str, Any], size: int = 100) -> List[Dict]:
        """
        Search IDS attacks in Elasticsearch
        
        Args:
            query: Elasticsearch query DSL
            size: Number of results to return
            
        Returns:
            List of attack documents
        """
        if not self.enabled or not self.client:
            return []
        
        try:
            index_pattern = f"{settings.ELASTICSEARCH_IDS_INDEX}-*"
            result = self.client.search(index=index_pattern, body=query, size=size)
            return [hit['_source'] for hit in result['hits']['hits']]
        except Exception as e:
            print(f"[ELASTICSEARCH] Search error: {e}")
            return []
    
    def search_honeypot(self, query: Dict[str, Any], size: int = 100) -> List[Dict]:
        """
        Search honeypot activities in Elasticsearch
        
        Args:
            query: Elasticsearch query DSL
            size: Number of results to return
            
        Returns:
            List of honeypot documents
        """
        if not self.enabled or not self.client:
            return []
        
        try:
            index_pattern = f"{settings.ELASTICSEARCH_HONEYPOT_INDEX}-*"
            result = self.client.search(index=index_pattern, body=query, size=size)
            return [hit['_source'] for hit in result['hits']['hits']]
        except Exception as e:
            print(f"[ELASTICSEARCH] Search error: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get Elasticsearch statistics"""
        if not self.enabled or not self.client:
            return {"enabled": False}
        
        try:
            # Get cluster health
            health = self.client.cluster.health()
            
            # Get indices stats
            honeypot_pattern = f"{settings.ELASTICSEARCH_HONEYPOT_INDEX}-*"
            ids_pattern = f"{settings.ELASTICSEARCH_IDS_INDEX}-*"
            
            honeypot_count = self.client.count(index=honeypot_pattern).get('count', 0)
            ids_count = self.client.count(index=ids_pattern).get('count', 0)
            
            return {
                "enabled": True,
                "cluster_status": health['status'],
                "honeypot_logs_count": honeypot_count,
                "ids_attacks_count": ids_count,
                "retention_days": self.retention_days
            }
        except Exception as e:
            print(f"[ELASTICSEARCH] Stats error: {e}")
            return {"enabled": True, "error": str(e)}


# Global instance
elasticsearch_service = ElasticsearchService()

