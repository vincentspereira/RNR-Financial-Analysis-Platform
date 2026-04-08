"""
Stock Screener API endpoints.

Provides endpoints for running stock screeners, managing presets,
and saving custom screeners.
"""
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.logging import get_logger
from app.schemas.screener import (
    SaveScreenerRequest,
    ScreenerFilter,
    ScreenerResponse,
)
from app.services.screener.screener_service import screener_service
from app.services.auth.auth_service import auth_service

router = APIRouter(prefix="/screener", tags=["screener"])
logger = get_logger("api.screener")


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


@router.post("/run", response_model=ScreenerResponse)
async def run_screener(
    filters: ScreenerFilter,
    current_user=Depends(get_current_user_from_token),
):
    """Run a custom stock screener with specified filters."""
    return screener_service.run_screener(filters)


@router.get("/presets")
async def get_preset_screeners(
    current_user=Depends(get_current_user_from_token),
):
    """Get all preset screener templates."""
    presets = screener_service.get_presets()
    return {"presets": presets}


@router.post("/presets/{preset_name}/run", response_model=ScreenerResponse)
async def run_preset_screener(
    preset_name: str,
    current_user=Depends(get_current_user_from_token),
):
    """Run a preset screener by name."""
    preset = screener_service.get_preset(preset_name)
    if not preset:
        raise HTTPException(status_code=404, detail=f"Preset '{preset_name}' not found")
    return screener_service.run_screener(preset.filters, preset_name=preset.name)


@router.post("/save")
async def save_screener(
    request: SaveScreenerRequest,
    current_user=Depends(get_current_user_from_token),
):
    """Save a custom screener."""
    user_id = str(current_user.id) if hasattr(current_user, 'id') else str(current_user)
    return screener_service.save_screener(user_id, request.name, request.filters)


@router.get("/saved")
async def get_saved_screeners(
    current_user=Depends(get_current_user_from_token),
):
    """Get user's saved custom screeners."""
    user_id = str(current_user.id) if hasattr(current_user, 'id') else str(current_user)
    return {"screeners": screener_service.get_user_screeners(user_id)}


@router.delete("/saved/{screener_id}")
async def delete_saved_screener(
    screener_id: str,
    current_user=Depends(get_current_user_from_token),
):
    """Delete a saved custom screener."""
    user_id = str(current_user.id) if hasattr(current_user, 'id') else str(current_user)
    deleted = screener_service.delete_screener(user_id, screener_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Screener not found")
    return {"message": "Screener deleted"}
