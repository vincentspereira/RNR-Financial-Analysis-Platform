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
from app.core.security import SecurityConfig
from app.models.audit import AuditLog
from app.models.user import User, UserSession
from app.services.auth.jwt_handler import jwt_handler
from app.core.logging import get_logger
from app.services.auth.password_handler import password_handler

logger = get_logger("app.auth.service")


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
        """Register a new user"""
        try:
            existing_user = await self.get_user_by_email(email, db)
            if existing_user:
                return None, "User with this email already exists"

            hashed_password = password_handler.hash_password(password)

            new_user = User(
                email=email.lower().strip(),
                password_hash=hashed_password,
                first_name=first_name.strip(),
                last_name=last_name.strip(),
                is_active=True,
                is_verified=False
            )

            db.add(new_user)
            await db.flush()

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
            logger.error(f"Registration failed: {str(e)}", exc_info=True)
            return None, "Registration failed. Please try again."

    async def authenticate_user(
        self,
        email: str,
        password: str,
        db: AsyncSession,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[Optional[User], Optional[str]]:
        """Authenticate user credentials with account lockout protection"""
        try:
            # Check account lockout before proceeding
            lockout_key = f"login_attempts:{email.lower().strip()}"
            attempts = await self._get_failed_attempts(lockout_key)

            if attempts >= SecurityConfig.MAX_LOGIN_ATTEMPTS:
                lockout_remaining = await self._get_lockout_remaining(lockout_key)
                return None, f"Account locked. Try again in {lockout_remaining} minutes."

            # Get user by email
            user = await self.get_user_by_email(email, db)
            if not user:
                await self._increment_failed_attempts(lockout_key)
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

            if not user.is_active:
                await self._increment_failed_attempts(lockout_key)
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

            if not password_handler.verify_password(password, user.password_hash):
                await self._increment_failed_attempts(lockout_key)
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

            # Successful login — clear failed attempts
            await self._clear_failed_attempts(lockout_key)

            # Update last login
            user.last_login = datetime.now(timezone.utc)

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
            logger.error(f"Authentication failed: {str(e)}", exc_info=True)
            return None, "Authentication failed. Please try again."

    async def create_user_session(
        self,
        user: User,
        db: AsyncSession,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        device_fingerprint: Optional[str] = None
    ) -> Tuple[Optional[Dict[str, str]], Optional[str]]:
        """Create a new user session with tokens"""
        try:
            tokens = jwt_handler.create_token_pair(user.id)

            access_token_hash = hashlib.sha256(
                tokens["access_token"].encode()
            ).hexdigest()
            refresh_token_hash = hashlib.sha256(
                tokens["refresh_token"].encode()
            ).hexdigest()

            access_exp = jwt_handler.get_token_expiration(tokens["access_token"])
            refresh_exp = jwt_handler.get_token_expiration(tokens["refresh_token"])

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
            logger.error(f"Session creation failed: {str(e)}", exc_info=True)
            return None, "Session creation failed. Please try again."

    async def refresh_token(
        self,
        refresh_token: str,
        db: AsyncSession,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[Optional[Dict[str, str]], Optional[str]]:
        """
        Refresh tokens with rotation — old refresh token is revoked and a new pair issued.
        Detects replay attacks by checking if the refresh token was already used.
        """
        try:
            # Verify refresh token format and expiration
            payload = jwt_handler.verify_token(refresh_token, "refresh")
            if not payload:
                return None, "Invalid or expired refresh token"

            user_id = UUID(payload["sub"])
            token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()

            # Check if this refresh token was already revoked (replay detection)
            if await self._is_token_revoked(token_hash):
                # Token reuse detected — revoke entire token family for this user
                await self._revoke_token_family(user_id, db)
                logger.logger.warning(
                    "Token reuse detected for user %s, revoked all sessions", user_id
                )
                return None, "Token reuse detected. Please re-authenticate."

            # Find session with this refresh token
            stmt = select(UserSession).where(
                UserSession.refresh_token_hash == token_hash,
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

            # Revoke the old refresh token to prevent replay
            await self._revoke_token(token_hash)

            # Issue a new token pair (rotation)
            new_tokens = jwt_handler.create_token_pair(user.id)

            new_access_hash = hashlib.sha256(
                new_tokens["access_token"].encode()
            ).hexdigest()
            new_refresh_hash = hashlib.sha256(
                new_tokens["refresh_token"].encode()
            ).hexdigest()

            # Update session with new token hashes
            session.token_hash = new_access_hash
            session.refresh_token_hash = new_refresh_hash
            session.expires_at = jwt_handler.get_token_expiration(new_tokens["access_token"])
            session.refresh_expires_at = jwt_handler.get_token_expiration(new_tokens["refresh_token"])
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
                "access_token": new_tokens["access_token"],
                "refresh_token": new_tokens["refresh_token"],
                "token_type": "bearer",
                "expires_in": jwt_handler.access_token_expire_minutes * 60
            }, None

        except Exception as e:
            await db.rollback()
            logger.error(f"Token refresh failed: {str(e)}", exc_info=True)
            return None, "Token refresh failed. Please re-authenticate."

    async def logout_user(
        self,
        access_token: str,
        db: AsyncSession,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """Logout user by revoking session"""
        try:
            user_id_str = jwt_handler.get_subject_from_token(access_token)
            if not user_id_str:
                return False, "Invalid token"

            user_id = UUID(user_id_str)

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
            logger.error(f"Logout failed: {str(e)}", exc_info=True)
            return False, "Logout failed. Please try again."

    # --- Account lockout helpers (Task 2.7) ---

    async def _get_failed_attempts(self, key: str) -> int:
        """Get number of failed login attempts from Redis"""
        try:
            from app.core.cache import cache_manager
            if cache_manager._connected:
                val = await cache_manager.redis_client.get(f"auth:{key}")
                return int(val) if val else 0
        except Exception:
            pass
        return 0

    async def _increment_failed_attempts(self, key: str) -> None:
        """Increment failed login attempts in Redis"""
        try:
            from app.core.cache import cache_manager
            if cache_manager._connected:
                redis_key = f"auth:{key}"
                pipe = cache_manager.redis_client.pipeline()
                pipe.incr(redis_key)
                pipe.expire(redis_key, SecurityConfig.LOCKOUT_DURATION_MINUTES * 60)
                await pipe.execute()
        except Exception as e:
            logger.logger.warning("Failed to increment login attempts: %s", e)

    async def _clear_failed_attempts(self, key: str) -> None:
        """Clear failed login attempts on successful login"""
        try:
            from app.core.cache import cache_manager
            if cache_manager._connected:
                await cache_manager.redis_client.delete(f"auth:{key}")
        except Exception:
            pass

    async def _get_lockout_remaining(self, key: str) -> int:
        """Get remaining lockout time in minutes"""
        try:
            from app.core.cache import cache_manager
            if cache_manager._connected:
                ttl = await cache_manager.redis_client.ttl(f"auth:{key}")
                return max(1, (ttl + 59) // 60) if ttl > 0 else 0
        except Exception:
            pass
        return SecurityConfig.LOCKOUT_DURATION_MINUTES

    # --- Token revocation helpers (Task 2.5) ---

    async def _revoke_token(self, token_hash: str) -> None:
        """Store revoked refresh token in Redis with TTL matching refresh token expiry"""
        try:
            from app.core.cache import cache_manager
            if cache_manager._connected:
                await cache_manager.redis_client.setex(
                    f"revoked_token:{token_hash}",
                    7 * 24 * 3600,  # 7 days (matches refresh token expiry)
                    "1",
                )
        except Exception as e:
            logger.logger.warning("Failed to revoke token in Redis: %s", e)

    async def _is_token_revoked(self, token_hash: str) -> bool:
        """Check if a token has been revoked (replay detection)"""
        try:
            from app.core.cache import cache_manager
            if cache_manager._connected:
                return bool(await cache_manager.redis_client.exists(f"revoked_token:{token_hash}"))
        except Exception:
            pass
        return False

    async def _revoke_token_family(self, user_id: UUID, db: AsyncSession) -> None:
        """Revoke all active sessions for a user (response to token reuse)"""
        try:
            stmt = select(UserSession).where(
                UserSession.user_id == user_id,
                UserSession.is_active == True,
            )
            result = await db.execute(stmt)
            for session in result.scalars().all():
                session.revoke()
            await db.commit()
        except Exception as e:
            logger.logger.error("Failed to revoke token family: %s", e)

    # --- User lookup ---

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
        """Verify session and return user if valid"""
        try:
            payload = jwt_handler.verify_token(access_token, "access")
            if not payload:
                return None

            user_id = UUID(payload["sub"])

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

            session.update_last_used()

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
    return await auth_service.register_user(email, password, first_name, last_name, db, ip_address, user_agent)

async def authenticate_user(email: str, password: str, db, ip_address: Optional[str] = None, user_agent: Optional[str] = None):
    return await auth_service.authenticate_user(email, password, db, ip_address, user_agent)

async def get_user_by_id(user_id, db):
    return await auth_service.get_user_by_id(user_id, db)
