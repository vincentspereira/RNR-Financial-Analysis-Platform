"""
Notification and alert schemas for request/response models.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AlertCondition(BaseModel):
    """Condition that triggers an alert."""
    type: str = Field(description="Alert type: price_above, price_below, price_crosses, volume_above, change_percent, drawdown_percent, profit_target")
    symbol: Optional[str] = None
    portfolio_id: Optional[str] = None
    threshold: float
    direction: Optional[str] = None


class CreateAlertRequest(BaseModel):
    """Request to create a new alert."""
    name: str
    condition: AlertCondition
    notification_methods: List[str] = Field(default=["in_app"])


class UpdateAlertRequest(BaseModel):
    """Request to update an existing alert."""
    is_active: Optional[bool] = None
    name: Optional[str] = None


class AlertResponse(BaseModel):
    """Alert response model."""
    id: str
    user_id: str
    name: str
    condition: AlertCondition
    notification_methods: List[str]
    is_active: bool
    triggered_count: int
    last_triggered: Optional[str] = None
    created_at: str


class Notification(BaseModel):
    """Notification model."""
    id: str
    user_id: str
    alert_id: Optional[str] = None
    title: str
    message: str
    severity: str = "info"
    is_read: bool = False
    created_at: str
    data: Optional[Dict[str, Any]] = None


class NotificationListResponse(BaseModel):
    """Response model for notification list."""
    notifications: List[Notification]
    total: int
    unread_count: int
