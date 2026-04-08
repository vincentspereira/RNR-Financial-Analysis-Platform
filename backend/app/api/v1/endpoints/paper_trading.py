"""
Paper Trading API endpoints.

Provides endpoints for paper trading portfolio management,
order placement, position management, and performance tracking.
"""
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.logging import get_logger
from app.schemas.paper_trading import (
    CreatePortfolioRequest,
    PlaceOrderRequest,
    PlaceOrderResponse,
)
from app.services.paper_trading.trading_engine import trading_engine
from app.services.auth.auth_service import auth_service

router = APIRouter(prefix="/paper-trading", tags=["paper-trading"])
logger = get_logger("api.paper_trading")


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


@router.post("/portfolios")
async def create_portfolio(
    request: CreatePortfolioRequest = CreatePortfolioRequest(),
    current_user=Depends(get_current_user_from_token),
):
    """Create a new paper trading portfolio."""
    user_id = _get_user_id(current_user)
    return trading_engine.create_portfolio(user_id, request.name, request.initial_capital)


@router.get("/portfolios")
async def list_portfolios(
    current_user=Depends(get_current_user_from_token),
):
    """List user's paper trading portfolios."""
    user_id = _get_user_id(current_user)
    portfolio = trading_engine.get_portfolio(user_id)
    if portfolio:
        return {"portfolios": [portfolio]}
    return {"portfolios": []}


@router.get("/portfolio")
async def get_portfolio(
    current_user=Depends(get_current_user_from_token),
):
    """Get active paper trading portfolio details."""
    user_id = _get_user_id(current_user)
    portfolio = trading_engine.get_portfolio(user_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="No paper trading portfolio found. Create one first.")
    return portfolio


@router.post("/orders", response_model=PlaceOrderResponse)
async def place_order(
    order: PlaceOrderRequest,
    current_user=Depends(get_current_user_from_token),
):
    """Place a paper trading order."""
    user_id = _get_user_id(current_user)
    return trading_engine.place_order(user_id, order)


@router.delete("/orders/{order_id}")
async def cancel_order(
    order_id: str,
    current_user=Depends(get_current_user_from_token),
):
    """Cancel a pending order (only available for limit/stop orders)."""
    user_id = _get_user_id(current_user)
    # Market orders fill instantly, only limit/stop orders can be cancelled
    raise HTTPException(status_code=501, detail="Order cancellation not yet implemented for market orders")


@router.get("/positions")
async def get_positions(
    current_user=Depends(get_current_user_from_token),
):
    """Get open positions."""
    user_id = _get_user_id(current_user)
    positions = trading_engine.get_positions(user_id)
    return {"positions": positions}


@router.post("/positions/{symbol}/close")
async def close_position(
    symbol: str,
    quantity: Optional[float] = Query(None),
    current_user=Depends(get_current_user_from_token),
):
    """Close a position (partially or fully)."""
    user_id = _get_user_id(current_user)
    result = trading_engine.close_position(user_id, symbol, quantity)
    if not result:
        raise HTTPException(status_code=404, detail=f"No position found for {symbol}")
    return result


@router.get("/trades")
async def get_trade_history(
    limit: int = Query(50, ge=1, le=200),
    current_user=Depends(get_current_user_from_token),
):
    """Get trade history."""
    user_id = _get_user_id(current_user)
    trades = trading_engine.get_trade_history(user_id, limit)
    return {"trades": trades}


@router.get("/performance")
async def get_performance(
    current_user=Depends(get_current_user_from_token),
):
    """Get trading performance metrics."""
    user_id = _get_user_id(current_user)
    return trading_engine.get_performance(user_id)


@router.get("/leaderboard")
async def get_leaderboard(
    current_user=Depends(get_current_user_from_token),
):
    """Get paper trading leaderboard."""
    return trading_engine.get_leaderboard()
