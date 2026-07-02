"""
Deep tests for AuthService (registration, authentication, sessions, refresh,
logout) with all DB / Redis interactions mocked.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.auth.auth_service import AuthService


@pytest.fixture
def svc() -> AuthService:
    return AuthService()


@pytest.fixture
def fake_db():
    db = MagicMock()
    db.added = []

    def _add(obj):
        db.added.append(obj)

    db.add = _add
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.flush = AsyncMock()
    db.execute = AsyncMock()
    return db


def _scalar_result(value):
    """Helper: make a Mock result whose scalar_one_or_none returns `value`."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


# ---------------------------------------------------------------------------
# register_user
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.auth
@pytest.mark.asyncio
class TestRegisterUser:
    async def test_register_user_success(self, svc, fake_db):
        # No existing user
        fake_db.execute.return_value = _scalar_result(None)
        user, error = await svc.register_user(
            email="new@example.com", password="Strong!Pass123",
            first_name="Alice", last_name="Smith", db=fake_db,
        )
        assert error is None
        assert user is not None
        assert user.email == "new@example.com"
        assert len(fake_db.added) == 2  # user + audit log

    async def test_register_user_duplicate_email(self, svc, fake_db):
        existing = MagicMock()
        fake_db.execute.return_value = _scalar_result(existing)
        user, error = await svc.register_user(
            email="exists@example.com", password="x",
            first_name="x", last_name="y", db=fake_db,
        )
        assert user is None
        assert "already exists" in error

    async def test_register_user_exception_rollback(self, svc, fake_db):
        fake_db.execute.side_effect = RuntimeError("db down")
        user, error = await svc.register_user(
            email="err@example.com", password="x",
            first_name="x", last_name="y", db=fake_db,
        )
        assert user is None
        assert "failed" in error.lower()
        fake_db.rollback.assert_awaited_once()


# ---------------------------------------------------------------------------
# authenticate_user
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.auth
@pytest.mark.asyncio
class TestAuthenticateUser:
    async def test_authenticate_account_locked(self, svc, fake_db):
        with patch.object(svc, "_get_failed_attempts", AsyncMock(return_value=5)), \
             patch.object(svc, "_get_lockout_remaining", AsyncMock(return_value=15)):
            user, error = await svc.authenticate_user(
                email="locked@example.com", password="x", db=fake_db,
            )
        assert user is None
        assert "locked" in error.lower()

    async def test_authenticate_user_not_found(self, svc, fake_db):
        with patch.object(svc, "_get_failed_attempts", AsyncMock(return_value=0)), \
             patch.object(svc, "_increment_failed_attempts", AsyncMock()):
            fake_db.execute.return_value = _scalar_result(None)
            user, error = await svc.authenticate_user(
                email="nobody@example.com", password="x", db=fake_db,
            )
        assert user is None
        assert "Invalid" in error

    async def test_authenticate_inactive_account(self, svc, fake_db):
        existing = MagicMock()
        existing.id = uuid4()
        existing.is_active = False
        existing.password_hash = "$2b$12$fake"
        with patch.object(svc, "_get_failed_attempts", AsyncMock(return_value=0)), \
             patch.object(svc, "_increment_failed_attempts", AsyncMock()):
            fake_db.execute.return_value = _scalar_result(existing)
            user, error = await svc.authenticate_user(
                email="inactive@example.com", password="x", db=fake_db,
            )
        assert user is None
        assert "inactive" in error.lower()

    async def test_authenticate_wrong_password(self, svc, fake_db):
        existing = MagicMock()
        existing.id = uuid4()
        existing.is_active = True
        existing.password_hash = "fake-hash"
        with patch.object(svc, "_get_failed_attempts", AsyncMock(return_value=0)), \
             patch.object(svc, "_increment_failed_attempts", AsyncMock()), \
             patch("app.services.auth.auth_service.password_handler.verify_password", return_value=False):
            fake_db.execute.return_value = _scalar_result(existing)
            user, error = await svc.authenticate_user(
                email="ok@example.com", password="wrong", db=fake_db,
            )
        assert user is None
        assert "Invalid" in error

    async def test_authenticate_success(self, svc, fake_db):
        existing = MagicMock()
        existing.id = uuid4()
        existing.is_active = True
        existing.password_hash = "fake-hash"
        with patch.object(svc, "_get_failed_attempts", AsyncMock(return_value=0)), \
             patch.object(svc, "_clear_failed_attempts", AsyncMock()), \
             patch("app.services.auth.auth_service.password_handler.verify_password", return_value=True):
            fake_db.execute.return_value = _scalar_result(existing)
            user, error = await svc.authenticate_user(
                email="ok@example.com", password="correct", db=fake_db,
            )
        assert error is None
        assert user is existing


# ---------------------------------------------------------------------------
# create_user_session
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.auth
@pytest.mark.asyncio
class TestCreateUserSession:
    async def test_create_user_session_returns_tokens(self, svc, fake_db):
        user = MagicMock()
        user.id = uuid4()
        user.email = "u@example.com"
        user.first_name = "U"
        user.last_name = "S"
        user.is_active = True
        user.is_verified = True
        user.subscription_tier = "basic"
        user.created_at = datetime.now(timezone.utc)
        user.last_login = None
        result, error = await svc.create_user_session(user, fake_db, ip_address="1.2.3.4")
        assert error is None
        assert "access_token" in result
        assert "refresh_token" in result
        assert "user" in result


# ---------------------------------------------------------------------------
# logout_user
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.auth
@pytest.mark.asyncio
class TestLogoutUser:
    async def test_logout_invalid_token(self, svc, fake_db):
        success, error = await svc.logout_user("not-a-jwt", fake_db)
        assert success is False
        assert error == "Invalid token"

    async def test_logout_with_valid_session(self, svc, fake_db):
        from app.services.auth.jwt_handler import jwt_handler
        user_id = uuid4()
        token = jwt_handler.create_access_token(user_id)
        # Mock a session that matches
        session = MagicMock()
        session.id = uuid4()
        session.revoke = MagicMock()
        fake_db.execute.return_value = _scalar_result(session)
        success, error = await svc.logout_user(token, fake_db)
        assert success is True

    async def test_logout_no_active_session(self, svc, fake_db):
        from app.services.auth.jwt_handler import jwt_handler
        user_id = uuid4()
        token = jwt_handler.create_access_token(user_id)
        fake_db.execute.return_value = _scalar_result(None)
        # Even with no session, logout returns True (idempotent)
        success, error = await svc.logout_user(token, fake_db)
        assert success is True


# ---------------------------------------------------------------------------
# refresh_token
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.auth
@pytest.mark.asyncio
class TestRefreshToken:
    async def test_refresh_invalid_token(self, svc, fake_db):
        result, error = await svc.refresh_token("not-a-jwt", fake_db)
        assert result is None
        assert "Invalid" in error or "expired" in error.lower()

    async def test_refresh_token_reuse_detected(self, svc, fake_db):
        from app.services.auth.jwt_handler import jwt_handler
        user_id = uuid4()
        token = jwt_handler.create_refresh_token(user_id)
        with patch.object(svc, "_is_token_revoked", AsyncMock(return_value=True)), \
             patch.object(svc, "_revoke_token_family", AsyncMock()):
            result, error = await svc.refresh_token(token, fake_db)
        assert result is None
        assert "reuse" in error.lower() or "re-authenticate" in error.lower()


# ---------------------------------------------------------------------------
# verify_session
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.auth
@pytest.mark.asyncio
class TestVerifySession:
    async def test_verify_invalid_token(self, svc, fake_db):
        assert await svc.verify_session("not-a-jwt", fake_db) is None

    async def test_verify_no_session(self, svc, fake_db):
        from app.services.auth.jwt_handler import jwt_handler
        user_id = uuid4()
        token = jwt_handler.create_access_token(user_id)
        fake_db.execute.return_value = _scalar_result(None)
        assert await svc.verify_session(token, fake_db) is None


# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.auth
@pytest.mark.asyncio
class TestUserLookup:
    async def test_get_user_by_email_returns_user(self, svc, fake_db):
        user = MagicMock()
        fake_db.execute.return_value = _scalar_result(user)
        result = await svc.get_user_by_email("u@e.com", fake_db)
        assert result is user

    async def test_get_user_by_email_normalises_lowercase(self, svc, fake_db):
        fake_db.execute.return_value = _scalar_result(None)
        await svc.get_user_by_email("  U@E.COM  ", fake_db)
        # Verify it executed (we don't assert the SQL, just that the call ran)
        fake_db.execute.assert_awaited_once()

    async def test_get_user_by_id_returns_user(self, svc, fake_db):
        user = MagicMock()
        fake_db.execute.return_value = _scalar_result(user)
        result = await svc.get_user_by_id(uuid4(), fake_db)
        assert result is user


# ---------------------------------------------------------------------------
# Module-level backward-compat shims
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.auth
@pytest.mark.asyncio
class TestModuleLevelShims:
    async def test_register_user_shim(self, fake_db):
        from app.services.auth import auth_service as mod
        fake_db.execute.return_value = _scalar_result(None)
        user, error = await mod.register_user(
            "shim@example.com", "Strong!Pass123", "First", "Last", fake_db
        )
        assert error is None
        assert user is not None

    async def test_get_user_by_id_shim(self, fake_db):
        from app.services.auth import auth_service as mod
        user = MagicMock()
        fake_db.execute.return_value = _scalar_result(user)
        result = await mod.get_user_by_id(uuid4(), fake_db)
        assert result is user
