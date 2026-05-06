"""
Performance optimization utilities for reaching 50ms API targets.

Provides:
- L1 in-memory cache (fallback when Redis is unavailable)
- Prepared / parameterized query helpers
- Batch query execution
- Connection pool warm-up
"""
import time
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Tuple
from threading import Lock

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_engine, get_async_session
from app.core.logging import get_logger

perf_logger = get_logger("app.core.performance")


class LRUCache:
    """Thread-safe in-memory LRU cache for L1 caching."""

    def __init__(self, max_size: int = 5000, default_ttl: int = 60):
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._cache: OrderedDict[str, Tuple[float, Any]] = OrderedDict()
        self._lock = Lock()
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._cache:
                expires_at, value = self._cache[key]
                if time.time() < expires_at:
                    self._cache.move_to_end(key)
                    self.hits += 1
                    return value
                del self._cache[key]
            self.misses += 1
            return None

    def set(self, key: str, value: Any, ttl: int = None):
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            expires_at = time.time() + (ttl or self._default_ttl)
            self._cache[key] = (expires_at, value)
            if len(self._cache) > self._max_size:
                self._cache.popitem(last=False)

    def invalidate(self, prefix: str = None):
        with self._lock:
            if prefix is None:
                self._cache.clear()
                return
            keys_to_del = [k for k in self._cache if k.startswith(prefix)]
            for k in keys_to_del:
                del self._cache[k]

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0

    @property
    def size(self) -> int:
        return len(self._cache)


# Global L1 cache
l1_cache = LRUCache(max_size=5000, default_ttl=60)


def cached_l1(prefix: str, ttl: int = 60):
    """Decorator for L1 in-memory caching of async functions."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            key = f"{prefix}:{args[1:]}:{sorted(kwargs.items())}"
            cached = l1_cache.get(key)
            if cached is not None:
                return cached
            result = await func(*args, **kwargs)
            if result is not None:
                l1_cache.set(key, result, ttl=ttl)
            return result
        wrapper.__name__ = func.__name__
        return wrapper
    return decorator


# --- Query helpers ---

COMMON_QUERIES = {
    "company_by_symbol": "SELECT * FROM companies WHERE symbol = :symbol LIMIT 1",
    "company_by_id": "SELECT * FROM companies WHERE id = :id LIMIT 1",
    "user_by_email": "SELECT * FROM users WHERE email = :email LIMIT 1",
    "user_by_id": "SELECT * FROM users WHERE id = :id LIMIT 1",
    "portfolio_by_user": "SELECT * FROM portfolios WHERE user_id = :user_id AND is_active = true",
    "market_data_latest": (
        "SELECT md.* FROM market_data md "
        "WHERE md.company_id = :company_id "
        "ORDER BY md.price_date DESC LIMIT :limit"
    ),
    "financial_statements_latest": (
        "SELECT * FROM financial_statements "
        "WHERE company_id = :company_id "
        "ORDER BY period_end_date DESC LIMIT :limit"
    ),
    "audit_logs_by_user": (
        "SELECT * FROM audit_logs WHERE user_id = :user_id "
        "ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
    ),
}


async def execute_prepared(
    session: AsyncSession,
    query_name: str,
    params: Dict[str, Any],
) -> Any:
    """Execute a pre-defined parameterized query."""
    sql = COMMON_QUERIES.get(query_name)
    if not sql:
        raise ValueError(f"Unknown prepared query: {query_name}")
    start = time.perf_counter()
    result = await session.execute(text(sql), params)
    elapsed = (time.perf_counter() - start) * 1000
    if elapsed > 50:
        perf_logger.warning("Slow prepared query %s: %.1fms", query_name, elapsed)
    return result


async def execute_batch(
    session: AsyncSession,
    queries: List[Tuple[str, Dict[str, Any]]],
) -> List[Any]:
    """Execute multiple prepared queries in a single transaction."""
    results = []
    for query_name, params in queries:
        result = await execute_prepared(session, query_name, params)
        results.append(result)
    return results


async def warm_connection_pool():
    """Pre-fill the connection pool at startup."""
    pool = async_engine.pool
    target = async_engine.pool.size()
    perf_logger.info("Warming connection pool to %d connections", target)

    async def _ping(i: int):
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))

    import asyncio
    tasks = [_ping(i) for i in range(min(target, 10))]
    await asyncio.gather(*tasks, return_exceptions=True)
    perf_logger.info("Connection pool warmed: %d/%d", pool.checkedin(), pool.size())


async def get_performance_stats() -> Dict[str, Any]:
    """Return current performance statistics."""
    pool = async_engine.pool
    return {
        "l1_cache": {
            "size": l1_cache.size,
            "hits": l1_cache.hits,
            "misses": l1_cache.misses,
            "hit_rate": f"{l1_cache.hit_rate:.1f}%",
        },
        "connection_pool": {
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
        },
    }
