"""
Real-time market data API endpoints.

Provides endpoints for managing market data subscriptions, checking streamer
status, and retrieving the latest price for a symbol.
"""
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.logging import get_logger
from app.models.company import Company, MarketData
from app.schemas.market_data import (
    MarketDataSubscription,
    MarketDataUnsubscription,
    MarketDataResponse,
    StreamerStatusResponse,
    SubscriptionResponse,
    UserSubscriptionsResponse,
    SubscriptionStatsResponse,
)
from app.services.market_data import market_data_streamer, subscription_manager
from app.services.auth.auth_service import auth_service

router = APIRouter(prefix="/market-data", tags=["market-data"])
logger = get_logger("api.market_data")


# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------


async def get_current_user_from_token(
    authorization: Annotated[Optional[str], Header()] = None,
    db: Annotated[AsyncSession, Depends(get_async_session)] = None,
):
    """Validate Bearer token and return the authenticated user."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
        )

    access_token = authorization.split(" ")[1]
    user = await auth_service.verify_session(access_token, db)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled",
        )

    return user


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/streamer/status",
    response_model=StreamerStatusResponse,
    summary="Get streamer status",
    description="Returns the current status of the market data WebSocket streamer.",
)
async def get_streamer_status(
    current_user=Depends(get_current_user_from_token),
):
    """Get the market data streamer connection status."""
    status_data = market_data_streamer.get_status()
    return StreamerStatusResponse(**status_data)


@router.post(
    "/subscribe",
    response_model=SubscriptionResponse,
    summary="Subscribe to symbols",
    description="Subscribe the authenticated user to real-time market data for the given symbols.",
)
async def subscribe_to_symbols(
    request: MarketDataSubscription,
    current_user=Depends(get_current_user_from_token),
):
    """Subscribe to real-time market data for specific symbols."""
    try:
        user_id = str(current_user.id)
        connection_id = f"{user_id}_default"

        new_symbols = await subscription_manager.subscribe(
            user_id=user_id,
            connection_id=connection_id,
            symbols=request.symbols,
        )

        # Also subscribe on the Polygon streamer
        await market_data_streamer.subscribe_symbols(request.symbols)

        return SubscriptionResponse(
            success=True,
            symbols=new_symbols,
            message=f"Subscribed to {len(new_symbols)} new symbols",
        )
    except Exception as exc:
        logger.error(f"Subscription error: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Subscription failed. Please try again later.",
        )


@router.post(
    "/unsubscribe",
    response_model=SubscriptionResponse,
    summary="Unsubscribe from symbols",
    description="Unsubscribe the authenticated user from real-time market data for the given symbols.",
)
async def unsubscribe_from_symbols(
    request: MarketDataUnsubscription,
    current_user=Depends(get_current_user_from_token),
):
    """Unsubscribe from real-time market data for specific symbols."""
    try:
        user_id = str(current_user.id)
        removed = await subscription_manager.unsubscribe(
            user_id=user_id,
            symbols=request.symbols,
        )

        # Check if any other users still need these symbols before unsubscribing from Polygon
        symbols_to_unsubscribe = []
        for symbol in removed:
            if subscription_manager.get_symbol_subscriber_count(symbol) == 0:
                symbols_to_unsubscribe.append(symbol)

        if symbols_to_unsubscribe:
            await market_data_streamer.unsubscribe_symbols(symbols_to_unsubscribe)

        return SubscriptionResponse(
            success=True,
            symbols=removed,
            message=f"Unsubscribed from {len(removed)} symbols",
        )
    except Exception as exc:
        logger.error(f"Unsubscribe error: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unsubscribe failed. Please try again later.",
        )


@router.get(
    "/subscriptions",
    response_model=UserSubscriptionsResponse,
    summary="Get user subscriptions",
    description="Get the list of symbols the authenticated user is currently subscribed to.",
)
async def get_user_subscriptions(
    current_user=Depends(get_current_user_from_token),
):
    """Get the user's current market data subscriptions."""
    user_id = str(current_user.id)
    symbols = subscription_manager.get_user_subscriptions(user_id)
    return UserSubscriptionsResponse(
        user_id=user_id,
        symbols=symbols,
        total=len(symbols),
    )


@router.get(
    "/stats",
    response_model=SubscriptionStatsResponse,
    summary="Get subscription statistics",
    description="Get global subscription statistics (admin-level overview).",
)
async def get_subscription_stats(
    current_user=Depends(get_current_user_from_token),
):
    """Get global subscription statistics."""
    stats = subscription_manager.get_stats()
    return SubscriptionStatsResponse(**stats)


@router.get(
    "/latest/{symbol}",
    response_model=MarketDataResponse,
    summary="Get latest price",
    description="Get the latest market data for a specific symbol from the database.",
)
async def get_latest_price(
    symbol: str,
    db: Annotated[AsyncSession, Depends(get_async_session)],
    current_user=Depends(get_current_user_from_token),
):
    """Get the latest market data for a symbol from the database."""
    try:
        # Resolve symbol to company
        company_stmt = select(Company.id, Company.symbol).where(
            Company.symbol == symbol.upper()
        )
        company_result = await db.execute(company_stmt)
        company = company_result.first()

        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company not found for symbol: {symbol}",
            )

        # Get latest market data
        md_stmt = (
            select(MarketData)
            .where(MarketData.company_id == company.id)
            .order_by(desc(MarketData.price_date))
            .limit(1)
        )
        md_result = await db.execute(md_stmt)
        market_data = md_result.scalar_one_or_none()

        if not market_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No market data found for symbol: {symbol}",
            )

        return MarketDataResponse(
            symbol=company.symbol,
            price=market_data.close_price,
            volume=market_data.volume,
            timestamp=market_data.created_at,
            open=market_data.open_price,
            high=market_data.high_price,
            low=market_data.low_price,
            change=market_data.adjusted_close - market_data.open_price
                if market_data.adjusted_close and market_data.open_price else None,
            change_percent=(
                (market_data.adjusted_close - market_data.open_price) / market_data.open_price * 100
                if market_data.adjusted_close and market_data.open_price and market_data.open_price > 0
                else None
            ),
            source=market_data.data_source,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error fetching latest price for {symbol}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve market data. Please try again later.",
        )
