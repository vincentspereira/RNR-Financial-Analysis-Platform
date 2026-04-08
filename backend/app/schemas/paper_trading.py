"""
Paper trading schemas for request/response models.
"""
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(str, Enum):
    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class PlaceOrderRequest(BaseModel):
    """Request to place a paper trading order."""
    symbol: str
    side: OrderSide
    order_type: OrderType = OrderType.MARKET
    quantity: float = Field(gt=0)
    price: Optional[float] = None
    stop_price: Optional[float] = None
    portfolio_id: Optional[str] = None


class Position(BaseModel):
    """Open position model."""
    symbol: str
    side: str
    quantity: float
    avg_entry_price: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_percent: float
    cost_basis: float


class Trade(BaseModel):
    """Executed trade model."""
    id: str
    symbol: str
    side: str
    order_type: str
    quantity: float
    fill_price: float
    total_value: float
    commission: float
    timestamp: str
    status: str


class PaperPortfolio(BaseModel):
    """Paper trading portfolio model."""
    id: str
    user_id: str
    name: str
    initial_capital: float
    cash_balance: float
    positions: List[Position]
    total_value: float
    total_pnl: float
    total_pnl_percent: float
    total_trades: int
    win_rate: float
    created_at: str


class PlaceOrderResponse(BaseModel):
    """Response after placing an order."""
    order_id: str
    status: OrderStatus
    symbol: str
    side: OrderSide
    quantity: float
    fill_price: Optional[float] = None
    total_value: Optional[float] = None
    commission: Optional[float] = None
    message: str


class CreatePortfolioRequest(BaseModel):
    """Request to create a paper trading portfolio."""
    name: str = "My Paper Portfolio"
    initial_capital: float = Field(default=100000.0, gt=0)


class PerformanceMetrics(BaseModel):
    """Trading performance metrics."""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_win: float
    avg_loss: float
    best_trade: float
    worst_trade: float
    total_pnl: float
    sharpe_ratio: Optional[float] = None


class LeaderboardEntry(BaseModel):
    """Leaderboard entry."""
    user_name: str
    total_pnl_percent: float
    total_value: float
    win_rate: float
