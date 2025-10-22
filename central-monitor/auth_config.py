"""
Authentication Configuration for Central Monitor
Single admin account for secure access to port 27009
"""

import bcrypt
from typing import Optional

class AuthConfig:
    """Authentication configuration with single admin account"""
    
    # Admin credentials (customize these)
    ADMIN_USERNAME = "admin"
    # Default password: "admin123" - Change this in production!
    # To generate new hash: bcrypt.hashpw(b"your_password", bcrypt.gensalt()).decode()
    ADMIN_PASSWORD_HASH = "$2b$12$jJ6KZrWJ2lfL8hSa7Q.XU.azBL4waumOASDlDWdj8bnZlcRioLi9C"  # "admin123"
    
    # Session configuration
    SESSION_SECRET_KEY = "change-this-secret-key-in-production-very-long-random-string"
    SESSION_COOKIE_NAME = "pandora_admin_session"
    SESSION_PERMANENT = True
    SESSION_LIFETIME_HOURS = 24
    
    @classmethod
    def verify_password(cls, username: str, password: str) -> bool:
        """
        Verify username and password against stored credentials
        
        Args:
            username: Username to check
            password: Plain text password to verify
            
        Returns:
            bool: True if credentials are valid
        """
        # Check username
        if username != cls.ADMIN_USERNAME:
            return False
        
        # Verify password hash
        try:
            password_bytes = password.encode('utf-8')
            hash_bytes = cls.ADMIN_PASSWORD_HASH.encode('utf-8')
            return bcrypt.checkpw(password_bytes, hash_bytes)
        except Exception as e:
            print(f"[AUTH ERROR] Password verification failed: {e}")
            return False
    
    @classmethod
    def generate_password_hash(cls, password: str) -> str:
        """
        Generate bcrypt hash for a new password
        Use this to create new password hashes for ADMIN_PASSWORD_HASH
        
        Args:
            password: Plain text password
            
        Returns:
            str: Bcrypt hash string
        """
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        hash_bytes = bcrypt.hashpw(password_bytes, salt)
        return hash_bytes.decode('utf-8')


# Helper function for generating new password hashes
if __name__ == '__main__':
    print("=== Password Hash Generator ===")
    print("\nCurrent admin credentials:")
    print(f"Username: {AuthConfig.ADMIN_USERNAME}")
    print(f"Password Hash: {AuthConfig.ADMIN_PASSWORD_HASH}")
    print("\nTo generate a new password hash:")
    new_password = input("Enter new password: ")
    new_hash = AuthConfig.generate_password_hash(new_password)
    print(f"\nNew password hash: {new_hash}")
    print("\nUpdate ADMIN_PASSWORD_HASH in auth_config.py with this hash")

