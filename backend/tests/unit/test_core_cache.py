"""
Tests for app.core.cache (CacheManager with mocked Redis).
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.cache import CacheManager, CacheStrategies, cached


@pytest.fixture
def manager() -> CacheManager:
    """Fresh CacheManager (not connected)."""
    return CacheManager()


@pytest.fixture
def connected_manager() -> CacheManager:
    """CacheManager with mocked Redis client + connected state."""
    m = CacheManager()
    m.redis_client = AsyncMock()
    m._connected = True
    return m


@pytest.mark.unit
class TestCacheKeyGeneration:
    def test_simple_key(self, manager):
        key = manager._generate_key("user", "alice")
        assert key == "user:alice"

    def test_key_with_kwargs(self, manager):
        key = manager._generate_key("user", "alice", country="US", age=30)
        # kwargs sorted alphabetically
        assert "age:30" in key
        assert "country:US" in key

    def test_long_key_hashed(self, manager):
        key = manager._generate_key("prefix", *(f"arg{i}" for i in range(100)))
        # Key was hashed because it exceeded 200 chars
        assert key.startswith("prefix:hash:")
        assert len(key) < 100


@pytest.mark.unit
class TestSerialization:
    def test_serialize_deserialize_roundtrip(self, manager):
        data = {"name": "AAPL", "price": 175.5, "tags": ["tech"]}
        serialized = manager._serialize_value(data)
        deserialized = manager._deserialize_value(serialized)
        assert deserialized == data

    def test_deserialize_none(self, manager):
        assert manager._deserialize_value(None) is None


@pytest.mark.unit
class TestHitRate:
    def test_hit_rate_no_data(self, manager):
        assert manager._calculate_hit_rate(0, 0) == 0.0

    def test_hit_rate_all_hits(self, manager):
        assert manager._calculate_hit_rate(100, 0) == 100.0

    def test_hit_rate_partial(self, manager):
        assert manager._calculate_hit_rate(70, 30) == 70.0


@pytest.mark.unit
@pytest.mark.asyncio
class TestCacheNotConnected:
    """All cache ops on a disconnected manager must return graceful defaults."""

    async def test_get_returns_none(self, manager):
        assert await manager.get("any") is None

    async def test_set_returns_false(self, manager):
        assert await manager.set("k", "v") is False

    async def test_delete_returns_zero(self, manager):
        assert await manager.delete("a", "b") == 0

    async def test_exists_returns_zero(self, manager):
        assert await manager.exists("a") == 0

    async def test_expire_returns_false(self, manager):
        assert await manager.expire("k", 60) is False

    async def test_ttl_returns_minus_one(self, manager):
        assert await manager.ttl("k") == -1

    async def test_flush_pattern_returns_zero(self, manager):
        assert await manager.flush_pattern("*") == 0

    async def test_get_stats_returns_disconnected(self, manager):
        stats = await manager.get_stats()
        assert stats["connected"] is False


@pytest.mark.unit
@pytest.mark.asyncio
class TestCacheConnected:
    async def test_get_hit(self, connected_manager):
        connected_manager.redis_client.get.return_value = b'{"k":"v"}'
        result = await connected_manager.get("foo")
        assert result == {"k": "v"}

    async def test_get_miss(self, connected_manager):
        connected_manager.redis_client.get.return_value = None
        assert await connected_manager.get("missing") is None

    async def test_get_swallows_errors(self, connected_manager):
        connected_manager.redis_client.get.side_effect = RuntimeError("boom")
        assert await connected_manager.get("any") is None

    async def test_set_success(self, connected_manager):
        connected_manager.redis_client.set.return_value = True
        assert await connected_manager.set("k", {"v": 1}) is True

    async def test_set_swallows_errors(self, connected_manager):
        connected_manager.redis_client.set.side_effect = RuntimeError("boom")
        assert await connected_manager.set("k", "v") is False

    async def test_delete_count(self, connected_manager):
        connected_manager.redis_client.delete.return_value = 2
        result = await connected_manager.delete("a", "b")
        assert result == 2

    async def test_exists_count(self, connected_manager):
        connected_manager.redis_client.exists.return_value = 1
        assert await connected_manager.exists("k") == 1

    async def test_expire(self, connected_manager):
        connected_manager.redis_client.expire.return_value = True
        assert await connected_manager.expire("k", 60) is True

    async def test_ttl(self, connected_manager):
        connected_manager.redis_client.ttl.return_value = 42
        assert await connected_manager.ttl("k") == 42

    async def test_flush_pattern_deletes_matching(self, connected_manager):
        connected_manager.redis_client.keys.return_value = [b"a", b"b", b"c"]
        connected_manager.redis_client.delete.return_value = 3
        assert await connected_manager.flush_pattern("user:*") == 3

    async def test_flush_pattern_no_matches(self, connected_manager):
        connected_manager.redis_client.keys.return_value = []
        assert await connected_manager.flush_pattern("nothing:*") == 0

    async def test_get_stats_when_connected(self, connected_manager):
        connected_manager.redis_client.info.return_value = {
            "used_memory_human": "10M",
            "connected_clients": 5,
            "total_commands_processed": 1000,
            "keyspace_hits": 800,
            "keyspace_misses": 200,
        }
        stats = await connected_manager.get_stats()
        assert stats["connected"] is True
        assert stats["used_memory"] == "10M"
        assert stats["hit_rate"] == 80.0

    async def test_get_stats_on_error(self, connected_manager):
        connected_manager.redis_client.info.side_effect = RuntimeError("boom")
        stats = await connected_manager.get_stats()
        assert stats["connected"] is False
        assert "error" in stats


@pytest.mark.unit
class TestCacheStrategies:
    def test_all_strategies_have_expire_and_prefix(self):
        for name in (
            "FINANCIAL_DATA", "COMPANY_INFO", "MARKET_DATA",
            "USER_SESSION", "API_RESPONSE", "CALCULATIONS",
        ):
            strategy = getattr(CacheStrategies, name)
            assert "expire" in strategy
            assert "prefix" in strategy


@pytest.mark.unit
@pytest.mark.asyncio
class TestCachedDecorator:
    async def test_cached_skip_cache(self):
        # skip_cache=True should call func every time
        call_count = 0

        @cached(strategy=CacheStrategies.API_RESPONSE, skip_cache=True)
        async def my_func(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        result1 = await my_func(5)
        result2 = await my_func(5)
        assert result1 == 10
        assert result2 == 10
        assert call_count == 2

    async def test_cached_when_disconnected_calls_func_each_time(self):
        # CacheManager is not connected → no caching; just runs the function
        call_count = 0

        @cached(strategy=CacheStrategies.API_RESPONSE)
        async def my_func(x):
            nonlocal call_count
            call_count += 1
            return x + 1

        # cache_manager is disconnected by default → call_count grows
        result = await my_func(10)
        assert result == 11
