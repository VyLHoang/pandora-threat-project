"""
Rate Limiting Utilities
Using Redis for distributed rate limiting
"""

from datetime import datetime, timedelta
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.redis_client import redis_client
from config import settings


class RateLimiter:
    """Rate limiter using Redis"""
    
    @staticmethod
    def check_rate_limit(identifier: str, limit: int, window: int = 60) -> tuple[bool, int]:
        """
        Check if request is within rate limit
        
        Args:
            identifier: Unique identifier (user_id, IP, etc.)
            limit: Maximum requests allowed
            window: Time window in seconds
        
        Returns:
            (is_allowed, remaining_quota)
        """
        key = f"rate_limit:{identifier}:{window}"
        
        # Get current count
        current = redis_client.get(key)
        
        if current is None:
            # First request in window
            redis_client.set(key, "1", expire=window)
            return True, limit - 1
        
        current = int(current)
        
        if current >= limit:
            # Limit exceeded
            return False, 0
        
        # Increment counter
        redis_client.increment(key)
        return True, limit - current - 1
    
    @staticmethod
    def check_daily_quota(user_id: int, daily_limit: int) -> tuple[bool, int]:
        """
        Check user's daily scan quota
        
        Returns:
            (has_quota, remaining)
        """
        today = datetime.utcnow().strftime("%Y-%m-%d")
        key = f"daily_quota:{user_id}:{today}"
        
        current = redis_client.get(key)
        
        if current is None:
            # First scan today
            redis_client.set(key, "1", expire=86400)  # 24 hours
            return True, daily_limit - 1
        
        current = int(current)
        
        if current >= daily_limit:
            return False, 0
        
        redis_client.increment(key)
        return True, daily_limit - current - 1
    
    @staticmethod
    def get_quota_info(user_id: int, daily_limit: int) -> dict:
        """Get quota information"""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        key = f"daily_quota:{user_id}:{today}"
        
        current = redis_client.get(key)
        used = int(current) if current else 0
        
        return {
            "daily_limit": daily_limit,
            "used_today": used,
            "remaining": max(0, daily_limit - used),
            "reset_at": datetime.utcnow().replace(
                hour=0, minute=0, second=0, microsecond=0
            ) + timedelta(days=1)
        }


# Global instance
rate_limiter = RateLimiter()

