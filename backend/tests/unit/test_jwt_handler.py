"""
Unit tests for JWTHandler.

Covers token issuance, verification, expiry, tampering, and the
access+refresh pair helper. No external dependencies — uses the real
`python-jose` library and the platform's configured SECRET_KEY.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from jose import jwt

from app.core.config import settings
from app.services.auth.jwt_handler import JWTHandler


@pytest.fixture
def handler() -> JWTHandler:
    return JWTHandler()


@pytest.mark.unit
@pytest.mark.auth
class TestJWTHandlerCreate:
    def test_create_access_token_returns_decodable_jwt(self, handler):
        user_id = uuid4()
        token = handler.create_access_token(user_id)
        decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert decoded["sub"] == str(user_id)
        assert decoded["type"] == "access"
        assert "iat" in decoded and "exp" in decoded

    def test_create_access_token_converts_uuid_to_string_subject(self, handler):
        user_id = uuid4()
        token = handler.create_access_token(user_id)
        assert handler.get_subject_from_token(token) == str(user_id)

    def test_create_access_token_default_expiry_matches_config(self, handler):
        token = handler.create_access_token(uuid4())
        exp = handler.get_token_expiration(token)
        assert exp is not None
        delta = exp - datetime.now(timezone.utc)
        # Should be within a few seconds of configured minutes
        assert (settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60) - 5 < delta.total_seconds() <= (
            settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )

    def test_create_access_token_honors_custom_expires_delta(self, handler):
        token = handler.create_access_token(uuid4(), expires_delta=timedelta(hours=2))
        exp = handler.get_token_expiration(token)
        assert exp is not None
        delta = exp - datetime.now(timezone.utc)
        # 2h minus a small margin
        assert 7000 < delta.total_seconds() <= 7200

    def test_create_access_token_includes_additional_claims(self, handler):
        token = handler.create_access_token(
            uuid4(), additional_claims={"role": "admin", "tenant": "t1"}
        )
        decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert decoded["role"] == "admin"
        assert decoded["tenant"] == "t1"

    def test_create_refresh_token_has_type_refresh(self, handler):
        token = handler.create_refresh_token(uuid4())
        decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert decoded["type"] == "refresh"

    def test_create_token_pair_returns_both_with_bearer(self, handler):
        pair = handler.create_token_pair(uuid4())
        assert set(pair.keys()) >= {"access_token", "refresh_token", "token_type"}
        assert pair["token_type"] == "bearer"
        # Validate types match
        access_payload = handler.verify_token(pair["access_token"], "access")
        refresh_payload = handler.verify_token(pair["refresh_token"], "refresh")
        assert access_payload is not None
        assert refresh_payload is not None


@pytest.mark.unit
@pytest.mark.auth
class TestJWTHandlerVerify:
    def test_verify_valid_access_token_returns_payload(self, handler):
        user_id = uuid4()
        token = handler.create_access_token(user_id)
        payload = handler.verify_token(token, "access")
        assert payload is not None
        assert payload["sub"] == str(user_id)

    def test_verify_rejects_wrong_token_type(self, handler):
        access = handler.create_access_token(uuid4())
        # Treat access token as refresh: should return None
        assert handler.verify_token(access, "refresh") is None

    def test_verify_rejects_expired_token(self, handler):
        token = handler.create_access_token(
            uuid4(), expires_delta=timedelta(seconds=-1)
        )
        assert handler.verify_token(token, "access") is None

    def test_verify_rejects_token_signed_with_wrong_key(self, handler):
        # Forge a token with a different key, then try to verify with our handler
        payload = {
            "sub": str(uuid4()),
            "type": "access",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
            "iat": datetime.now(timezone.utc),
        }
        forged = jwt.encode(payload, "totally-different-key", algorithm=settings.ALGORITHM)
        assert handler.verify_token(forged, "access") is None

    def test_verify_rejects_malformed_token(self, handler):
        assert handler.verify_token("not.a.jwt", "access") is None
        assert handler.verify_token("", "access") is None


@pytest.mark.unit
@pytest.mark.auth
class TestJWTHandlerHelpers:
    def test_get_subject_returns_sub_for_valid_token(self, handler):
        user_id = uuid4()
        token = handler.create_access_token(user_id)
        assert handler.get_subject_from_token(token) == str(user_id)

    def test_get_subject_returns_sub_even_when_expired(self, handler):
        # is_token_expired=True path: get_subject still works (no exp verify)
        user_id = uuid4()
        token = handler.create_access_token(user_id, expires_delta=timedelta(seconds=-1))
        assert handler.get_subject_from_token(token) == str(user_id)

    def test_get_subject_returns_none_for_invalid_token(self, handler):
        assert handler.get_subject_from_token("invalid") is None

    def test_is_token_expired_false_for_fresh(self, handler):
        token = handler.create_access_token(uuid4())
        assert handler.is_token_expired(token) is False

    def test_is_token_expired_true_for_past_exp(self, handler):
        token = handler.create_access_token(uuid4(), expires_delta=timedelta(seconds=-1))
        assert handler.is_token_expired(token) is True

    def test_is_token_expired_true_for_malformed(self, handler):
        assert handler.is_token_expired("not-a-jwt") is True

    def test_get_token_expiration_returns_none_for_invalid(self, handler):
        assert handler.get_token_expiration("not-a-jwt") is None
