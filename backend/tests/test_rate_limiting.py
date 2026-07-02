"""
Tests for Redis-backed rate limiting (Phase 2, Task 2.6)
"""
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.security import RateLimiter, SecurityConfig


class TestRateLimiter:
    """Test Redis-backed sliding window rate limiter"""

    def test_rate_limiter_init(self):
        limiter = RateLimiter()
        assert limiter._redis is None

    @pytest.mark.asyncio
    async def test_check_rate_limit_allows_under_limit(self):
        """Requests under the limit should be allowed"""
        limiter = RateLimiter()

        mock_redis = MagicMock()
        pipe = MagicMock()
        pipe.zremrangebyscore.return_value = pipe
        pipe.zadd.return_value = pipe
        pipe.zcard.return_value = pipe
        pipe.expire.return_value = pipe
        pipe.execute = AsyncMock(return_value=[0, 1, 1, True])
        mock_redis.pipeline.return_value = pipe

        with patch.object(limiter, '_get_redis', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_redis
            result = await limiter.check_rate_limit("test_ip", limit=10, window=60)
            assert result is True

    @pytest.mark.asyncio
    async def test_check_rate_limit_blocks_over_limit(self):
        """Requests over the limit should be blocked"""
        limiter = RateLimiter()

        mock_redis = MagicMock()
        pipe = MagicMock()
        pipe.zremrangebyscore.return_value = pipe
        pipe.zadd.return_value = pipe
        pipe.zcard.return_value = pipe
        pipe.expire.return_value = pipe
        pipe.execute = AsyncMock(return_value=[0, 1, 11, True])  # count=11
        mock_redis.pipeline.return_value = pipe

        with patch.object(limiter, '_get_redis', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_redis
            result = await limiter.check_rate_limit("test_ip", limit=10, window=60)
            assert result is False

    @pytest.mark.asyncio
    async def test_check_rate_limit_defaults(self):
        """Default limit should come from SecurityConfig"""
        limiter = RateLimiter()
        mock_redis = MagicMock()
        pipe = MagicMock()
        pipe.zremrangebyscore.return_value = pipe
        pipe.zadd.return_value = pipe
        pipe.zcard.return_value = pipe
        pipe.expire.return_value = pipe
        pipe.execute = AsyncMock(return_value=[0, 1, 1, True])
        mock_redis.pipeline.return_value = pipe

        with patch.object(limiter, '_get_redis', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_redis
            # Call without explicit limit
            result = await limiter.check_rate_limit("test_ip", window=60)
            assert result is True

    @pytest.mark.asyncio
    async def test_fallback_on_redis_failure(self):
        """Should allow requests if Redis is unavailable"""
        limiter = RateLimiter()

        with patch.object(limiter, '_get_redis', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("Redis connection failed")
            result = await limiter.check_rate_limit("test_ip", limit=10, window=60)
            assert result is True  # Fallback to allowing

    @pytest.mark.asyncio
    async def test_close_redis(self):
        """Should close Redis connection cleanly"""
        limiter = RateLimiter()
        mock_redis = MagicMock()
        mock_redis.close = AsyncMock()
        limiter._redis = mock_redis

        await limiter.close()

        # close() sets self._redis = None, so capture the mock first.
        mock_redis.close.assert_called_once()
        assert limiter._redis is None
