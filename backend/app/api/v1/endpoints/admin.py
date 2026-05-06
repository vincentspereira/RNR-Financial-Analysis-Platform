"""
Admin Dashboard API endpoints.

Provides endpoints for user management, system metrics, revenue analytics,
activity logging, and SOC 2 compliance reporting. All endpoints require admin role.
"""
from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, Header
from pydantic import BaseModel, Field
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


# ---------------------------------------------------------------------------
# SOC 2 Compliance endpoints
# ---------------------------------------------------------------------------

class ComplianceReportRequest(BaseModel):
    start_date: Optional[datetime] = Field(None, description="Report start date")
    end_date: Optional[datetime] = Field(None, description="Report end date")
    tsc_category: Optional[str] = Field(None, description="Filter by TSC category")


@router.get("/compliance/report")
async def get_soc2_compliance_report(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    tsc_category: Optional[str] = None,
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_async_session),
):
    """Generate SOC 2 compliance report for a period."""
    from app.core.compliance import soc2_service
    return await soc2_service.get_compliance_report(
        session=db,
        start_date=start_date,
        end_date=end_date,
        tsc_category=tsc_category,
    )


@router.get("/compliance/integrity-check")
async def verify_audit_integrity(
    limit: int = Query(100, ge=10, le=1000),
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_async_session),
):
    """Verify integrity hashes of audit log entries."""
    from app.core.compliance import soc2_service
    return await soc2_service.verify_audit_integrity(session=db, limit=limit)


@router.post("/compliance/event")
async def log_compliance_event(
    action: str = Query(..., description="Action name"),
    resource_type: str = Query(..., description="Resource type"),
    resource_id: Optional[str] = None,
    success: bool = True,
    error_message: Optional[str] = None,
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_async_session),
):
    """Manually log a SOC 2 compliance event."""
    from app.core.compliance import soc2_service
    from uuid import UUID as UUIDType
    log = await soc2_service.log_compliance_event(
        session=db,
        action=action,
        resource_type=resource_type,
        user_id=admin.id if hasattr(admin, 'id') else None,
        resource_id=UUID(resource_id) if resource_id else None,
        success=success,
        error_message=error_message,
        metadata={"source": "admin_api"},
    )
    return {"id": str(log.id), "action": action, "logged": True}
