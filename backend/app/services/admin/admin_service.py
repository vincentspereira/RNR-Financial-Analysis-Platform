"""
Admin dashboard service for user management and system analytics.

Provides user CRUD, system metrics, revenue analytics, and activity logging.
"""
import hashlib
import random
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.core.logging import get_logger
from app.schemas.admin import (
    ActivityLogEntry,
    RevenueMetrics,
    SystemMetrics,
    UserSummary,
)

logger = get_logger("app.services.admin")

# Generate mock users
_first_names = ["James", "Emma", "Liam", "Olivia", "Noah", "Ava", "William", "Sophia",
                "Benjamin", "Isabella", "Lucas", "Mia", "Henry", "Charlotte", "Alexander",
                "Amelia", "Daniel", "Harper", "Matthew", "Evelyn"]
_last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
               "Davis", "Rodriguez", "Martinez", "Anderson", "Taylor", "Thomas", "Jackson",
               "White", "Harris", "Martin", "Thompson", "Moore", "Clark"]
_domains = ["gmail.com", "outlook.com", "yahoo.com", "company.com", "proton.me"]
_roles = ["user", "user", "user", "user", "premium", "premium", "admin"]
_tiers = ["free", "free", "free", "pro", "pro", "enterprise"]
_actions = ["login", "view_portfolio", "run_analysis", "place_trade", "export_report",
            "create_alert", "update_settings", "run_screener", "view_dashboard"]

MOCK_USERS: List[Dict] = []
_rng = random.Random(42)

for i in range(50):
    uid = str(uuid4())
    first = _first_names[i % len(_first_names)]
    last = _last_names[i % len(_last_names)]
    role = _roles[i % len(_roles)]
    tier = _tiers[i % len(_tiers)]
    if role == "admin":
        tier = "enterprise"
    elif role == "premium":
        tier = "pro"

    days_ago = _rng.randint(0, 365)
    created = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()

    login_days_ago = _rng.randint(0, min(days_ago, 30)) if _rng.random() > 0.2 else None
    last_login = (datetime.now(timezone.utc) - timedelta(days=login_days_ago)).isoformat() if login_days_ago is not None else None

    MOCK_USERS.append({
        "id": uid,
        "email": f"{first.lower()}.{last.lower()}@{_domains[i % len(_domains)]}",
        "full_name": f"{first} {last}",
        "role": role,
        "is_active": _rng.random() > 0.1,
        "subscription_tier": tier,
        "created_at": created,
        "last_login": last_login,
        "portfolio_count": _rng.randint(0, 8),
        "total_trades": _rng.randint(0, 150),
    })

# Activity log
MOCK_ACTIVITY: List[Dict] = []
for i in range(200):
    hours_ago = _rng.randint(0, 720)
    user = MOCK_USERS[i % len(MOCK_USERS)]
    MOCK_ACTIVITY.append({
        "timestamp": (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat(),
        "user_email": user["email"],
        "action": _actions[i % len(_actions)],
        "details": f"Executed from {('Chrome' if _rng.random() > 0.5 else 'Firefox')} browser",
        "ip_address": f"192.168.{_rng.randint(1,255)}.{_rng.randint(1,255)}",
    })
MOCK_ACTIVITY.sort(key=lambda x: x["timestamp"], reverse=True)


class AdminService:
    """Admin dashboard service."""

    def get_users(
        self, page: int = 1, page_size: int = 20,
        search: Optional[str] = None, role: Optional[str] = None,
        active_only: bool = False
    ) -> Dict:
        """Get paginated user list with filters."""
        filtered = MOCK_USERS[:]

        if search:
            search_lower = search.lower()
            filtered = [
                u for u in filtered
                if search_lower in u["email"].lower()
                or (u["full_name"] and search_lower in u["full_name"].lower())
            ]

        if role:
            filtered = [u for u in filtered if u["role"] == role]

        if active_only:
            filtered = [u for u in filtered if u["is_active"]]

        total = len(filtered)
        start = (page - 1) * page_size
        end = start + page_size
        users = [UserSummary(**u) for u in filtered[start:end]]

        return {
            "users": users,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def get_user(self, user_id: str) -> Optional[UserSummary]:
        """Get a single user by ID."""
        for u in MOCK_USERS:
            if u["id"] == user_id:
                return UserSummary(**u)
        return None

    def update_user(self, user_id: str, updates: Dict) -> Optional[UserSummary]:
        """Update user properties."""
        for u in MOCK_USERS:
            if u["id"] == user_id:
                if "role" in updates and updates["role"] is not None:
                    u["role"] = updates["role"]
                if "is_active" in updates and updates["is_active"] is not None:
                    u["is_active"] = updates["is_active"]
                if "subscription_tier" in updates and updates["subscription_tier"] is not None:
                    u["subscription_tier"] = updates["subscription_tier"]
                return UserSummary(**u)
        return None

    def get_system_metrics(self) -> SystemMetrics:
        """Get system-wide metrics."""
        active_users = len([u for u in MOCK_USERS if u["is_active"]])
        return SystemMetrics(
            total_users=len(MOCK_USERS),
            active_users_24h=max(5, active_users // 3),
            active_users_7d=max(12, active_users * 2 // 3),
            active_users_30d=active_users,
            total_portfolios=sum(u["portfolio_count"] for u in MOCK_USERS),
            total_trades=sum(u["total_trades"] for u in MOCK_USERS),
            total_alerts_configured=_rng.randint(50, 200),
            api_calls_today=_rng.randint(1000, 5000),
            api_calls_7d=_rng.randint(8000, 35000),
            average_response_time_ms=round(_rng.uniform(45, 120), 1),
            uptime_percentage=round(99.9 + _rng.uniform(0, 0.09), 2),
            storage_used_gb=round(_rng.uniform(5, 25), 1),
            error_rate_percentage=round(_rng.uniform(0.1, 2.0), 2),
        )

    def get_revenue_metrics(self) -> RevenueMetrics:
        """Get revenue and subscription metrics."""
        tier_counts = {"free": 0, "pro": 0, "enterprise": 0}
        for u in MOCK_USERS:
            tier = u.get("subscription_tier", "free")
            if tier in tier_counts:
                tier_counts[tier] += 1

        pricing = {"free": 0, "pro": 29, "enterprise": 99}
        revenue_by_tier = {tier: count * pricing[tier] for tier, count in tier_counts.items()}

        total_mrr = sum(revenue_by_tier.values())

        return RevenueMetrics(
            mrr=total_mrr,
            total_revenue=total_mrr * 12 + _rng.randint(0, 5000),
            subscribers_by_tier=tier_counts,
            revenue_by_tier=revenue_by_tier,
            churn_rate=round(_rng.uniform(1.5, 5.0), 1),
            new_subscribers_30d=_rng.randint(5, 25),
            cancelled_subscribers_30d=_rng.randint(1, 8),
        )

    def get_activity_log(
        self, page: int = 1, page_size: int = 20,
        user_id: Optional[str] = None, action: Optional[str] = None
    ) -> Dict:
        """Get paginated activity log."""
        filtered = MOCK_ACTIVITY[:]

        if user_id:
            user_email = next((u["email"] for u in MOCK_USERS if u["id"] == user_id), None)
            filtered = [e for e in filtered if e["user_email"] == user_email]
        if action:
            filtered = [e for e in filtered if e["action"] == action]

        total = len(filtered)
        start = (page - 1) * page_size
        end = start + page_size
        entries = [ActivityLogEntry(**e) for e in filtered[start:end]]

        return {
            "entries": entries,
            "total": total,
            "page": page,
            "page_size": page_size,
        }


admin_service = AdminService()
