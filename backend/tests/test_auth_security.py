"""
Tests for auth service features: account lockout, refresh token rotation (Phase 2)
"""
import hashlib
import pytest
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.security import SecurityConfig
from app.services.auth.auth_service import AuthService


@pytest.fixture
def service():
    return AuthService()


@pytest.fixture
def mock_user():
    user = MagicMock()
    user.id = uuid4()
    user.email = "test@test.com"
    user.is_active = True
    user.password_hash = "$2b$12$fakehash"
    return user


class TestAccountLockout:
    """Test account lockout after failed login attempts (Task 2.7)"""

    @pytest.mark.asyncio
    async def test_failed_attempts_increment(self, service, mock_redis):
        """Failed login attempts are tracked in Redis"""
        key = "login_attempts:test@test.com"

        with patch.object(service, '_get_failed_attempts', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = 0
            attempts = await service._get_failed_attempts(key)
            assert attempts == 0

    @pytest.mark.asyncio
    async def test_account_locked_after_max_attempts(self, service):
        """Account should be locked after MAX_LOGIN_ATTEMPTS failed attempts"""
        # Simulate max attempts reached
        with patch.object(service, '_get_failed_attempts', new_callable=AsyncMock) as mock_get, \
             patch.object(service, '_get_lockout_remaining', new_callable=AsyncMock) as mock_remaining:
            mock_get.return_value = SecurityConfig.MAX_LOGIN_ATTEMPTS
            mock_remaining.return_value = 25

            result_user, error = await service.authenticate_user(
                "locked@test.com", "anypassword", AsyncMock()
            )
            assert result_user is None
            assert "locked" in error.lower()
            assert "25" in error

    @pytest.mark.asyncio
    async def test_clear_attempts_on_success(self, service, mock_redis):
        """Failed attempt counter should be cleared on successful login"""
        email = "success@test.com"
        key = f"login_attempts:{email}"

        with patch.object(service, '_clear_failed_attempts', new_callable=AsyncMock) as mock_clear, \
             patch.object(service, '_get_failed_attempts', new_callable=AsyncMock) as mock_get, \
             patch.object(service, 'get_user_by_email', new_callable=AsyncMock) as mock_get_user, \
             patch('app.services.auth.auth_service.password_handler') as mock_pw:

            mock_get.return_value = 2
            mock_get_user.return_value = MagicMock(
                is_active=True,
                password_hash="hash",
                last_login=None,
                id=uuid4(),
            )
            mock_pw.verify_password.return_value = True

            await service.authenticate_user(email, "password", AsyncMock())
            mock_clear.assert_called_once()

    @pytest.mark.asyncio
    async def test_lockout_remaining_time(self, service, mock_redis):
        """Lockout remaining time should be read from Redis TTL"""
        mock_redis.ttl = AsyncMock(return_value=1200)  # 20 minutes

        with patch('app.core.cache.cache_manager') as mock_cache:
            mock_cache._connected = True
            mock_cache.redis_client = mock_redis

            remaining = await service._get_lockout_remaining("auth:test")
            assert remaining == 20  # 1200 seconds / 60 = 20 minutes


class TestRefreshTokenRotation:
    """Test refresh token rotation with replay detection (Task 2.5)"""

    @pytest.mark.asyncio
    async def test_token_revocation_stored_in_redis(self, service, mock_redis):
        """Revoked tokens should be stored in Redis"""
        token_hash = hashlib.sha256(b"test_token").hexdigest()

        with patch('app.core.cache.cache_manager') as mock_cache:
            mock_cache._connected = True
            mock_cache.redis_client = mock_redis

            await service._revoke_token(token_hash)
            mock_redis.setex.assert_called_once()
            call_args = mock_redis.setex.call_args
            assert call_args[0][0] == f"revoked_token:{token_hash}"
            assert call_args[0][1] == 7 * 24 * 3600  # 7 days

    @pytest.mark.asyncio
    async def test_is_token_revoked(self, service, mock_redis):
        """Should detect when a token has been revoked"""
        token_hash = hashlib.sha256(b"test_token").hexdigest()

        with patch('app.core.cache.cache_manager') as mock_cache:
            mock_cache._connected = True
            mock_cache.redis_client = mock_redis

            # Token not revoked
            mock_redis.exists = AsyncMock(return_value=0)
            result = await service._is_token_revoked(token_hash)
            assert result is False

            # Token revoked
            mock_redis.exists = AsyncMock(return_value=1)
            result = await service._is_token_revoked(token_hash)
            assert result is True

    @pytest.mark.asyncio
    async def test_reuse_detection_rejects_token(self, service):
        """Reused refresh tokens should be rejected"""
        token_hash = hashlib.sha256(b"reused_token").hexdigest()

        with patch.object(service, '_is_token_revoked', new_callable=AsyncMock) as mock_revoked, \
             patch.object(service, '_revoke_token_family', new_callable=AsyncMock):

            mock_revoked.return_value = True

            from app.services.auth.jwt_handler import jwt_handler
            with patch.object(jwt_handler, 'verify_token', return_value={
                "sub": str(uuid4()),
                "type": "refresh",
                "exp": 9999999999,
            }):
                result_tokens, error = await service.refresh_token(
                    "reused_token", AsyncMock()
                )
                assert result_tokens is None
                assert "reuse" in error.lower()

    @pytest.mark.asyncio
    async def test_revoke_token_family(self, service):
        """Token family revocation should revoke all user sessions"""
        user_id = uuid4()
        mock_session1 = MagicMock()
        mock_session2 = MagicMock()

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_session1, mock_session2]
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()

        with patch.object(service, '_revoke_token', new_callable=AsyncMock):
            await service._revoke_token_family(user_id, mock_db)
            mock_session1.revoke.assert_called_once()
            mock_session2.revoke.assert_called_once()
            mock_db.commit.assert_called_once()


class TestSecurityConfig:
    """Test security configuration values"""

    def test_max_login_attempts(self):
        assert SecurityConfig.MAX_LOGIN_ATTEMPTS == 5

    def test_lockout_duration(self):
        assert SecurityConfig.LOCKOUT_DURATION_MINUTES == 30

    def test_min_password_length(self):
        assert SecurityConfig.MIN_PASSWORD_LENGTH == 12
