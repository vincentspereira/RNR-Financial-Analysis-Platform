"""
Notification & Alert API endpoints.

Provides endpoints for managing alerts and notifications.
"""
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.logging import get_logger
from app.schemas.notifications import (
    CreateAlertRequest,
    UpdateAlertRequest,
    NotificationListResponse,
)
from app.services.notifications.notification_service import notification_service
from app.services.auth.auth_service import auth_service

router = APIRouter(prefix="/notifications", tags=["notifications"])
logger = get_logger("api.notifications")


async def get_current_user_from_token(
    authorization: Annotated[Optional[str], Header()] = None,
    db: Annotated[AsyncSession, Depends(get_async_session)] = None,
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization header format")
    access_token = authorization.split(" ")[1]
    user = await auth_service.verify_session(access_token, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account is disabled")
    return user


def _get_user_id(user) -> str:
    return str(user.id) if hasattr(user, 'id') else str(user)


# --- Alert endpoints ---

@router.post("/alerts")
async def create_alert(
    request: CreateAlertRequest,
    current_user=Depends(get_current_user_from_token),
):
    """Create a new alert."""
    user_id = _get_user_id(current_user)
    alert = notification_service.create_alert(user_id, request)
    return alert


@router.get("/alerts")
async def list_alerts(
    current_user=Depends(get_current_user_from_token),
):
    """List all alerts for the current user."""
    user_id = _get_user_id(current_user)
    return notification_service.get_alerts(user_id)


@router.patch("/alerts/{alert_id}")
async def update_alert(
    alert_id: str,
    request: UpdateAlertRequest,
    current_user=Depends(get_current_user_from_token),
):
    """Update an alert (toggle active, rename)."""
    user_id = _get_user_id(current_user)
    result = notification_service.update_alert(user_id, alert_id, request.model_dump(exclude_none=True))
    if not result:
        raise HTTPException(status_code=404, detail="Alert not found")
    return result


@router.delete("/alerts/{alert_id}")
async def delete_alert(
    alert_id: str,
    current_user=Depends(get_current_user_from_token),
):
    """Delete an alert."""
    user_id = _get_user_id(current_user)
    deleted = notification_service.delete_alert(user_id, alert_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"message": "Alert deleted"}


# --- Notification endpoints ---

@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user=Depends(get_current_user_from_token),
):
    """List notifications with pagination."""
    user_id = _get_user_id(current_user)
    return notification_service.get_notifications(user_id, limit, offset)


@router.get("/unread-count")
async def get_unread_count(
    current_user=Depends(get_current_user_from_token),
):
    """Get unread notification count."""
    user_id = _get_user_id(current_user)
    count = notification_service.get_unread_count(user_id)
    return {"unread_count": count}


@router.patch("/{notification_id}/read")
async def mark_as_read(
    notification_id: str,
    current_user=Depends(get_current_user_from_token),
):
    """Mark a notification as read."""
    user_id = _get_user_id(current_user)
    marked = notification_service.mark_as_read(user_id, notification_id)
    if not marked:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Notification marked as read"}


@router.post("/mark-all-read")
async def mark_all_read(
    current_user=Depends(get_current_user_from_token),
):
    """Mark all notifications as read."""
    user_id = _get_user_id(current_user)
    count = notification_service.mark_all_read(user_id)
    return {"message": f"Marked {count} notifications as read"}
