"""
IBKR REST endpoints.

Routes (all under /api/v1/ibkr):
- GET    /status              connection status + safety counters
- POST   /connect             open connection to TWS / Gateway
- POST   /disconnect          close connection
- GET    /account             account summary (net liq, buying power, cash...)
- GET    /positions           current positions held at IBKR
- POST   /orders              place an order (BUY/SELL, market/limit/stop)
- GET    /orders              list orders persisted from this platform
- GET    /orders/{id}         single order (refreshes status from IBKR)
- DELETE /orders/{id}         cancel order
- POST   /orders/sync         sync open-order status from IBKR -> DB
- GET    /quote/{symbol}      snapshot market data quote

All routes require an authenticated user. Order placement additionally
requires `IBKR_READONLY=false`.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_async_session
from app.core.logging import get_logger
from app.schemas.ibkr import (
    IBKRAccountSummaryResponse,
    IBKRConnectionStatusResponse,
    IBKRMarketDataSnapshot,
    IBKROrderListResponse,
    IBKROrderRecord,
    IBKRPositionRow,
    IBKRPositionsResponse,
    IBKRSyncResponse,
    PlaceIBKROrderRequest,
)
from app.services.auth.auth_service import auth_service
from app.services.ibkr.client import (
    IBKRConnectionError,
    IBKRNotAvailableError,
    ibkr_client,
)
from app.services.ibkr.contracts import contract_resolver
from app.services.ibkr.orders import OrderRejectedError, order_manager
from app.services.ibkr.safety import SafetyLimitExceeded

router = APIRouter(prefix="/ibkr", tags=["ibkr"])
logger = get_logger("api.ibkr")


# ----------------------------------------------------------------------------
# Auth dependency (mirrors paper_trading.py)
# ----------------------------------------------------------------------------
async def get_current_user(
    authorization: Annotated[Optional[str], Header()] = None,
    db: Annotated[AsyncSession, Depends(get_async_session)] = None,
):
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


def _require_enabled() -> None:
    if not settings.IBKR_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "IBKR integration is disabled. Set IBKR_ENABLED=true in .env "
                "and restart the backend."
            ),
        )


def _require_writeable() -> None:
    if settings.IBKR_READONLY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "IBKR integration is in read-only mode. Set IBKR_READONLY=false "
                "in .env to enable order placement."
            ),
        )


# ----------------------------------------------------------------------------
# Connection management
# ----------------------------------------------------------------------------

@router.get("/status", response_model=IBKRConnectionStatusResponse)
async def get_status(current_user=Depends(get_current_user)):
    s = ibkr_client.status()
    return IBKRConnectionStatusResponse(
        state=s.state.value,
        host=s.host,
        port=s.port,
        client_id=s.client_id,
        account_id=s.account_id,
        readonly=s.readonly,
        last_error=s.last_error,
        reconnect_attempts=s.reconnect_attempts,
        server_version=s.server_version,
    )


@router.post("/connect", response_model=IBKRConnectionStatusResponse)
async def connect(current_user=Depends(get_current_user)):
    _require_enabled()
    try:
        s = await ibkr_client.connect()
    except IBKRNotAvailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except IBKRConnectionError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return IBKRConnectionStatusResponse(
        state=s.state.value,
        host=s.host,
        port=s.port,
        client_id=s.client_id,
        account_id=s.account_id,
        readonly=s.readonly,
        last_error=s.last_error,
        reconnect_attempts=s.reconnect_attempts,
        server_version=s.server_version,
    )


@router.post("/disconnect")
async def disconnect(current_user=Depends(get_current_user)):
    await ibkr_client.disconnect()
    return {"status": "disconnected"}


# ----------------------------------------------------------------------------
# Account & positions
# ----------------------------------------------------------------------------

_ACCOUNT_TAGS = [
    "NetLiquidation",
    "TotalCashValue",
    "BuyingPower",
    "AvailableFunds",
    "ExcessLiquidity",
    "GrossPositionValue",
    "UnrealizedPnL",
    "RealizedPnL",
]


@router.get("/account", response_model=IBKRAccountSummaryResponse)
async def get_account_summary(current_user=Depends(get_current_user)):
    _require_enabled()
    try:
        ib = await ibkr_client.ensure_connected()
    except (IBKRNotAvailableError, IBKRConnectionError) as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    account = settings.IBKR_ACCOUNT_ID or ""
    try:
        summary_rows = await ib.accountSummaryAsync(account=account)
    except Exception as exc:
        logger.error("accountSummary failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"IBKR accountSummary failed: {exc}")

    by_tag = {row.tag: row for row in summary_rows if row.tag in _ACCOUNT_TAGS}

    def _f(tag: str) -> Optional[float]:
        row = by_tag.get(tag)
        if row is None or row.value in (None, ""):
            return None
        try:
            return float(row.value)
        except (TypeError, ValueError):
            return None

    return IBKRAccountSummaryResponse(
        account=account or (next(iter(summary_rows), None).account if summary_rows else "") or "",
        net_liquidation=_f("NetLiquidation"),
        total_cash_value=_f("TotalCashValue"),
        buying_power=_f("BuyingPower"),
        available_funds=_f("AvailableFunds"),
        excess_liquidity=_f("ExcessLiquidity"),
        gross_position_value=_f("GrossPositionValue"),
        unrealized_pnl=_f("UnrealizedPnL"),
        realized_pnl=_f("RealizedPnL"),
        currency=(by_tag.get("NetLiquidation").currency if by_tag.get("NetLiquidation") else "USD"),
    )


@router.get("/positions", response_model=IBKRPositionsResponse)
async def get_positions(current_user=Depends(get_current_user)):
    _require_enabled()
    try:
        ib = await ibkr_client.ensure_connected()
    except (IBKRNotAvailableError, IBKRConnectionError) as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    raw = ib.positions(account=settings.IBKR_ACCOUNT_ID or "")
    positions: List[IBKRPositionRow] = []
    for p in raw:
        c = p.contract
        positions.append(
            IBKRPositionRow(
                account=p.account,
                symbol=c.symbol,
                sec_type=c.secType,
                exchange=getattr(c, "exchange", "") or "",
                currency=c.currency,
                quantity=float(p.position),
                avg_cost=float(p.avgCost),
            )
        )
    return IBKRPositionsResponse(positions=positions)


# ----------------------------------------------------------------------------
# Orders
# ----------------------------------------------------------------------------

@router.post("/orders", response_model=IBKROrderRecord)
async def place_order(
    req: PlaceIBKROrderRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    _require_enabled()
    _require_writeable()
    try:
        return await order_manager.place_order(db, current_user.id, req)
    except SafetyLimitExceeded as exc:
        raise HTTPException(status_code=429, detail=exc.decision.reason)
    except OrderRejectedError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except (IBKRNotAvailableError, IBKRConnectionError) as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.get("/orders", response_model=IBKROrderListResponse)
async def list_orders(
    include_closed: bool = Query(True),
    limit: int = Query(50, ge=1, le=200),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    orders = await order_manager.list_orders(
        db, current_user.id, limit=limit, include_closed=include_closed
    )
    return IBKROrderListResponse(orders=orders)


@router.get("/orders/{order_id}", response_model=IBKROrderRecord)
async def get_order(
    order_id: UUID = Path(...),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    try:
        return await order_manager.get_order(db, current_user.id, order_id)
    except OrderRejectedError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/orders/{order_id}", response_model=IBKROrderRecord)
async def cancel_order(
    order_id: UUID = Path(...),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    _require_enabled()
    _require_writeable()
    try:
        return await order_manager.cancel_order(db, current_user.id, order_id)
    except OrderRejectedError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except (IBKRNotAvailableError, IBKRConnectionError) as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.post("/orders/sync", response_model=IBKRSyncResponse)
async def sync_open_orders(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    _require_enabled()
    try:
        updated = await order_manager.sync_open_orders(db, current_user.id)
    except (IBKRNotAvailableError, IBKRConnectionError) as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return IBKRSyncResponse(updated=updated)


# ----------------------------------------------------------------------------
# Market data
# ----------------------------------------------------------------------------

@router.get("/quote/{symbol}", response_model=IBKRMarketDataSnapshot)
async def get_quote(
    symbol: str = Path(..., min_length=1, max_length=16),
    sec_type: str = Query("STK", pattern="^(STK|OPT|FUT|CASH)$"),
    exchange: str = Query("SMART"),
    currency: str = Query("USD"),
    current_user=Depends(get_current_user),
):
    _require_enabled()
    try:
        contract = await contract_resolver.resolve(
            symbol=symbol, sec_type=sec_type, exchange=exchange, currency=currency
        )
        ib = await ibkr_client.ensure_connected()
    except (IBKRNotAvailableError, IBKRConnectionError) as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    ticker = ib.reqMktData(contract, "", False, False)
    try:
        # Up to 3s for snapshot data to settle
        for _ in range(30):
            await asyncio.sleep(0.1)
            if ticker.last or ticker.close or ticker.bid:
                break
    finally:
        ib.cancelMktData(contract)

    return IBKRMarketDataSnapshot(
        symbol=symbol.upper(),
        bid=float(ticker.bid) if ticker.bid and ticker.bid > 0 else None,
        ask=float(ticker.ask) if ticker.ask and ticker.ask > 0 else None,
        last=float(ticker.last) if ticker.last and ticker.last > 0 else None,
        close=float(ticker.close) if ticker.close and ticker.close > 0 else None,
        high=float(ticker.high) if ticker.high and ticker.high > 0 else None,
        low=float(ticker.low) if ticker.low and ticker.low > 0 else None,
        volume=float(ticker.volume) if ticker.volume and ticker.volume > 0 else None,
        timestamp=datetime.now(timezone.utc),
    )
