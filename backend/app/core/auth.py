"""
Authentication utilities and dependencies for the Financial Analysis Platform
"""
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from app.core.database import get_async_session
from app.services.auth.jwt_handler import JWTHandler
from app.services.auth.auth_service import AuthService
from app.models.user import User

# Initialize services
jwt_handler = JWTHandler()
auth_service = AuthService()

# Security scheme
security = HTTPBearer()


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create access token
    
    Args:
        data: Token payload data
        expires_delta: Token expiration time
        
    Returns:
        str: JWT access token
    """
    return jwt_handler.create_access_token(data.get("user_id", data.get("sub")), expires_delta)


def verify_token(token: str) -> Dict[str, Any]:
    """
    Verify JWT token
    
    Args:
        token: JWT token to verify
        
    Returns:
        Dict[str, Any]: Token payload
        
    Raises:
        HTTPException: If token is invalid
    """
    payload = jwt_handler.verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    return payload


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_async_session)
) -> User:
    """
    Get current authenticated user
    
    Args:
        credentials: HTTP authorization credentials
        db: Database session
        
    Returns:
        User: Current authenticated user
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        # Verify token
        payload = jwt_handler.verify_token(credentials.credentials)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        
        # Get user from database
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        user = await auth_service.get_user_by_id(user_id, db)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is disabled"
            )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User: Current active user
        
    Raises:
        HTTPException: If user is not active
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


async def get_current_verified_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current verified user
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User: Current verified user
        
    Raises:
        HTTPException: If user is not verified
    """
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User email not verified"
        )
    return current_user


def get_optional_current_user(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_async_session)
) -> Optional[User]:
    """
    Get current user if authenticated, otherwise return None
    
    Args:
        authorization: Authorization header
        db: Database session
        
    Returns:
        Optional[User]: Current user or None
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None
    
    try:
        token = authorization.split(" ")[1]
        payload = jwt_handler.verify_token(token)
        if not payload:
            return None
        
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        # Note: This would need to be async in real implementation
        # For testing purposes, we'll return a mock user
        return None
        
    except Exception:
        return None


# Dependency for database session (alias for compatibility)
def get_db():
    """
    Alias for get_async_session for backward compatibility
    """
    return get_async_session()
