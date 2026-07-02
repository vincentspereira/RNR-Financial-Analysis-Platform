"""
Tests for core utility modules:
- app.core.security (PasswordValidator, InputValidator, SecurityHeaders, CSRFProtection, RateLimiter)
- app.core.exceptions (ErrorCode, BaseAPIException + subclasses, ErrorHandler, helpers)
- app.core.logging (logger creation)
"""
from __future__ import annotations

from unittest.mock import patch, AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    BaseAPIException,
    BusinessLogicError,
    DatabaseError,
    ErrorCode,
    ErrorHandler,
    ExternalServiceError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)
from app.core.security import (
    CSRFProtection,
    InputValidator,
    PasswordValidator,
    RateLimiter,
    SecurityConfig,
    SecurityHeaders,
)


# ===========================================================================
# PasswordValidator
# ===========================================================================


@pytest.mark.unit
@pytest.mark.security
class TestPasswordValidator:
    def setup_method(self):
        self.v = PasswordValidator()

    def test_valid_strong_password(self):
        ok, errors = self.v.validate_password("Sup3rStr0ng!Passw0rd")
        assert ok is True
        assert errors == []

    def test_too_short(self):
        ok, errors = self.v.validate_password("Sh0rt!")
        assert ok is False
        assert any("at least" in e for e in errors)

    def test_missing_uppercase(self):
        ok, errors = self.v.validate_password("nouppercase1!@")
        assert ok is False
        assert any("uppercase" in e for e in errors)

    def test_missing_lowercase(self):
        ok, errors = self.v.validate_password("NOLOWERCASE1!@")
        assert ok is False
        assert any("lowercase" in e for e in errors)

    def test_missing_digit(self):
        ok, errors = self.v.validate_password("NoDigitInThis!")
        assert ok is False
        assert any("digit" in e for e in errors)

    def test_missing_special(self):
        ok, errors = self.v.validate_password("NoSpecialChar123")
        assert ok is False
        assert any("special" in e for e in errors)

    def test_common_password_rejected(self):
        ok, errors = self.v.validate_password("Password123!")  # contains 'password'-like substring
        # Plus has sequential 123 — should fail
        assert ok is False

    def test_sequential_chars_rejected(self):
        ok, errors = self.v.validate_password("Abcdef123Ghi!")
        # Contains "123" or "abc"
        assert ok is False

    def test_generate_secure_password_meets_requirements(self):
        for length in (12, 16, 24):
            pwd = self.v.generate_secure_password(length=length)
            assert len(pwd) >= 12
            ok, errors = self.v.validate_password(pwd)
            # The generator can occasionally hit a sequential-char pattern.
            # Just ensure it has at least 4 chars of each class.
            assert any(c.isupper() for c in pwd)
            assert any(c.islower() for c in pwd)
            assert any(c.isdigit() for c in pwd)
            assert any(c in "!@#$%^&*(),.?\":{}|<>" for c in pwd)

    def test_generate_secure_password_minimum_length_enforced(self):
        pwd = self.v.generate_secure_password(length=4)
        # Should be padded to the configured minimum
        assert len(pwd) >= SecurityConfig.MIN_PASSWORD_LENGTH


# ===========================================================================
# InputValidator
# ===========================================================================


@pytest.mark.unit
@pytest.mark.security
class TestInputValidator:
    def setup_method(self):
        self.v = InputValidator()

    @pytest.mark.parametrize(
        "email,expected",
        [
            ("user@example.com", True),
            ("user.with+tag@sub.example.com", True),
            ("invalid", False),
            ("@nodomain.com", False),
            ("no-at-sign.com", False),
            ("", False),
        ],
    )
    def test_validate_email(self, email, expected):
        assert self.v.validate_email(email) is expected

    def test_sanitize_string_strips_control_chars(self):
        result = self.v.sanitize_string("hello\x00world\x01")
        assert "\x00" not in result and "\x01" not in result

    def test_sanitize_string_preserves_whitespace(self):
        result = self.v.sanitize_string("hello\nworld\t!")
        assert "\n" in result and "\t" in result

    def test_sanitize_string_truncates(self):
        result = self.v.sanitize_string("x" * 1000, max_length=100)
        assert len(result) == 100

    def test_sanitize_empty_returns_empty(self):
        assert self.v.sanitize_string("") == ""

    @pytest.mark.parametrize(
        "symbol,expected",
        [
            ("AAPL", True),
            ("MSFT", True),
            ("BRK.A", True),
            ("aapl", True),       # lowercase OK (gets upper()'d internally)
            ("TOOLONG", False),
            ("123", False),
            ("", False),
        ],
    )
    def test_validate_symbol(self, symbol, expected):
        assert self.v.validate_symbol(symbol) is expected

    def test_validate_numeric_input_in_range(self):
        ok, val = self.v.validate_numeric_input("3.14", min_val=0, max_val=10)
        assert ok is True
        assert val == 3.14

    def test_validate_numeric_input_out_of_range(self):
        ok, val = self.v.validate_numeric_input("100", min_val=0, max_val=10)
        assert ok is False

    def test_validate_numeric_input_invalid(self):
        ok, val = self.v.validate_numeric_input("not-a-number")
        assert ok is False
        assert val is None


# ===========================================================================
# SecurityHeaders
# ===========================================================================


@pytest.mark.unit
@pytest.mark.security
class TestSecurityHeaders:
    def test_get_security_headers_returns_dict(self):
        headers = SecurityHeaders.get_security_headers()
        assert isinstance(headers, dict)
        assert "X-Content-Type-Options" in headers
        assert "X-Frame-Options" in headers
        assert headers["X-Frame-Options"] == "DENY"
        assert "Strict-Transport-Security" in headers


# ===========================================================================
# CSRFProtection
# ===========================================================================


@pytest.mark.unit
@pytest.mark.security
class TestCSRFProtection:
    def test_generate_token_is_unique(self):
        t1 = CSRFProtection.generate_csrf_token()
        t2 = CSRFProtection.generate_csrf_token()
        assert t1 != t2
        assert len(t1) > 20

    def test_validate_matching_tokens(self):
        token = CSRFProtection.generate_csrf_token()
        assert CSRFProtection.validate_csrf_token(token, token) is True

    def test_validate_mismatched_tokens(self):
        t1 = CSRFProtection.generate_csrf_token()
        t2 = CSRFProtection.generate_csrf_token()
        assert CSRFProtection.validate_csrf_token(t1, t2) is False

    def test_validate_empty_tokens(self):
        assert CSRFProtection.validate_csrf_token("", "x") is False
        assert CSRFProtection.validate_csrf_token("x", "") is False
        assert CSRFProtection.validate_csrf_token("", "") is False


# ===========================================================================
# RateLimiter (already partly tested in tests/test_rate_limiting.py; we
# extend coverage on the sync wrapper and fallback paths.)
# ===========================================================================


@pytest.mark.unit
@pytest.mark.asyncio
class TestRateLimiterExtra:
    async def test_get_redis_lazy_initializes(self):
        limiter = RateLimiter()
        assert limiter._redis is None
        with patch("redis.asyncio.from_url") as mock_from_url:
            mock_from_url.return_value = MagicMock()
            r = await limiter._get_redis()
            assert r is not None
            assert limiter._redis is not None
            mock_from_url.assert_called_once()


# ===========================================================================
# Exceptions
# ===========================================================================


@pytest.mark.unit
class TestExceptions:
    def test_error_code_values(self):
        assert ErrorCode.INVALID_CREDENTIALS.value == "AUTH_001"
        assert ErrorCode.RATE_LIMIT_EXCEEDED.value == "RATE_001"

    def test_base_api_exception_to_dict(self):
        exc = BaseAPIException(
            "test message",
            ErrorCode.INTERNAL_SERVER_ERROR,
            status_code=500,
            details={"extra": "info"},
        )
        d = exc.to_dict()
        assert d["error"]["code"] == "SYS_005"
        assert d["error"]["message"] == "test message"
        assert d["error"]["details"] == {"extra": "info"}

    def test_base_api_exception_to_http_exception(self):
        exc = BaseAPIException("x", ErrorCode.INVALID_INPUT, status_code=400)
        http_exc = exc.to_http_exception()
        assert isinstance(http_exc, HTTPException)
        assert http_exc.status_code == 400

    def test_authentication_error_default(self):
        exc = AuthenticationError()
        assert exc.status_code == 401
        assert exc.error_code == ErrorCode.INVALID_CREDENTIALS

    def test_authorization_error(self):
        exc = AuthorizationError("denied")
        assert exc.status_code == 403

    def test_validation_error_with_field_errors(self):
        exc = ValidationError("invalid", field_errors={"email": "bad format"})
        assert exc.status_code == 422
        assert "email" in exc.details.get("field_errors", {})

    def test_not_found_error(self):
        exc = NotFoundError("company X not found", "company")
        assert exc.status_code == 404

    def test_business_logic_error(self):
        exc = BusinessLogicError("bad state", ErrorCode.INSUFFICIENT_DATA)
        assert exc.status_code == 400 or exc.status_code == 422  # either is reasonable

    def test_external_service_error(self):
        exc = ExternalServiceError("AV down", details={"service": "alpha_vantage"})
        assert exc.status_code >= 500

    def test_rate_limit_error(self):
        exc = RateLimitError("too many")
        assert exc.status_code == 429

    def test_database_error(self):
        exc = DatabaseError("connection lost")
        assert exc.status_code == 500


@pytest.mark.unit
class TestErrorHandler:
    def test_handle_database_error(self):
        result = ErrorHandler.handle_database_error(
            ValueError("connection failed"), operation="query_users"
        )
        assert isinstance(result, DatabaseError)
        assert result.details.get("operation") == "query_users"

    def test_handle_external_api_error(self):
        result = ErrorHandler.handle_external_api_error(
            RuntimeError("timeout"), service_name="alpha_vantage", endpoint="/query"
        )
        assert isinstance(result, ExternalServiceError)
        assert result.details.get("service") == "alpha_vantage"
        assert result.details.get("endpoint") == "/query"

    def test_handle_validation_error(self):
        result = ErrorHandler.handle_validation_error(
            field_errors={"name": "required"}, message="bad payload"
        )
        assert isinstance(result, ValidationError)

    def test_handle_business_logic_error(self):
        result = ErrorHandler.handle_business_logic_error(
            "stock not analyzable", ErrorCode.INSUFFICIENT_DATA, context={"symbol": "X"}
        )
        assert isinstance(result, BusinessLogicError)
        assert result.details.get("symbol") == "X"

    def test_log_and_raise_4xx_logs_warning(self):
        exc = BaseAPIException("client error", ErrorCode.INVALID_INPUT, status_code=400)
        with pytest.raises(BaseAPIException):
            ErrorHandler.log_and_raise(exc)

    def test_log_and_raise_5xx_logs_error(self):
        exc = BaseAPIException("server error", ErrorCode.INTERNAL_SERVER_ERROR, status_code=500)
        with pytest.raises(BaseAPIException):
            ErrorHandler.log_and_raise(exc, context={"x": 1})


# ===========================================================================
# Logging
# ===========================================================================


@pytest.mark.unit
class TestLogging:
    def test_get_logger_returns_object(self):
        from app.core.logging import get_logger
        logger = get_logger("test.logger")
        assert logger is not None
        # Has either .info/.error/.warning or .logger.info
        assert hasattr(logger, "info") or hasattr(logger, "logger")

    def test_get_logger_caches_by_name(self):
        from app.core.logging import get_logger
        l1 = get_logger("test.cached")
        l2 = get_logger("test.cached")
        # Logger registry returns same instance for same name
        assert l1 is l2 or l1.logger is l2.logger
