"""
Redis client for caching and rate limiting
"""

import redis
from typing import Optional
import json
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings


class RedisClient:
    """Redis client wrapper"""
    
    def __init__(self):
        # Only set password if it's not empty
        redis_args = {
            'host': settings.REDIS_HOST,
            'port': settings.REDIS_PORT,
            'db': settings.REDIS_DB,
            'decode_responses': True
        }
        
        # Only add password if it exists
        if settings.REDIS_PASSWORD:
            redis_args['password'] = settings.REDIS_PASSWORD
        
        self.client = redis.Redis(**redis_args)
    
    def get(self, key: str) -> Optional[str]:
        """Get value by key"""
        try:
            return self.client.get(key)
        except Exception as e:
            print(f"Redis GET error: {e}")
            return None
    
    def set(self, key: str, value: str, expire: int = None):
        """Set value with optional expiration (seconds)"""
        try:
            if expire:
                self.client.setex(key, expire, value)
            else:
                self.client.set(key, value)
        except Exception as e:
            print(f"Redis SET error: {e}")
    
    def get_json(self, key: str) -> Optional[dict]:
        """Get JSON value"""
        value = self.get(key)
        if value:
            try:
                return json.loads(value)
            except:
                return None
        return None
    
    def set_json(self, key: str, value: dict, expire: int = None):
        """Set JSON value"""
        try:
            json_str = json.dumps(value)
            self.set(key, json_str, expire)
        except Exception as e:
            print(f"Redis SET JSON error: {e}")
    
    def delete(self, key: str):
        """Delete key"""
        try:
            self.client.delete(key)
        except Exception as e:
            print(f"Redis DELETE error: {e}")
    
    def increment(self, key: str, amount: int = 1) -> int:
        """Increment counter"""
        try:
            return self.client.incr(key, amount)
        except Exception as e:
            print(f"Redis INCR error: {e}")
            return 0
    
    def expire(self, key: str, seconds: int):
        """Set expiration on key"""
        try:
            self.client.expire(key, seconds)
        except Exception as e:
            print(f"Redis EXPIRE error: {e}")
    
    def exists(self, key: str) -> bool:
        """Check if key exists"""
        try:
            return self.client.exists(key) > 0
        except Exception as e:
            print(f"Redis EXISTS error: {e}")
            return False
    
    def ping(self) -> bool:
        """Check Redis connection"""
        try:
            return self.client.ping()
        except Exception as e:
            print(f"Redis PING error: {e}")
            return False


# Global Redis client instance
redis_client = RedisClient()

