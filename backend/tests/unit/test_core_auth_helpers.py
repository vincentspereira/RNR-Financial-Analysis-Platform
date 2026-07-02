"""
Tests for app.core.auth helper functions.
"""
from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.core.auth import (
    create_access_token,
    get_current_active_user,
    get_current_user,
    get_current_verified_user,
    verify_token,
)


@pytest.mark.unit
@pytest.mark.auth
class TestCreateAccessToken:
    def test_with_user_id(self):
        token = create_access_token({"user_id": str(uuid4())})
        assert isinstance(token, str) and token.count(".") == 2

    def test_with_sub(self):
        token = create_access_token({"sub": str(uuid4())})
        assert isinstance(token, str)

    def test_with_custom_expiry(self):
        token = create_access_token(
            {"user_id": str(uuid4())}, expires_delta=timedelta(hours=2)
        )
        assert isinstance(token, str)


@pytest.mark.unit
@pytest.mark.auth
class TestVerifyToken:
    def test_valid_token(self):
        from app.services.auth.jwt_handler import jwt_handler
        token = jwt_handler.create_access_token(uuid4())
        payload = verify_token(token)
        assert payload is not None

    def test_invalid_token_raises_401(self):
        with pytest.raises(HTTPException) as exc_info:
            verify_token("not-a-jwt")
        assert exc_info.value.status_code == 401


@pytest.mark.unit
@pytest.mark.auth
@pytest.mark.asyncio
class TestGetCurrentUser:
    async def test_invalid_token_raises(self):
        from fastapi.security import HTTPAuthorizationCredentials
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="bad-token")
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=creds, db=MagicMock())
        assert exc_info.value.status_code == 401

    async def test_missing_sub_raises(self):
        from fastapi.security import HTTPAuthorizationCredentials
        # Build a token with no `sub`
        from jose import jwt
        from app.core.config import settings
        from datetime import datetime, timezone, timedelta
        token = jwt.encode(
            {"exp": datetime.now(timezone.utc) + timedelta(minutes=10), "type": "access"},
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=creds, db=MagicMock())
        assert exc_info.value.status_code == 401

    async def test_user_not_found_raises(self):
        from fastapi.security import HTTPAuthorizationCredentials
        from app.services.auth.jwt_handler import jwt_handler
        token = jwt_handler.create_access_token(uuid4())
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        with patch("app.core.auth.auth_service.get_user_by_id", AsyncMock(return_value=None)):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(credentials=creds, db=MagicMock())
        assert exc_info.value.status_code == 401

    async def test_inactive_user_raises(self):
        from fastapi.security import HTTPAuthorizationCredentials
        from app.services.auth.jwt_handler import jwt_handler
        user = MagicMock()
        user.is_active = False
        token = jwt_handler.create_access_token(uuid4())
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        with patch("app.core.auth.auth_service.get_user_by_id", AsyncMock(return_value=user)):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(credentials=creds, db=MagicMock())
        assert exc_info.value.status_code == 401

    async def test_active_user_returned(self):
        from fastapi.security import HTTPAuthorizationCredentials
        from app.services.auth.jwt_handler import jwt_handler
        user = MagicMock()
        user.is_active = True
        token = jwt_handler.create_access_token(uuid4())
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        with patch("app.core.auth.auth_service.get_user_by_id", AsyncMock(return_value=user)):
            result = await get_current_user(credentials=creds, db=MagicMock())
        assert result is user


@pytest.mark.unit
@pytest.mark.auth
@pytest.mark.asyncio
class TestActiveAndVerifiedUser:
    async def test_active_user_passes(self):
        user = MagicMock()
        user.is_active = True
        result = await get_current_active_user(current_user=user)
        assert result is user

    async def test_inactive_user_raises(self):
        user = MagicMock()
        user.is_active = False
        with pytest.raises(HTTPException) as exc_info:
            await get_current_active_user(current_user=user)
        assert exc_info.value.status_code == 400

    async def test_verified_user_passes(self):
        user = MagicMock()
        user.is_verified = True
        result = await get_current_verified_user(current_user=user)
        assert result is user

    async def test_unverified_user_raises(self):
        user = MagicMock()
        user.is_verified = False
        with pytest.raises(HTTPException) as exc_info:
            await get_current_verified_user(current_user=user)
        assert exc_info.value.status_code == 400


@pytest.mark.unit
@pytest.mark.auth
class TestGetOptionalCurrentUser:
    def test_no_authorization_returns_none(self):
        from app.core.auth import get_optional_current_user
        result = get_optional_current_user(authorization=None, db=MagicMock())
        assert result is None

    def test_invalid_format_returns_none(self):
        from app.core.auth import get_optional_current_user
        result = get_optional_current_user(authorization="NotBearer foo", db=MagicMock())
        assert result is None

    def test_invalid_token_returns_none(self):
        from app.core.auth import get_optional_current_user
        result = get_optional_current_user(authorization="Bearer not-a-jwt", db=MagicMock())
        assert result is None
