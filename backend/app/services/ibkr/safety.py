"""
Safety gate: per-user daily order count and notional caps.

Hard fail-stop in front of every order placement, so a bug or runaway loop
cannot blow through the account. Counters live in-process and reset at UTC
midnight. For multi-instance deployments, move counters to Redis.
"""
from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Tuple

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("app.services.ibkr.safety")


@dataclass
class _UserDayState:
    day_utc: str
    order_count: int = 0
    notional_usd: float = 0.0


@dataclass
class SafetyDecision:
    allowed: bool
    reason: str
    order_count_today: int
    notional_today_usd: float
    order_limit: int
    notional_limit_usd: float


class SafetyLimitExceeded(Exception):
    def __init__(self, decision: SafetyDecision) -> None:
        super().__init__(decision.reason)
        self.decision = decision


class SafetyGate:
    def __init__(self) -> None:
        self._state: Dict[str, _UserDayState] = defaultdict(
            lambda: _UserDayState(day_utc=self._today())
        )
        self._lock = asyncio.Lock()

    @staticmethod
    def _today() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _get(self, user_id: str) -> _UserDayState:
        s = self._state[user_id]
        today = self._today()
        if s.day_utc != today:
            s.day_utc = today
            s.order_count = 0
            s.notional_usd = 0.0
        return s

    async def check(self, user_id: str, notional_usd: float) -> SafetyDecision:
        """
        Pre-flight check before placing an order. Does NOT increment counters.
        Call `record()` after a successful placement.
        """
        async with self._lock:
            s = self._get(user_id)
            order_limit = settings.IBKR_ORDER_DAILY_LIMIT
            notional_limit = settings.IBKR_ORDER_NOTIONAL_LIMIT_USD

            if s.order_count >= order_limit:
                d = SafetyDecision(
                    allowed=False,
                    reason=(
                        f"Daily order limit reached "
                        f"({s.order_count}/{order_limit}). "
                        f"Limit resets at 00:00 UTC."
                    ),
                    order_count_today=s.order_count,
                    notional_today_usd=s.notional_usd,
                    order_limit=order_limit,
                    notional_limit_usd=notional_limit,
                )
                logger.warning("Safety gate denied: %s (user=%s)", d.reason, user_id)
                return d

            if s.notional_usd + notional_usd > notional_limit:
                d = SafetyDecision(
                    allowed=False,
                    reason=(
                        f"Daily notional limit would be exceeded "
                        f"(${s.notional_usd:,.2f} + ${notional_usd:,.2f} "
                        f"> ${notional_limit:,.2f}). "
                        f"Limit resets at 00:00 UTC."
                    ),
                    order_count_today=s.order_count,
                    notional_today_usd=s.notional_usd,
                    order_limit=order_limit,
                    notional_limit_usd=notional_limit,
                )
                logger.warning("Safety gate denied: %s (user=%s)", d.reason, user_id)
                return d

            return SafetyDecision(
                allowed=True,
                reason="OK",
                order_count_today=s.order_count,
                notional_today_usd=s.notional_usd,
                order_limit=order_limit,
                notional_limit_usd=notional_limit,
            )

    async def record(self, user_id: str, notional_usd: float) -> None:
        async with self._lock:
            s = self._get(user_id)
            s.order_count += 1
            s.notional_usd += notional_usd


safety_gate = SafetyGate()
