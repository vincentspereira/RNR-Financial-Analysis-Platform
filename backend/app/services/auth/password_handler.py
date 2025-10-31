"""
Password handling utilities for secure authentication
"""
from passlib.context import CryptContext


class PasswordHandler:
    """
    Handles password hashing and verification using bcrypt
    """
    
    def __init__(self):
        """Initialize password context with bcrypt"""
        self.pwd_context = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto"
        )
    
    def hash_password(self, password: str) -> str:
        """
        Hash a password using bcrypt
        
        Args:
            password: Plain text password to hash
            
        Returns:
            Hashed password string
        """
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash
        
        Args:
            plain_password: Plain text password to verify
            hashed_password: Stored hashed password
            
        Returns:
            True if password matches, False otherwise
        """
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def needs_update(self, hashed_password: str) -> bool:
        """
        Check if password hash needs to be updated
        
        Args:
            hashed_password: Stored hashed password
            
        Returns:
            True if hash needs updating, False otherwise
        """
        return self.pwd_context.needs_update(hashed_password)


# Global password handler instance
password_handler = PasswordHandler()