"""
Usage tracking and metering for subscription plans.

Records usage events and checks plan limits for metered features.
"""
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.subscription import UsageRecord

logger = get_logger("app.services.billing.usage_tracker")

# Default limits when no plan is found
DEFAULT_LIMITS = {
    "api_calls_per_day": 100,
    "portfolios": 1,
    "holdings_per_portfolio": 5,
    "watchlists": 1,
    "symbols_per_watchlist": 10,
    "backtests_per_month": 5,
    "exports_per_month": 3,
    "sentiment_requests_per_day": 50,
}


class UsageTracker:
    """Track and meter API usage per user."""

    async def record_usage(
        self,
        db: AsyncSession,
        user_id: str,
        subscription_id: Optional[str],
        usage_type: str,
        quantity: int = 1,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> UsageRecord:
        """Record a usage event."""
        record = UsageRecord(
            user_id=UUID(user_id) if isinstance(user_id, str) else user_id,
            subscription_id=UUID(subscription_id) if subscription_id and isinstance(subscription_id, str) else subscription_id,
            usage_type=usage_type,
            quantity=quantity,
            metadata_=metadata,
            recorded_at=datetime.now(timezone.utc),
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return record

    async def get_usage(
        self,
        db: AsyncSession,
        user_id: str,
        usage_type: Optional[str] = None,
        period: str = "current_month",
    ) -> Dict[str, Any]:
        """Get usage stats for a user."""
        uid = UUID(user_id) if isinstance(user_id, str) else user_id

        now = datetime.now(timezone.utc)
        if period == "current_month":
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif period == "current_day":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "current_week":
            start = now - timedelta(days=now.weekday())
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        conditions = [UsageRecord.user_id == uid, UsageRecord.recorded_at >= start]
        if usage_type:
            conditions.append(UsageRecord.usage_type == usage_type)

        stmt = select(
            UsageRecord.usage_type,
            func.sum(UsageRecord.quantity).label("total"),
        ).where(and_(*conditions)).group_by(UsageRecord.usage_type)

        result = await db.execute(stmt)
        rows = result.all()

        usage_by_type = {row.usage_type: int(row.total) for row in rows}
        total = sum(usage_by_type.values())

        return {
            "user_id": str(uid),
            "period": period,
            "start_date": start.isoformat(),
            "end_date": now.isoformat(),
            "total_events": total,
            "by_type": usage_by_type,
        }

    async def check_limit(
        self,
        db: AsyncSession,
        user_id: str,
        usage_type: str,
        plan_limits: Optional[Dict[str, int]] = None,
    ) -> bool:
        """Check if user has exceeded their plan limit. Returns True if within limit."""
        limits = plan_limits or DEFAULT_LIMITS
        limit = limits.get(usage_type, -1)

        if limit == -1:
            return True  # Unlimited

        uid = UUID(user_id) if isinstance(user_id, str) else user_id
        now = datetime.now(timezone.utc)

        # Determine period based on usage type
        if "_per_day" in usage_type:
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif "_per_month" in usage_type:
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        stmt = select(func.sum(UsageRecord.quantity)).where(
            and_(
                UsageRecord.user_id == uid,
                UsageRecord.usage_type == usage_type,
                UsageRecord.recorded_at >= start,
            )
        )
        result = await db.execute(stmt)
        current = result.scalar() or 0

        return int(current) < limit

    async def get_usage_summary(
        self,
        db: AsyncSession,
        user_id: str,
        plan_limits: Optional[Dict[str, int]] = None,
    ) -> Dict[str, Any]:
        """Get usage summary across all types for a user."""
        limits = plan_limits or DEFAULT_LIMITS

        usage = await self.get_usage(db, user_id)
        by_type = usage.get("by_type", {})

        summary = {}
        for limit_key, limit_value in limits.items():
            current = by_type.get(limit_key, 0)
            summary[limit_key] = {
                "current": current,
                "limit": limit_value,
                "remaining": limit_value - current if limit_value >= 0 else -1,
                "unlimited": limit_value == -1,
            }

        return {
            "user_id": user_id,
            "period": usage["period"],
            "usage": summary,
        }
