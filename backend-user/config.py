"""
Configuration Settings
Load from environment variables
"""

from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "Pandora Threat Intelligence"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "change-this-secret-key-in-production"
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Database (User DB - Port 5433)
    DATABASE_URL: str = "postgresql+psycopg://pandora_user:pandora_user_pass_2024@localhost:5433/pandora_user_db"
    DB_ECHO: bool = False
    
    # Redis (User Redis - Port 6380)
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6380
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    
    # VirusTotal
    VIRUSTOTAL_API_KEY: str = ""
    VIRUSTOTAL_API_URL: str = "https://www.virustotal.com/api/v3"
    
    # JWT
    JWT_SECRET_KEY: str = "change-this-jwt-secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    FREE_TIER_DAILY_LIMIT: int = 100
    PRO_TIER_DAILY_LIMIT: int = 1000
    ENTERPRISE_TIER_DAILY_LIMIT: int = 10000
    
    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:22002"
    
    # GeoIP
    GEOIP_DB_PATH: str = os.path.join(os.path.dirname(__file__), "GeoLite2-City.mmdb")
    
    # Email
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "noreply@pandora.com"
    
    # Monitoring
    CENTRAL_MONITOR_URL: str = "http://localhost:22002/api/logs"
    ENABLE_MONITORING: bool = True
    
    # Elasticsearch
    ELASTICSEARCH_HOSTS: List[str] = ["http://localhost:9200"]
    ELASTICSEARCH_USERNAME: str = ""
    ELASTICSEARCH_PASSWORD: str = ""
    ELASTICSEARCH_LOG_RETENTION_DAYS: int = 90
    ELASTICSEARCH_HONEYPOT_INDEX: str = "pandora-honeypot-logs"
    ELASTICSEARCH_IDS_INDEX: str = "pandora-ids-attacks"
    ELASTICSEARCH_ENABLED: bool = True
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins into list"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    @property
    def redis_url(self) -> str:
        """Build Redis URL"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields from environment variables


# Global settings instance
settings = Settings()

