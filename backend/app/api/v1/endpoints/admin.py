"""
Admin Dashboard API endpoints.

Provides endpoints for user management, system metrics, revenue analytics,
and activity logging. All endpoints require admin role.
"""
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.logging import get_logger
from app.schemas.admin import UpdateUserRequest
from app.services.admin.admin_service import admin_service
from app.services.auth.auth_service import auth_service

router = APIRouter(prefix="/admin", tags=["admin"])
logger = get_logger("api.admin")


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


async def require_admin(current_user=Depends(get_current_user_from_token)):
    """Verify the current user has admin privileges."""
    is_super = getattr(current_user, 'is_superuser', False)
    if not is_super:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@router.get("/users")
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    role: Optional[str] = None,
    active_only: bool = False,
    admin=Depends(require_admin),
):
    """List all users with pagination and filters."""
    return admin_service.get_users(page, page_size, search, role, active_only)


@router.get("/users/{user_id}")
async def get_user(
    user_id: str,
    admin=Depends(require_admin),
):
    """Get a single user by ID."""
    user = admin_service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/users/{user_id}")
async def update_user(
    user_id: str,
    updates: UpdateUserRequest,
    admin=Depends(require_admin),
):
    """Update user role, status, or subscription tier."""
    result = admin_service.update_user(user_id, updates.model_dump(exclude_none=True))
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    return result


@router.get("/metrics")
async def get_system_metrics(
    admin=Depends(require_admin),
):
    """Get system-wide metrics."""
    return admin_service.get_system_metrics()


@router.get("/revenue")
async def get_revenue_metrics(
    admin=Depends(require_admin),
):
    """Get revenue and subscription metrics."""
    return admin_service.get_revenue_metrics()


@router.get("/activity-log")
async def get_activity_log(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    admin=Depends(require_admin),
):
    """Get activity log with pagination."""
    return admin_service.get_activity_log(page, page_size, user_id, action)
