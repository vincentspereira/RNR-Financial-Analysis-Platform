"""
Pydantic v2 schemas for billing and subscription endpoints.
"""
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class PlanFeature(BaseModel):
    """A feature included in a plan."""
    name: str
    description: Optional[str] = None


class PlanLimits(BaseModel):
    """Usage limits for a plan."""
    api_calls_per_day: int = 100
    portfolios: int = 1
    holdings_per_portfolio: int = 5
    watchlists: int = 1
    symbols_per_watchlist: int = 10
    backtests_per_month: int = 5
    exports_per_month: int = 3
    sentiment_requests_per_day: int = 10


class PlanResponse(BaseModel):
    """Subscription plan details."""
    id: str
    name: str
    description: Optional[str] = None
    price_monthly: Decimal
    price_annually: Optional[Decimal] = None
    features: List[str]
    limits: Dict[str, int]
    is_active: bool = True


class PlansListResponse(BaseModel):
    """List of available plans."""
    plans: List[PlanResponse]
    total: int


class SubscriptionResponse(BaseModel):
    """User's current subscription."""
    id: str
    plan_name: str
    status: str
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool = False
    features: List[str] = []
    limits: Dict[str, int] = {}


class SubscriptionStatusResponse(BaseModel):
    """Subscription status check."""
    has_subscription: bool
    plan_name: Optional[str] = None
    status: Optional[str] = None
    stripe_configured: bool


class CreateSubscriptionRequest(BaseModel):
    """Request to create a new subscription."""
    plan_name: str = Field(..., description="Name of the plan to subscribe to")
    payment_method_id: Optional[str] = Field(None, description="Stripe payment method ID")


class UpdateSubscriptionRequest(BaseModel):
    """Request to update subscription plan."""
    new_plan_name: str = Field(..., description="Name of the new plan")


class CancelSubscriptionRequest(BaseModel):
    """Request to cancel subscription."""
    reason: Optional[str] = Field(None, description="Cancellation reason")


class UsageResponse(BaseModel):
    """Usage statistics for a single type."""
    current: int
    limit: int
    remaining: int
    unlimited: bool


class UsageSummaryResponse(BaseModel):
    """Usage summary across all types."""
    user_id: str
    period: str
    usage: Dict[str, UsageResponse]


class PortalUrlResponse(BaseModel):
    """Stripe customer portal URL."""
    url: Optional[str] = None
    configured: bool = False


class InvoiceResponse(BaseModel):
    """Invoice details."""
    id: str
    amount_paid: float
    currency: str
    status: str
    created: Optional[datetime] = None
    pdf_url: Optional[str] = None


class WebhookResponse(BaseModel):
    """Webhook processing result."""
    received: bool
    event_type: Optional[str] = None
    processed: bool = False
