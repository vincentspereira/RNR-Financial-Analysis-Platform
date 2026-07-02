"""
Pydantic schemas for the IBKR integration.

Used for the /api/v1/ibkr/* REST endpoints.
"""
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class OrderAction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class TimeInForce(str, Enum):
    DAY = "DAY"
    GTC = "GTC"  # Good-til-cancelled
    IOC = "IOC"  # Immediate-or-cancel
    GTD = "GTD"  # Good-til-date


class IBKROrderStatus(str, Enum):
    PENDING_SUBMIT = "pending_submit"
    SUBMITTED = "submitted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    PENDING_CANCEL = "pending_cancel"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    UNKNOWN = "unknown"


class PlaceIBKROrderRequest(BaseModel):
    """Request body for POST /api/v1/ibkr/orders."""

    symbol: str = Field(min_length=1, max_length=16)
    action: OrderAction
    order_type: OrderType = OrderType.MARKET
    quantity: float = Field(gt=0)
    limit_price: Optional[float] = Field(default=None, gt=0)
    stop_price: Optional[float] = Field(default=None, gt=0)
    time_in_force: TimeInForce = TimeInForce.DAY

    # Contract specification (defaults are standard US equities)
    sec_type: str = Field(default="STK", pattern="^(STK|OPT|FUT|CASH)$")
    exchange: str = Field(default="SMART", max_length=16)
    currency: str = Field(default="USD", min_length=3, max_length=4)

    @field_validator("symbol")
    @classmethod
    def upper_symbol(cls, v: str) -> str:
        return v.strip().upper()


class IBKROrderRecord(BaseModel):
    """Serialised IBKROrder row."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    client_order_id: str
    ib_order_id: Optional[int] = None
    ib_perm_id: Optional[int] = None
    account_id: Optional[str] = None
    symbol: str
    sec_type: str
    exchange: str
    currency: str
    action: str
    order_type: str
    quantity: Decimal
    limit_price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    time_in_force: str
    status: str
    filled_quantity: Decimal
    avg_fill_price: Optional[Decimal] = None
    notional_usd_at_submit: Optional[Decimal] = None
    last_error: Optional[str] = None
    submitted_at: datetime
    updated_at: datetime


class IBKRConnectionStatusResponse(BaseModel):
    """Response for GET /api/v1/ibkr/status."""

    state: str
    host: str
    port: int
    client_id: int
    account_id: Optional[str] = None
    readonly: bool
    last_error: Optional[str] = None
    reconnect_attempts: int = 0
    server_version: Optional[int] = None


class IBKRPositionRow(BaseModel):
    """One position from IBKR."""

    account: str
    symbol: str
    sec_type: str
    exchange: str
    currency: str
    quantity: float
    avg_cost: float
    market_price: Optional[float] = None
    market_value: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    realized_pnl: Optional[float] = None


class IBKRPositionsResponse(BaseModel):
    positions: List[IBKRPositionRow]


class IBKRAccountSummaryResponse(BaseModel):
    """Selected fields from IBKR account summary."""

    account: str
    net_liquidation: Optional[float] = None
    total_cash_value: Optional[float] = None
    buying_power: Optional[float] = None
    available_funds: Optional[float] = None
    excess_liquidity: Optional[float] = None
    gross_position_value: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    realized_pnl: Optional[float] = None
    currency: Optional[str] = "USD"


class IBKRSyncResponse(BaseModel):
    updated: int


class IBKROrderListResponse(BaseModel):
    orders: List[IBKROrderRecord]


class IBKRMarketDataSnapshot(BaseModel):
    """Snapshot quote for one symbol."""

    symbol: str
    bid: Optional[float] = None
    ask: Optional[float] = None
    last: Optional[float] = None
    close: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    volume: Optional[float] = None
    timestamp: datetime
