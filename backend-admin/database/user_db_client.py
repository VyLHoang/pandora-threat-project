"""
User Database Client for Admin Backend
Admin có quyền READ-ONLY vào User Database để monitoring
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
import sys
import os

# Import config
from config import settings


# Create engine for User Database (Read-only connection)
user_engine = create_engine(
    settings.USER_DATABASE_URL,
    echo=settings.DB_ECHO,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10
)

UserDBSession = sessionmaker(autocommit=False, autoflush=False, bind=user_engine)


@contextmanager
def get_user_db_session() -> Session:
    """
    Context manager để lấy session từ User Database
    Admin chỉ có quyền READ, không được WRITE vào User DB
    """
    session = UserDBSession()
    try:
        yield session
    finally:
        session.close()


def get_user_db() -> Session:
    """
    Dependency cho FastAPI routes
    Sử dụng cho các endpoint cần đọc dữ liệu từ User DB
    """
    db = UserDBSession()
    try:
        yield db
    finally:
        db.close()


# Import User models để Admin có thể query
# Lưu ý: Chỉ import models, KHÔNG import routes hay services từ User Backend
try:
    # Add backend-user to path
    user_backend_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        'backend-user'
    )
    if user_backend_path not in sys.path:
        sys.path.insert(0, user_backend_path)
    
    # Import User models
    from models.user import User as UserModel
    from models.scan import Scan, ScanResult
    
    # ScanHistory không tồn tại trong User Backend
    ScanHistory = None
    
    print("[OK] User DB models imported successfully")
    
except ImportError as e:
    print(f"[WARNING] Could not import User models: {e}")
    print("[INFO] Admin will not have access to User DB structure")
    UserModel = None
    Scan = None
    ScanResult = None


def test_user_db_connection():
    """Test connection to User Database"""
    try:
        with get_user_db_session() as session:
            # Try to count users
            if UserModel:
                user_count = session.query(UserModel).count()
                print(f"[OK] Connected to User DB - Found {user_count} users")
                return True
            else:
                print("[WARNING] User models not available")
                return False
    except Exception as e:
        print(f"[ERROR] Cannot connect to User DB: {e}")
        return False


if __name__ == "__main__":
    print("Testing User Database connection from Admin Backend...")
    test_user_db_connection()

