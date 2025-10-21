"""
Database connection and session management
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings

from config import settings as main_settings

# Import models to ensure they are registered
def import_models():
    """Import all models for table creation"""
    try:
        from models.user import User
        from models.scan import Scan, ScanResult
        from models.attack import AttackLog
        from models.honeypot import HoneypotLog, HoneypotSession
    except ImportError as e:
        print(f"[WARNING] Could not import some models: {e}")

# Create engine with database-specific settings
def create_database_engine():
    """Create database engine with appropriate settings for database type"""
    db_url = main_settings.DATABASE_URL

    if db_url.startswith('sqlite'):
        # SQLite settings
        return create_engine(
            db_url,
            echo=main_settings.DB_ECHO,
            connect_args={'check_same_thread': False}  # Allow multiple threads for SQLite
        )
    else:
        # PostgreSQL settings
        return create_engine(
            db_url,
            echo=main_settings.DB_ECHO,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20
        )

# Create engine
engine = create_database_engine()

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for getting database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database - create all tables
    """
    import_models()  # Import all models first
    Base.metadata.create_all(bind=engine)
    print("[OK] Database tables created successfully")


def drop_db():
    """
    Drop all tables - use with caution!
    """
    Base.metadata.drop_all(bind=engine)
    print("[WARNING] All tables dropped")

