"""
Admin dashboard schemas for request/response models.
"""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class UserSummary(BaseModel):
    """Summary of a user for admin view."""
    id: str
    email: str
    full_name: Optional[str] = None
    role: str
    is_active: bool
    subscription_tier: str
    created_at: str
    last_login: Optional[str] = None
    portfolio_count: int
    total_trades: int


class UserListResponse(BaseModel):
    """Paginated user list response."""
    users: List[UserSummary]
    total: int
    page: int
    page_size: int


class UpdateUserRequest(BaseModel):
    """Request to update user properties."""
    role: Optional[str] = None
    is_active: Optional[bool] = None
    subscription_tier: Optional[str] = None


class SystemMetrics(BaseModel):
    """System-wide metrics."""
    total_users: int
    active_users_24h: int
    active_users_7d: int
    active_users_30d: int
    total_portfolios: int
    total_trades: int
    total_alerts_configured: int
    api_calls_today: int
    api_calls_7d: int
    average_response_time_ms: float
    uptime_percentage: float
    storage_used_gb: float
    error_rate_percentage: float


class RevenueMetrics(BaseModel):
    """Revenue and subscription metrics."""
    mrr: float
    total_revenue: float
    subscribers_by_tier: Dict[str, int]
    revenue_by_tier: Dict[str, float]
    churn_rate: float
    new_subscribers_30d: int
    cancelled_subscribers_30d: int


class ActivityLogEntry(BaseModel):
    """Single activity log entry."""
    timestamp: str
    user_email: str
    action: str
    details: Optional[str] = None
    ip_address: Optional[str] = None


class ActivityLogResponse(BaseModel):
    """Paginated activity log response."""
    entries: List[ActivityLogEntry]
    total: int
    page: int
    page_size: int
