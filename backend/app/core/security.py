"""
Security configuration and utilities for the Financial Analysis Platform
"""
import secrets
import string
import time
from typing import Optional

from fastapi import HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
import redis.asyncio as redis
import re

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("app.security")


class SecurityConfig:
    """Security configuration and utilities"""

    # Password requirements
    MIN_PASSWORD_LENGTH = 12
    MAX_PASSWORD_LENGTH = 128
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_DIGITS = True
    REQUIRE_SPECIAL_CHARS = True

    # Account lockout settings
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 30

    # Session settings
    SESSION_TIMEOUT_MINUTES = 30
    MAX_CONCURRENT_SESSIONS = 3

    # Rate limiting
    RATE_LIMIT_REQUESTS_PER_MINUTE = 60
    RATE_LIMIT_BURST = 10

    # Security headers
    SECURITY_HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
    }


class PasswordValidator:
    """Password validation utilities"""

    @staticmethod
    def validate_password(password: str) -> tuple[bool, list[str]]:
        """
        Validate password against security requirements

        Args:
            password: Password to validate

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Length check
        if len(password) < SecurityConfig.MIN_PASSWORD_LENGTH:
            errors.append(f"Password must be at least {SecurityConfig.MIN_PASSWORD_LENGTH} characters long")

        if len(password) > SecurityConfig.MAX_PASSWORD_LENGTH:
            errors.append(f"Password must be no more than {SecurityConfig.MAX_PASSWORD_LENGTH} characters long")

        # Character requirements
        if SecurityConfig.REQUIRE_UPPERCASE and not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")

        if SecurityConfig.REQUIRE_LOWERCASE and not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")

        if SecurityConfig.REQUIRE_DIGITS and not re.search(r'\d', password):
            errors.append("Password must contain at least one digit")

        if SecurityConfig.REQUIRE_SPECIAL_CHARS and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Password must contain at least one special character")

        # Common password patterns
        if password.lower() in ['password', '123456', 'qwerty', 'admin', 'letmein']:
            errors.append("Password is too common and easily guessable")

        # Sequential characters
        if re.search(r'(012|123|234|345|456|567|678|789|890|abc|bcd|cde|def)', password.lower()):
            errors.append("Password should not contain sequential characters")

        return len(errors) == 0, errors

    @staticmethod
    def generate_secure_password(length: int = 16) -> str:
        """
        Generate a cryptographically secure password

        Args:
            length: Password length (minimum 12)

        Returns:
            Secure password string
        """
        if length < SecurityConfig.MIN_PASSWORD_LENGTH:
            length = SecurityConfig.MIN_PASSWORD_LENGTH

        # Character sets
        lowercase = string.ascii_lowercase
        uppercase = string.ascii_uppercase
        digits = string.digits
        special = "!@#$%^&*(),.?\":{}|<>"

        # Ensure at least one character from each required set
        password = [
            secrets.choice(uppercase),
            secrets.choice(lowercase),
            secrets.choice(digits),
            secrets.choice(special)
        ]

        # Fill remaining length with random characters
        all_chars = lowercase + uppercase + digits + special
        for _ in range(length - 4):
            password.append(secrets.choice(all_chars))

        # Shuffle the password
        secrets.SystemRandom().shuffle(password)

        return ''.join(password)


class InputValidator:
    """Input validation utilities"""

    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    @staticmethod
    def sanitize_string(input_str: str, max_length: int = 255) -> str:
        """Sanitize string input"""
        if not input_str:
            return ""

        # Remove null bytes and control characters
        sanitized = ''.join(char for char in input_str if ord(char) >= 32 or char in '\t\n\r')

        # Trim to max length
        return sanitized[:max_length].strip()

    @staticmethod
    def validate_symbol(symbol: str) -> bool:
        """Validate stock symbol format"""
        if not symbol:
            return False

        # Stock symbols: 1-5 uppercase letters, optionally followed by a dot and more letters
        pattern = r'^[A-Z]{1,5}(\.[A-Z]{1,2})?$'
        return bool(re.match(pattern, symbol.upper()))

    @staticmethod
    def validate_numeric_input(value: str, min_val: float = None, max_val: float = None) -> tuple[bool, Optional[float]]:
        """Validate numeric input"""
        try:
            num_value = float(value)

            if min_val is not None and num_value < min_val:
                return False, None

            if max_val is not None and num_value > max_val:
                return False, None

            return True, num_value
        except (ValueError, TypeError):
            return False, None


class SecurityHeaders:
    """Security headers middleware"""

    @staticmethod
    def get_security_headers() -> dict:
        """Get security headers for responses"""
        return SecurityConfig.SECURITY_HEADERS.copy()


class RateLimiter:
    """Redis-backed distributed rate limiter using sliding window"""

    def __init__(self):
        self._redis: Optional[redis.Redis] = None

    async def _get_redis(self) -> redis.Redis:
        """Get or create Redis connection"""
        if not self._redis:
            redis_url = getattr(settings, "REDIS_URL", "redis://localhost:6379/0")
            self._redis = redis.from_url(redis_url)
        return self._redis

    async def check_rate_limit(self, key: str, limit: int = None, window: int = 60) -> bool:
        """
        Sliding window rate limit check using Redis sorted sets.

        Args:
            key: Unique identifier (IP, user ID, etc.)
            limit: Maximum requests allowed in the window
            window: Time window in seconds

        Returns:
            True if request is allowed, False if rate limited
        """
        if limit is None:
            limit = SecurityConfig.RATE_LIMIT_REQUESTS_PER_MINUTE

        try:
            r = await self._get_redis()
            now = time.time()
            window_key = f"rate_limit:{key}"

            pipe = r.pipeline()
            pipe.zremrangebyscore(window_key, 0, now - window)
            pipe.zadd(window_key, {str(now): now})
            pipe.zcard(window_key)
            pipe.expire(window_key, window)

            results = await pipe.execute()
            count = results[2]

            return count <= limit
        except Exception as e:
            # Fall back to allowing the request if Redis is unavailable
            logger.logger.warning("Rate limit check failed, allowing request: %s", e)
            return True

    def is_rate_limited(self, identifier: str, max_requests: int = None, window_minutes: int = 1) -> bool:
        """
        Synchronous wrapper — returns True if rate limited.

        Note: For async contexts, prefer check_rate_limit() directly.
        This method returns the inverse of the check (True = limited).
        """
        import asyncio
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # We're inside an async context but called synchronously — log warning
            logger.logger.warning("is_rate_limited() called from async context; use check_rate_limit() instead")
            return False

        result = asyncio.run(
            self.check_rate_limit(identifier, max_requests, window_minutes * 60)
        )
        return not result

    async def close(self):
        """Close Redis connection"""
        if self._redis:
            await self._redis.close()
            self._redis = None


class CSRFProtection:
    """CSRF protection utilities"""

    @staticmethod
    def generate_csrf_token() -> str:
        """Generate CSRF token"""
        return secrets.token_urlsafe(32)

    @staticmethod
    def validate_csrf_token(token: str, expected_token: str) -> bool:
        """Validate CSRF token"""
        if not token or not expected_token:
            return False

        return secrets.compare_digest(token, expected_token)


# Global instances
password_validator = PasswordValidator()
input_validator = InputValidator()
rate_limiter = RateLimiter()
csrf_protection = CSRFProtection()
