"""
Authentication service for user management and session handling
"""
import hashlib
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.models.audit import AuditLog
from app.models.user import User, UserSession
from app.services.auth.jwt_handler import jwt_handler
from app.services.auth.password_handler import password_handler


class AuthService:
    """
    Main authentication service handling user operations
    """
    
    async def register_user(
        self,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        db: AsyncSession,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[Optional[User], Optional[str]]:
        """
        Register a new user
        
        Args:
            email: User email address
            password: Plain text password
            first_name: User's first name
            last_name: User's last name
            db: Database session
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            Tuple of (User object, error message)
        """
        try:
            # Check if user already exists
            existing_user = await self.get_user_by_email(email, db)
            if existing_user:
                return None, "User with this email already exists"
            
            # Hash password
            hashed_password = password_handler.hash_password(password)
            
            # Create new user
            new_user = User(
                email=email.lower().strip(),
                password_hash=hashed_password,
                first_name=first_name.strip(),
                last_name=last_name.strip(),
                is_active=True,
                is_verified=False  # Email verification required
            )
            
            db.add(new_user)
            await db.flush()  # Get the user ID
            
            # Create audit log
            audit_log = AuditLog.create_log(
                action="user_register",
                resource_type="user",
                user_id=new_user.id,
                resource_id=new_user.id,
                new_values={
                    "email": email,
                    "first_name": first_name,
                    "last_name": last_name
                },
                ip_address=ip_address,
                user_agent=user_agent,
                compliance_category="GDPR"
            )
            db.add(audit_log)
            
            await db.commit()
            return new_user, None
            
        except Exception as e:
            await db.rollback()
            return None, f"Registration failed: {str(e)}"
    
    async def authenticate_user(
        self,
        email: str,
        password: str,
        db: AsyncSession,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[Optional[User], Optional[str]]:
        """
        Authenticate user credentials
        
        Args:
            email: User email address
            password: Plain text password
            db: Database session
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            Tuple of (User object, error message)
        """
        try:
            # Get user by email
            user = await self.get_user_by_email(email, db)
            if not user:
                # Create audit log for failed login
                audit_log = AuditLog.create_log(
                    action="login_failed",
                    resource_type="user",
                    audit_metadata={"reason": "user_not_found", "email": email},
                    ip_address=ip_address,
                    user_agent=user_agent,
                    success=False,
                    compliance_category="SOX"
                )
                db.add(audit_log)
                await db.commit()
                return None, "Invalid email or password"
            
            # Check if user is active
            if not user.is_active:
                audit_log = AuditLog.create_log(
                    action="login_failed",
                    resource_type="user",
                    user_id=user.id,
                    audit_metadata={"reason": "account_inactive"},
                    ip_address=ip_address,
                    user_agent=user_agent,
                    success=False,
                    compliance_category="SOX"
                )
                db.add(audit_log)
                await db.commit()
                return None, "Account is inactive"
            
            # Verify password
            if not password_handler.verify_password(password, user.password_hash):
                audit_log = AuditLog.create_log(
                    action="login_failed",
                    resource_type="user",
                    user_id=user.id,
                    audit_metadata={"reason": "invalid_password"},
                    ip_address=ip_address,
                    user_agent=user_agent,
                    success=False,
                    compliance_category="SOX"
                )
                db.add(audit_log)
                await db.commit()
                return None, "Invalid email or password"
            
            # Update last login
            user.last_login = datetime.now(timezone.utc)
            
            # Create successful login audit log
            audit_log = AuditLog.create_log(
                action="login_success",
                resource_type="user",
                user_id=user.id,
                ip_address=ip_address,
                user_agent=user_agent,
                compliance_category="SOX"
            )
            db.add(audit_log)
            
            await db.commit()
            return user, None
            
        except Exception as e:
            await db.rollback()
            return None, f"Authentication failed: {str(e)}"
    
    async def create_user_session(
        self,
        user: User,
        db: AsyncSession,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        device_fingerprint: Optional[str] = None
    ) -> Tuple[Optional[Dict[str, str]], Optional[str]]:
        """
        Create a new user session with tokens
        
        Args:
            user: User object
            db: Database session
            ip_address: Client IP address
            user_agent: Client user agent
            device_fingerprint: Device fingerprint for security
            
        Returns:
            Tuple of (token dictionary, error message)
        """
        try:
            # Create token pair
            tokens = jwt_handler.create_token_pair(user.id)
            
            # Hash tokens for storage
            access_token_hash = hashlib.sha256(
                tokens["access_token"].encode()
            ).hexdigest()
            refresh_token_hash = hashlib.sha256(
                tokens["refresh_token"].encode()
            ).hexdigest()
            
            # Get token expiration times
            access_exp = jwt_handler.get_token_expiration(tokens["access_token"])
            refresh_exp = jwt_handler.get_token_expiration(tokens["refresh_token"])
            
            # Create session record
            session = UserSession(
                user_id=user.id,
                token_hash=access_token_hash,
                refresh_token_hash=refresh_token_hash,
                expires_at=access_exp,
                refresh_expires_at=refresh_exp,
                ip_address=ip_address,
                user_agent=user_agent,
                device_fingerprint=device_fingerprint,
                is_active=True
            )
            
            db.add(session)
            
            # Create audit log
            audit_log = AuditLog.create_log(
                action="session_created",
                resource_type="user_session",
                user_id=user.id,
                resource_id=session.id,
                ip_address=ip_address,
                user_agent=user_agent,
                session_id=str(session.id),
                compliance_category="SOX"
            )
            db.add(audit_log)
            
            await db.commit()
            
            # Add expiration info to tokens
            tokens.update({
                "expires_in": jwt_handler.access_token_expire_minutes * 60,
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "is_active": user.is_active,
                    "is_verified": user.is_verified,
                    "subscription_tier": user.subscription_tier,
                    "created_at": user.created_at.isoformat(),
                    "last_login": user.last_login.isoformat() if user.last_login else None
                }
            })
            
            return tokens, None
            
        except Exception as e:
            await db.rollback()
            return None, f"Session creation failed: {str(e)}"
    
    async def refresh_token(
        self,
        refresh_token: str,
        db: AsyncSession,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[Optional[Dict[str, str]], Optional[str]]:
        """
        Refresh access token using refresh token
        
        Args:
            refresh_token: Refresh token
            db: Database session
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            Tuple of (new token dictionary, error message)
        """
        try:
            # Verify refresh token
            payload = jwt_handler.verify_token(refresh_token, "refresh")
            if not payload:
                return None, "Invalid or expired refresh token"
            
            user_id = UUID(payload["sub"])
            
            # Find session with this refresh token
            refresh_token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
            
            stmt = select(UserSession).where(
                UserSession.refresh_token_hash == refresh_token_hash,
                UserSession.is_active == True
            )
            result = await db.execute(stmt)
            session = result.scalar_one_or_none()
            
            if not session or session.user_id != user_id:
                return None, "Invalid refresh token"
            
            # Get user
            user = await self.get_user_by_id(user_id, db)
            if not user or not user.is_active:
                return None, "User not found or inactive"
            
            # Create new access token
            new_access_token = jwt_handler.create_access_token(user.id)
            new_access_token_hash = hashlib.sha256(
                new_access_token.encode()
            ).hexdigest()
            
            # Update session
            session.token_hash = new_access_token_hash
            session.expires_at = jwt_handler.get_token_expiration(new_access_token)
            session.last_used_at = datetime.now(timezone.utc)
            
            # Create audit log
            audit_log = AuditLog.create_log(
                action="token_refreshed",
                resource_type="user_session",
                user_id=user.id,
                resource_id=session.id,
                ip_address=ip_address,
                user_agent=user_agent,
                session_id=str(session.id),
                compliance_category="SOX"
            )
            db.add(audit_log)
            
            await db.commit()
            
            return {
                "access_token": new_access_token,
                "refresh_token": refresh_token,  # Keep same refresh token
                "token_type": "bearer",
                "expires_in": jwt_handler.access_token_expire_minutes * 60
            }, None
            
        except Exception as e:
            await db.rollback()
            return None, f"Token refresh failed: {str(e)}"
    
    async def logout_user(
        self,
        access_token: str,
        db: AsyncSession,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Logout user by revoking session
        
        Args:
            access_token: Access token to revoke
            db: Database session
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            Tuple of (success boolean, error message)
        """
        try:
            # Get user ID from token
            user_id_str = jwt_handler.get_subject_from_token(access_token)
            if not user_id_str:
                return False, "Invalid token"
            
            user_id = UUID(user_id_str)
            
            # Find and revoke session
            access_token_hash = hashlib.sha256(access_token.encode()).hexdigest()
            
            stmt = select(UserSession).where(
                UserSession.token_hash == access_token_hash,
                UserSession.user_id == user_id,
                UserSession.is_active == True
            )
            result = await db.execute(stmt)
            session = result.scalar_one_or_none()
            
            if session:
                session.revoke()
                
                # Create audit log
                audit_log = AuditLog.create_log(
                    action="logout",
                    resource_type="user_session",
                    user_id=user_id,
                    resource_id=session.id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    session_id=str(session.id),
                    compliance_category="SOX"
                )
                db.add(audit_log)
                
                await db.commit()
            
            return True, None
            
        except Exception as e:
            await db.rollback()
            return False, f"Logout failed: {str(e)}"
    
    async def get_user_by_email(self, email: str, db: AsyncSession) -> Optional[User]:
        """Get user by email address"""
        stmt = select(User).where(User.email == email.lower().strip())
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_user_by_id(self, user_id: UUID, db: AsyncSession) -> Optional[User]:
        """Get user by ID"""
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def verify_session(
        self, 
        access_token: str, 
        db: AsyncSession
    ) -> Optional[User]:
        """
        Verify session and return user if valid
        
        Args:
            access_token: Access token to verify
            db: Database session
            
        Returns:
            User object if session is valid, None otherwise
        """
        try:
            # Verify token format and expiration
            payload = jwt_handler.verify_token(access_token, "access")
            if not payload:
                return None
            
            user_id = UUID(payload["sub"])
            
            # Check if session exists and is active
            access_token_hash = hashlib.sha256(access_token.encode()).hexdigest()
            
            stmt = select(UserSession).where(
                UserSession.token_hash == access_token_hash,
                UserSession.user_id == user_id,
                UserSession.is_active == True
            )
            result = await db.execute(stmt)
            session = result.scalar_one_or_none()
            
            if not session:
                return None
            
            # Update last used time
            session.update_last_used()
            
            # Get and return user
            user = await self.get_user_by_id(user_id, db)
            if user and user.is_active:
                await db.commit()
                return user
            
            return None
            
        except Exception:
            return None


# Global auth service instance
auth_service = AuthService()

# Module-level functions for backward compatibility
async def register_user(email: str, password: str, first_name: str, last_name: str, db, ip_address: Optional[str] = None, user_agent: Optional[str] = None):
    """Register a new user"""
    return await auth_service.register_user(email, password, first_name, last_name, db, ip_address, user_agent)

async def authenticate_user(email: str, password: str, db, ip_address: Optional[str] = None, user_agent: Optional[str] = None):
    """Authenticate user"""
    return await auth_service.authenticate_user(email, password, db, ip_address, user_agent)

async def get_user_by_id(user_id, db):
    """Get user by ID"""
    return await auth_service.get_user_by_id(user_id, db)