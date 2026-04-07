"""
Pydantic v2 schemas for portfolio optimization endpoints.
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class PortfolioOptimizationRequest(BaseModel):
    """Request body for portfolio weight optimization."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "symbols": ["AAPL", "MSFT", "GOOGL", "AMZN"],
                "optimization_method": "max_sharpe",
                "risk_free_rate": 0.02,
                "lookback_days": 252,
                "constraints": {"min_weight": 0.05, "max_weight": 0.40},
            }
        }
    )

    portfolio_id: Optional[str] = Field(
        None,
        description="UUID of an existing portfolio to use its holdings",
    )
    symbols: Optional[List[str]] = Field(
        None,
        max_length=50,
        description="Ticker symbols to optimize (alternative to portfolio_id)",
    )
    optimization_method: str = Field(
        default="max_sharpe",
        pattern=r"^(max_sharpe|min_variance|target_return|equal_weight|risk_parity)$",
        description="Optimization objective",
    )
    risk_free_rate: Optional[float] = Field(
        default=0.02,
        ge=0,
        le=0.1,
        description="Annual risk-free rate (decimal)",
    )
    lookback_days: Optional[int] = Field(
        default=252,
        ge=30,
        le=1000,
        description="Number of trading days of history to use",
    )
    target_return: Optional[float] = Field(
        None,
        description="Target annualized return (required when method=target_return)",
    )
    risk_tolerance: Optional[float] = Field(
        None,
        description="Maximum acceptable annualized volatility",
    )
    constraints: Optional[Dict[str, Any]] = Field(
        None,
        description=(
            "Weight constraints: min_weight, max_weight (global), "
            "or per_symbol={SYMBOL: {min: x, max: y}}"
        ),
    )


class EfficientFrontierRequest(BaseModel):
    """Request body for efficient frontier calculation."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "symbols": ["AAPL", "MSFT", "GOOGL"],
                "num_portfolios": 5000,
                "risk_free_rate": 0.02,
            }
        }
    )

    symbols: List[str] = Field(
        ...,
        min_length=2,
        max_length=50,
        description="Ticker symbols for the universe",
    )
    num_portfolios: Optional[int] = Field(
        default=5000,
        ge=100,
        le=50000,
        description="Number of random portfolios to simulate",
    )
    risk_free_rate: Optional[float] = Field(
        default=0.02,
        ge=0,
        le=0.1,
        description="Annual risk-free rate",
    )
    lookback_days: Optional[int] = Field(
        default=252,
        ge=30,
        le=1000,
        description="Historical lookback in trading days",
    )


class RiskAnalysisRequest(BaseModel):
    """Request body for VaR / CVaR risk analysis."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "symbols": ["AAPL", "MSFT", "GOOGL"],
                "confidence_level": 0.95,
                "method": "historical",
                "portfolio_value": 100000,
            }
        }
    )

    portfolio_id: Optional[str] = Field(
        None,
        description="UUID of existing portfolio (alternative to symbols)",
    )
    symbols: Optional[List[str]] = Field(
        None,
        description="Ticker symbols (alternative to portfolio_id)",
    )
    confidence_level: Optional[float] = Field(
        default=0.95,
        ge=0.9,
        le=0.999,
        description="VaR confidence level (0.90, 0.95, 0.99)",
    )
    method: Optional[str] = Field(
        default="historical",
        pattern=r"^(historical|parametric|monte_carlo)$",
        description="VaR calculation method",
    )
    portfolio_value: Optional[float] = Field(
        default=100000,
        gt=0,
        description="Current portfolio value for dollar VaR",
    )
    lookback_days: Optional[int] = Field(
        default=252,
        ge=30,
        le=1000,
        description="Historical lookback in trading days",
    )


class MonteCarloRequest(BaseModel):
    """Request body for Monte Carlo simulation."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "symbols": ["AAPL", "MSFT", "GOOGL"],
                "num_simulations": 1000,
                "time_horizon": 252,
                "initial_value": 100000,
            }
        }
    )

    symbols: List[str] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Ticker symbols to include",
    )
    weights: Optional[List[float]] = Field(
        None,
        description="Portfolio weights (equal-weight if omitted)",
    )
    num_simulations: Optional[int] = Field(
        default=1000,
        ge=100,
        le=100000,
        description="Number of simulation paths",
    )
    time_horizon: Optional[int] = Field(
        default=252,
        ge=1,
        le=2520,
        description="Number of trading days to simulate",
    )
    initial_value: Optional[float] = Field(
        default=100000,
        gt=0,
        description="Starting portfolio value",
    )
    lookback_days: Optional[int] = Field(
        default=252,
        ge=30,
        le=1000,
        description="Historical lookback in trading days for parameter estimation",
    )


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class OptimizedPortfolioResponse(BaseModel):
    """Optimized portfolio weights and expected performance."""

    weights: Dict[str, float]
    expected_return: float
    expected_volatility: float
    sharpe_ratio: float
    method: str


class EfficientFrontierPoint(BaseModel):
    """A single point on the efficient frontier."""

    return_: float = Field(alias="return")
    volatility: float
    sharpe_ratio: float
    weights: Dict[str, float]

    model_config = ConfigDict(populate_by_name=True)


class EfficientFrontierResponse(BaseModel):
    """Efficient frontier with key portfolios highlighted."""

    frontier: List[EfficientFrontierPoint]
    min_variance: EfficientFrontierPoint
    max_sharpe: EfficientFrontierPoint
    symbols: List[str]
    risk_free_rate: float


class RiskMetricsResponse(BaseModel):
    """Comprehensive risk metrics for a portfolio."""

    var_value: float
    var_percent: float
    cvar_value: float
    cvar_percent: float
    confidence_level: float
    method: str
    portfolio_value: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    volatility: float


class MonteCarloResponse(BaseModel):
    """Monte Carlo simulation results."""

    mean_final_value: float
    median_final_value: float
    p5_final_value: float
    p95_final_value: float
    probability_of_loss: float
    max_value: float
    min_value: float
    simulations_run: int
    percentiles: Dict[str, float]


class PortfolioMetricsResponse(BaseModel):
    """Comprehensive portfolio performance metrics."""

    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    calmar_ratio: float
    win_rate: float
    average_return: float
    annualized_return: float
    volatility: float
    annualized_volatility: float
    skewness: float
    kurtosis: float
    total_return: float
