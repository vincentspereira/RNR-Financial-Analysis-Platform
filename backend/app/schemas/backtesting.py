"""
Pydantic v2 schemas for backtesting endpoints.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class StrategyConfig(BaseModel):
    """Strategy configuration for backtesting."""
    strategy_type: str = Field(
        ...,
        description="Strategy type: sma_crossover, ema_crossover, rsi_oversold_overbought, bollinger_breakout, macd_signal, dual_momentum",
    )
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Strategy-specific parameters",
    )


class SlippageConfigSchema(BaseModel):
    """Slippage model configuration."""
    model: str = Field(default="percentage", pattern=r"^(fixed|percentage|volume_based)$")
    value: float = Field(default=0.001, ge=0)


class TransactionCostConfigSchema(BaseModel):
    """Transaction cost model configuration."""
    model: str = Field(default="percentage", pattern=r"^(flat|per_share|percentage)$")
    value: float = Field(default=0.001, ge=0)


class BacktestRequest(BaseModel):
    """Request to run a backtest."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "symbols": ["AAPL"],
                "strategy": {"strategy_type": "sma_crossover", "parameters": {"fast_period": 20, "slow_period": 50}},
                "initial_capital": 100000,
                "lookback_days": 504,
            }
        }
    )

    symbols: List[str] = Field(..., min_length=1, max_length=50)
    strategy: StrategyConfig
    initial_capital: float = Field(default=100000, gt=0)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    lookback_days: Optional[int] = Field(default=504, ge=30, le=2000)
    slippage: Optional[SlippageConfigSchema] = None
    transaction_costs: Optional[TransactionCostConfigSchema] = None
    benchmark_symbol: Optional[str] = "SPY"
    position_size_pct: float = Field(default=1.0, gt=0, le=1.0)


class TradeRecordResponse(BaseModel):
    """A single trade record in the backtest."""
    symbol: str
    action: str
    date: date
    price: float
    shares: float
    commission: float
    slippage_cost: float
    pnl: Optional[float] = None


class BacktestMetricsResponse(BaseModel):
    """Performance metrics from a backtest."""
    total_return: float
    annualized_return: float
    cagr: float
    max_drawdown: float
    max_drawdown_duration_days: int
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    win_rate: float
    profit_factor: float
    avg_win: float
    avg_loss: float
    total_trades: int
    avg_holding_period_days: float
    alpha: Optional[float] = None
    beta: Optional[float] = None
    information_ratio: Optional[float] = None


class BacktestResponse(BaseModel):
    """Complete backtest result."""
    status: str
    strategy: str
    symbols: List[str]
    initial_capital: float
    final_value: float
    metrics: BacktestMetricsResponse
    equity_curve: List[Dict[str, Any]]
    trades: List[TradeRecordResponse]
    benchmark_total_return: Optional[float] = None
    run_date: datetime


class BacktestCompareRequest(BaseModel):
    """Request to compare multiple strategies."""
    symbols: List[str] = Field(..., min_length=1, max_length=50)
    strategies: List[StrategyConfig] = Field(..., min_length=2, max_length=10)
    initial_capital: float = Field(default=100000, gt=0)
    lookback_days: Optional[int] = Field(default=504, ge=30, le=2000)


class BacktestCompareResponse(BaseModel):
    """Comparison of multiple strategy backtests."""
    results: List[BacktestResponse]
    comparison_metrics: Dict[str, Dict[str, float]]


class StrategyInfo(BaseModel):
    """Information about an available strategy."""
    strategy_type: str
    description: str
    default_parameters: Dict[str, Any]


class StrategiesListResponse(BaseModel):
    """List of available strategies."""
    total: int
    strategies: List[StrategyInfo]
