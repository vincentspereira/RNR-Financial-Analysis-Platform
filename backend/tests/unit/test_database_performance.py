"""
Tests for app.core.database_performance.
DB connections themselves are mocked — we only test the pure logic.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.database_performance import (
    DatabaseHealthChecker,
    DatabasePerformanceMonitor,
)


@pytest.fixture
def monitor() -> DatabasePerformanceMonitor:
    return DatabasePerformanceMonitor()


@pytest.fixture
def checker() -> DatabaseHealthChecker:
    return DatabaseHealthChecker()


# ---------------------------------------------------------------------------
# DatabasePerformanceMonitor
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestQueryTypeDetection:
    @pytest.mark.parametrize(
        "stmt,expected",
        [
            ("SELECT * FROM users", "SELECT"),
            ("  select id from t", "SELECT"),
            ("INSERT INTO users (name) VALUES ('x')", "INSERT"),
            ("UPDATE users SET name='x'", "UPDATE"),
            ("DELETE FROM users", "DELETE"),
            ("VACUUM ANALYZE", "OTHER"),
            ("CREATE TABLE x()", "OTHER"),
        ],
    )
    def test_query_type(self, monitor, stmt, expected):
        assert monitor._get_query_type(stmt) == expected


@pytest.mark.unit
@pytest.mark.asyncio
class TestQueryStatistics:
    async def test_empty_statistics(self, monitor):
        stats = await monitor.get_query_statistics()
        assert stats["total_queries"] == 0
        assert stats["slow_queries"] == 0
        assert stats["top_slow_queries"] == []

    async def test_with_query_stats(self, monitor):
        monitor.query_stats[1] = {
            "statement": "SELECT * FROM users",
            "count": 5,
            "total_time": 10.0,
            "avg_time": 2.0,
            "max_time": 3.0,
            "min_time": 1.0,
        }
        monitor.query_stats[2] = {
            "statement": "INSERT INTO logs",
            "count": 2,
            "total_time": 0.1,
            "avg_time": 0.05,
            "max_time": 0.06,
            "min_time": 0.04,
        }
        stats = await monitor.get_query_statistics()
        assert stats["total_queries"] == 2
        assert stats["slow_queries"] == 1  # SELECT @ 2.0s exceeds 1.0s threshold

    async def test_query_type_distribution(self, monitor):
        monitor.query_stats[1] = {
            "statement": "SELECT 1", "count": 3, "total_time": 0, "avg_time": 0,
            "max_time": 0, "min_time": 0,
        }
        monitor.query_stats[2] = {
            "statement": "INSERT INTO t", "count": 2, "total_time": 0, "avg_time": 0,
            "max_time": 0, "min_time": 0,
        }
        dist = monitor._get_query_type_distribution()
        assert dist["SELECT"] == 3
        assert dist["INSERT"] == 2


@pytest.mark.unit
@pytest.mark.asyncio
class TestConnectionPoolStats:
    async def test_pool_stats_structure(self, monitor):
        with patch("app.core.database_performance.async_engine") as mock_engine:
            mock_pool = MagicMock()
            mock_pool.size.return_value = 20
            mock_pool.checkedin.return_value = 15
            mock_pool.checkedout.return_value = 5
            mock_pool.overflow.return_value = 0
            mock_pool.invalid.return_value = 0
            mock_engine.pool = mock_pool
            stats = await monitor.get_connection_pool_stats()
            assert stats["pool_size"] == 20
            assert stats["checked_in_connections"] == 15
            assert stats["checked_out_connections"] == 5


# ---------------------------------------------------------------------------
# DatabaseHealthChecker
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestDatabaseHealthChecker:
    async def test_connection_failure_marks_unhealthy(self, checker):
        with patch("app.core.database_performance.async_engine") as mock_engine:
            # async_engine.begin() raises
            mock_engine.begin.side_effect = RuntimeError("conn refused")
            result = await checker.check_database_health()
        assert result["status"] in ("unhealthy", "degraded")
        # Either way, checks dict is populated
        assert "checks" in result

    async def test_basic_health_call_returns_dict(self, checker):
        # Even when everything fails, returns a dict with checks
        result = await checker.check_database_health()
        assert isinstance(result, dict)
        assert "status" in result
        assert "checks" in result
