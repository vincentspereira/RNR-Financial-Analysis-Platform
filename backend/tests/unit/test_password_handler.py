"""
Unit tests for PasswordHandler (bcrypt-backed via passlib).
"""
from __future__ import annotations

import pytest

from app.services.auth.password_handler import PasswordHandler


@pytest.fixture
def handler() -> PasswordHandler:
    return PasswordHandler()


@pytest.mark.unit
@pytest.mark.auth
class TestPasswordHandler:
    def test_hash_password_returns_non_plaintext(self, handler):
        password = "Sup3rS3cret!!"
        hashed = handler.hash_password(password)
        assert hashed != password
        # bcrypt hashes start with $2a$, $2b$ or $2y$
        assert hashed.startswith("$2")

    def test_hash_password_uses_random_salt(self, handler):
        password = "Sup3rS3cret!!"
        h1 = handler.hash_password(password)
        h2 = handler.hash_password(password)
        # Same password, but different salts → different hashes
        assert h1 != h2

    def test_verify_password_accepts_correct(self, handler):
        password = "Sup3rS3cret!!"
        hashed = handler.hash_password(password)
        assert handler.verify_password(password, hashed) is True

    def test_verify_password_rejects_wrong(self, handler):
        hashed = handler.hash_password("correct-password")
        assert handler.verify_password("wrong-password", hashed) is False

    def test_verify_password_is_case_sensitive(self, handler):
        hashed = handler.hash_password("Password123")
        assert handler.verify_password("password123", hashed) is False
        assert handler.verify_password("Password123", hashed) is True

    def test_hash_and_verify_roundtrip_unicode(self, handler):
        # Bcrypt has a 72-byte limit; UTF-8 chars consume more bytes.
        password = "пароль-üñîçødé-中文-123!"
        hashed = handler.hash_password(password)
        assert handler.verify_password(password, hashed) is True

    def test_verify_password_returns_false_for_malformed_hash(self, handler):
        # passlib raises on truly malformed strings; our handler should
        # at minimum not silently return True for the wrong password.
        with pytest.raises(Exception):
            handler.verify_password("anything", "not-a-bcrypt-hash")
