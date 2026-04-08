"""
Notification and alert management service.

Manages user alerts (price, portfolio, volume) and in-app notifications.
"""
import asyncio
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.core.logging import get_logger
from app.schemas.notifications import (
    AlertCondition,
    AlertResponse,
    CreateAlertRequest,
    Notification,
)

logger = get_logger("app.services.notifications")

# In-memory storage
_alerts: Dict[str, List[Dict]] = {}  # user_id -> list of alerts
_notifications: Dict[str, List[Dict]] = {}  # user_id -> list of notifications


class NotificationService:
    """Manage alerts and notifications."""

    def create_alert(self, user_id: str, request: CreateAlertRequest) -> AlertResponse:
        """Create a new alert for a user."""
        alert_id = str(uuid4())
        alert = {
            "id": alert_id,
            "user_id": user_id,
            "name": request.name,
            "condition": request.condition.model_dump(),
            "notification_methods": request.notification_methods,
            "is_active": True,
            "triggered_count": 0,
            "last_triggered": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        if user_id not in _alerts:
            _alerts[user_id] = []
        _alerts[user_id].append(alert)
        return AlertResponse(**alert)

    def get_alerts(self, user_id: str) -> List[AlertResponse]:
        """Get all alerts for a user."""
        return [AlertResponse(**a) for a in _alerts.get(user_id, [])]

    def update_alert(self, user_id: str, alert_id: str, updates: Dict) -> Optional[AlertResponse]:
        """Update an alert."""
        for alert in _alerts.get(user_id, []):
            if alert["id"] == alert_id:
                if "is_active" in updates and updates["is_active"] is not None:
                    alert["is_active"] = updates["is_active"]
                if "name" in updates and updates["name"] is not None:
                    alert["name"] = updates["name"]
                return AlertResponse(**alert)
        return None

    def delete_alert(self, user_id: str, alert_id: str) -> bool:
        """Delete an alert."""
        if user_id in _alerts:
            original_len = len(_alerts[user_id])
            _alerts[user_id] = [a for a in _alerts[user_id] if a["id"] != alert_id]
            return len(_alerts[user_id]) < original_len
        return False

    def create_notification(
        self,
        user_id: str,
        title: str,
        message: str,
        severity: str = "info",
        alert_id: Optional[str] = None,
        data: Optional[Dict] = None,
    ) -> Notification:
        """Create a new notification."""
        notif_id = str(uuid4())
        notif = {
            "id": notif_id,
            "user_id": user_id,
            "alert_id": alert_id,
            "title": title,
            "message": message,
            "severity": severity,
            "is_read": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }
        if user_id not in _notifications:
            _notifications[user_id] = []
        _notifications[user_id].insert(0, notif)  # Newest first
        return Notification(**notif)

    def get_notifications(
        self, user_id: str, limit: int = 50, offset: int = 0
    ) -> Dict:
        """Get notifications with pagination."""
        user_notifs = _notifications.get(user_id, [])
        unread_count = sum(1 for n in user_notifs if not n["is_read"])
        paginated = user_notifs[offset: offset + limit]
        return {
            "notifications": [Notification(**n) for n in paginated],
            "total": len(user_notifs),
            "unread_count": unread_count,
        }

    def get_unread_count(self, user_id: str) -> int:
        """Get unread notification count."""
        return sum(1 for n in _notifications.get(user_id, []) if not n["is_read"])

    def mark_as_read(self, user_id: str, notification_id: str) -> bool:
        """Mark a notification as read."""
        for notif in _notifications.get(user_id, []):
            if notif["id"] == notification_id:
                notif["is_read"] = True
                return True
        return False

    def mark_all_read(self, user_id: str) -> int:
        """Mark all notifications as read. Returns count marked."""
        count = 0
        for notif in _notifications.get(user_id, []):
            if not notif["is_read"]:
                notif["is_read"] = True
                count += 1
        return count

    def delete_notification(self, user_id: str, notification_id: str) -> bool:
        """Delete a notification."""
        if user_id in _notifications:
            original_len = len(_notifications[user_id])
            _notifications[user_id] = [
                n for n in _notifications[user_id] if n["id"] != notification_id
            ]
            return len(_notifications[user_id]) < original_len
        return False


notification_service = NotificationService()
