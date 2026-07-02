"""
Unit tests for the IBKR safety gate.

The gate enforces per-user, per-UTC-day order count and notional caps.
Tests cover allow/deny paths, day rollover, and concurrent access safety.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from app.services.ibkr.safety import SafetyGate


@pytest.fixture
def gate() -> SafetyGate:
    # Fresh gate per test — module-level singleton must not leak state between tests.
    return SafetyGate()


@pytest.mark.unit
@pytest.mark.asyncio
class TestSafetyGateAllow:
    async def test_fresh_user_is_allowed(self, gate):
        decision = await gate.check("user-1", notional_usd=1000.0)
        assert decision.allowed is True
        assert decision.order_count_today == 0
        assert decision.notional_today_usd == 0.0
        assert decision.reason == "OK"

    async def test_record_increments_counters(self, gate):
        await gate.record("user-1", 1234.50)
        decision = await gate.check("user-1", notional_usd=0.0)
        assert decision.allowed is True
        assert decision.order_count_today == 1
        assert decision.notional_today_usd == pytest.approx(1234.50)

    async def test_record_multiple_users_isolated(self, gate):
        await gate.record("alice", 500.0)
        await gate.record("bob", 200.0)
        a = await gate.check("alice", 0.0)
        b = await gate.check("bob", 0.0)
        assert a.notional_today_usd == pytest.approx(500.0)
        assert b.notional_today_usd == pytest.approx(200.0)
        assert a.order_count_today == 1
        assert b.order_count_today == 1


@pytest.mark.unit
@pytest.mark.asyncio
class TestSafetyGateDeny:
    async def test_denied_when_order_count_exceeds_limit(self, gate):
        with patch("app.services.ibkr.safety.settings") as mock_settings:
            mock_settings.IBKR_ORDER_DAILY_LIMIT = 3
            mock_settings.IBKR_ORDER_NOTIONAL_LIMIT_USD = 1_000_000.0
            # Place 3 orders → at limit
            for _ in range(3):
                d = await gate.check("user", 100.0)
                assert d.allowed is True
                await gate.record("user", 100.0)
            # 4th order denied
            d = await gate.check("user", 100.0)
            assert d.allowed is False
            assert "Daily order limit" in d.reason
            assert d.order_count_today == 3

    async def test_denied_when_notional_would_exceed_limit(self, gate):
        with patch("app.services.ibkr.safety.settings") as mock_settings:
            mock_settings.IBKR_ORDER_DAILY_LIMIT = 100
            mock_settings.IBKR_ORDER_NOTIONAL_LIMIT_USD = 10_000.0
            await gate.record("user", 7_000.0)
            d = await gate.check("user", notional_usd=4_000.0)  # would total 11k
            assert d.allowed is False
            assert "notional limit" in d.reason

    async def test_at_exactly_notional_limit_is_allowed(self, gate):
        with patch("app.services.ibkr.safety.settings") as mock_settings:
            mock_settings.IBKR_ORDER_DAILY_LIMIT = 100
            mock_settings.IBKR_ORDER_NOTIONAL_LIMIT_USD = 10_000.0
            await gate.record("user", 5_000.0)
            d = await gate.check("user", 5_000.0)  # exactly 10k total
            assert d.allowed is True


@pytest.mark.unit
@pytest.mark.asyncio
class TestSafetyGateDayRollover:
    async def test_counters_reset_at_new_utc_day(self, gate):
        await gate.record("user", 5000.0)
        before = await gate.check("user", 0.0)
        assert before.order_count_today == 1

        # Simulate next day by mutating internal state
        gate._state["user"].day_utc = "1970-01-01"

        after = await gate.check("user", 0.0)
        assert after.order_count_today == 0
        assert after.notional_today_usd == 0.0


@pytest.mark.unit
@pytest.mark.asyncio
class TestSafetyGateConcurrency:
    async def test_concurrent_records_do_not_lose_updates(self, gate):
        # Fire 20 concurrent record() calls. Lock should serialise them so
        # final count is exactly 20.
        await asyncio.gather(*(gate.record("user", 1.0) for _ in range(20)))
        d = await gate.check("user", 0.0)
        assert d.order_count_today == 20
        assert d.notional_today_usd == pytest.approx(20.0)
