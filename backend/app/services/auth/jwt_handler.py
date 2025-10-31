"""
JWT token handling for authentication and authorization
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Union
from uuid import UUID

from jose import JWTError, jwt
from pydantic import ValidationError

from app.core.config import settings


class JWTHandler:
    """
    Handles JWT token creation, validation, and management
    """
    
    def __init__(self):
        """Initialize JWT handler with configuration"""
        self.secret_key = settings.SECRET_KEY
        self.algorithm = settings.ALGORITHM
        self.access_token_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        self.refresh_token_expire_days = 7  # Refresh tokens expire in 7 days
    
    def create_access_token(
        self, 
        subject: Union[str, UUID], 
        expires_delta: Optional[timedelta] = None,
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new access token
        
        Args:
            subject: User ID or identifier
            expires_delta: Custom expiration time
            additional_claims: Additional claims to include in token
            
        Returns:
            Encoded JWT access token
        """
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=self.access_token_expire_minutes
            )
        
        # Convert UUID to string if necessary
        if isinstance(subject, UUID):
            subject = str(subject)
        
        # Base claims
        to_encode = {
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "sub": subject,
            "type": "access"
        }
        
        # Add additional claims if provided
        if additional_claims:
            to_encode.update(additional_claims)
        
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def create_refresh_token(
        self, 
        subject: Union[str, UUID],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a new refresh token
        
        Args:
            subject: User ID or identifier
            expires_delta: Custom expiration time
            
        Returns:
            Encoded JWT refresh token
        """
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(days=self.refresh_token_expire_days)
        
        # Convert UUID to string if necessary
        if isinstance(subject, UUID):
            subject = str(subject)
        
        to_encode = {
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "sub": subject,
            "type": "refresh"
        }
        
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
        """
        Verify and decode a JWT token
        
        Args:
            token: JWT token to verify
            token_type: Expected token type ('access' or 'refresh')
            
        Returns:
            Decoded token payload if valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm]
            )
            
            # Check token type
            if payload.get("type") != token_type:
                return None
            
            # Check expiration
            exp = payload.get("exp")
            if exp is None:
                return None
            
            if datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
                return None
            
            return payload
            
        except (JWTError, ValidationError, ValueError):
            return None
    
    def get_subject_from_token(self, token: str) -> Optional[str]:
        """
        Extract subject (user ID) from token without full verification
        
        Args:
            token: JWT token
            
        Returns:
            Subject string if extractable, None otherwise
        """
        try:
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm],
                options={"verify_exp": False}  # Don't verify expiration for this check
            )
            return payload.get("sub")
        except (JWTError, ValidationError):
            return None
    
    def is_token_expired(self, token: str) -> bool:
        """
        Check if token is expired
        
        Args:
            token: JWT token to check
            
        Returns:
            True if expired, False if valid or invalid format
        """
        try:
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm],
                options={"verify_exp": False}
            )
            
            exp = payload.get("exp")
            if exp is None:
                return True
            
            return datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc)
            
        except (JWTError, ValidationError):
            return True
    
    def get_token_expiration(self, token: str) -> Optional[datetime]:
        """
        Get token expiration time
        
        Args:
            token: JWT token
            
        Returns:
            Expiration datetime if valid token, None otherwise
        """
        try:
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm],
                options={"verify_exp": False}
            )
            
            exp = payload.get("exp")
            if exp is None:
                return None
            
            return datetime.fromtimestamp(exp, tz=timezone.utc)
            
        except (JWTError, ValidationError):
            return None
    
    def create_token_pair(self, subject: Union[str, UUID]) -> Dict[str, str]:
        """
        Create both access and refresh tokens
        
        Args:
            subject: User ID or identifier
            
        Returns:
            Dictionary with access_token and refresh_token
        """
        access_token = self.create_access_token(subject)
        refresh_token = self.create_refresh_token(subject)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }


# Global JWT handler instance
jwt_handler = JWTHandler()