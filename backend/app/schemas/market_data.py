"""
Pydantic v2 schemas for real-time market data endpoints.
"""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class MarketDataSubscription(BaseModel):
    """Request to subscribe to real-time market data symbols."""
    symbols: List[str] = Field(..., min_length=1, max_length=50, description="Symbols to subscribe to")
    data_types: List[str] = Field(
        default=["trade", "quote"],
        max_length=3,
        description="Data types: trade, quote, aggregate",
    )


class MarketDataUnsubscription(BaseModel):
    """Request to unsubscribe from market data symbols."""
    symbols: List[str] = Field(..., min_length=1, max_length=50, description="Symbols to unsubscribe from")


class MarketDataResponse(BaseModel):
    """Normalized market data point."""
    symbol: str
    price: Optional[Decimal] = None
    volume: int = 0
    timestamp: datetime
    bid: Optional[Decimal] = None
    ask: Optional[Decimal] = None
    high: Optional[Decimal] = None
    low: Optional[Decimal] = None
    open: Optional[Decimal] = None
    change: Optional[Decimal] = None
    change_percent: Optional[Decimal] = None
    source: Optional[str] = None


class StreamerStatusResponse(BaseModel):
    """Status of the market data streamer."""
    connected: bool
    running: bool
    reconnect_attempts: int
    subscribed_symbols: int
    symbols: List[str]


class SubscriptionResponse(BaseModel):
    """Response after subscribing or unsubscribing."""
    success: bool
    symbols: List[str]
    message: str


class UserSubscriptionsResponse(BaseModel):
    """List of user's current subscriptions."""
    user_id: str
    symbols: List[str]
    total: int


class SubscriptionStatsResponse(BaseModel):
    """Global subscription statistics."""
    total_subscribed_symbols: int
    total_subscribed_users: int
    total_active_connections: int
    top_symbols: List[dict]
