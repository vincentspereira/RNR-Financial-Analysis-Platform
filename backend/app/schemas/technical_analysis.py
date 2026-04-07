"""
Pydantic v2 schemas for Technical Analysis endpoints.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class TechnicalAnalysisRequest(BaseModel):
    """Request schema for calculating specific technical indicators."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "symbol": "AAPL",
                "indicators": ["sma", "ema", "rsi", "macd", "bollinger_bands"],
                "period": 252,
                "interval": "daily",
            }
        }
    )

    symbol: str = Field(
        ..., max_length=10, description="Stock ticker symbol"
    )
    indicators: List[str] = Field(
        ..., min_length=1, max_length=50, description="List of indicator names to calculate"
    )
    period: Optional[int] = Field(
        default=252, ge=5, le=1000, description="Lookback period in trading days"
    )
    interval: Optional[str] = Field(
        default="daily",
        pattern=r"^(daily|weekly|monthly)$",
        description="Data interval",
    )


class IndicatorResult(BaseModel):
    """Result for a single technical indicator."""

    name: str = Field(..., description="Indicator name")
    values: Dict[str, Any] = Field(
        ..., description="Computed indicator values (key -> list or scalar)"
    )
    latest_value: Optional[float] = Field(
        None, description="Most recent non-null value of the indicator"
    )
    signal: Optional[str] = Field(
        None, description="Signal: bullish, bearish, or neutral"
    )


class TechnicalAnalysisResponse(BaseModel):
    """Response schema for technical indicator calculations."""

    symbol: str
    indicators: List[IndicatorResult]
    data_points: int = Field(..., description="Number of data points used")
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    calculated_at: datetime


class TechnicalSummaryRequest(BaseModel):
    """Request schema for technical analysis summary."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "symbol": "AAPL",
                "period": 252,
            }
        }
    )

    symbol: str = Field(..., max_length=10, description="Stock ticker symbol")
    period: Optional[int] = Field(
        default=252, ge=5, le=1000, description="Lookback period in trading days"
    )


class TechnicalSummaryResponse(BaseModel):
    """Response schema with consolidated buy/sell signal."""

    symbol: str
    overall_signal: str = Field(
        ...,
        description="Overall signal: strong_buy, buy, neutral, sell, strong_sell",
    )
    signal_strength: float = Field(
        ..., ge=0, le=100, description="Signal strength from 0 to 100"
    )
    trend: str = Field(
        ..., description="Trend assessment: bullish, bearish, sideways"
    )
    momentum: str = Field(
        ..., description="Momentum assessment: bullish, bearish, neutral"
    )
    volatility: str = Field(
        ..., description="Volatility assessment: low, medium, high"
    )
    key_levels: Dict[str, Optional[float]] = Field(
        ...,
        description="Key price levels: support, resistance, pivot, etc.",
    )
    indicator_signals: List[Dict[str, str]] = Field(
        ...,
        description="Per-indicator signals [{name, signal, description}]",
    )


class BatchTechnicalAnalysisRequest(BaseModel):
    """Request schema for batch technical analysis across multiple symbols."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "symbols": ["AAPL", "MSFT", "GOOGL"],
                "indicators": ["rsi", "macd", "bollinger_bands"],
                "period": 252,
            }
        }
    )

    symbols: List[str] = Field(
        ..., min_length=1, max_length=10, description="List of stock ticker symbols (max 10)"
    )
    indicators: List[str] = Field(
        ..., min_length=1, max_length=50, description="List of indicator names to calculate"
    )
    period: Optional[int] = Field(
        default=252, ge=5, le=1000, description="Lookback period in trading days"
    )
    interval: Optional[str] = Field(
        default="daily",
        pattern=r"^(daily|weekly|monthly)$",
        description="Data interval",
    )


class BatchTechnicalAnalysisResponse(BaseModel):
    """Response schema for batch technical analysis."""

    results: List[TechnicalAnalysisResponse]
    successful: int = Field(..., description="Number of successful calculations")
    failed: int = Field(..., description="Number of failed calculations")
    errors: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Errors encountered per symbol",
    )


class IndicatorInfo(BaseModel):
    """Descriptive information about an available indicator."""

    name: str
    category: str
    description: str


class AvailableIndicatorsResponse(BaseModel):
    """Response listing all available technical indicators."""

    total: int
    categories: Dict[str, List[IndicatorInfo]]
