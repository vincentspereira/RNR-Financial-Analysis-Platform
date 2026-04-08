"""
Stock screener schemas for request/response models.
"""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ScreenerFilter(BaseModel):
    """Filter criteria for stock screening."""
    market_cap_min: Optional[float] = None
    market_cap_max: Optional[float] = None
    sector: Optional[List[str]] = None
    industry: Optional[str] = None
    exchange: Optional[List[str]] = None
    pe_ratio_min: Optional[float] = None
    pe_ratio_max: Optional[float] = None
    pb_ratio_min: Optional[float] = None
    pb_ratio_max: Optional[float] = None
    ps_ratio_min: Optional[float] = None
    ps_ratio_max: Optional[float] = None
    dividend_yield_min: Optional[float] = None
    dividend_yield_max: Optional[float] = None
    price_change_1d_min: Optional[float] = None
    price_change_1d_max: Optional[float] = None
    price_change_1y_min: Optional[float] = None
    price_change_1y_max: Optional[float] = None
    revenue_growth_min: Optional[float] = None
    earnings_growth_min: Optional[float] = None
    debt_to_equity_max: Optional[float] = None
    current_ratio_min: Optional[float] = None
    roe_min: Optional[float] = None
    rsi_14_min: Optional[float] = None
    rsi_14_max: Optional[float] = None
    sma_50_above: Optional[bool] = None
    sma_200_above: Optional[bool] = None
    sort_by: str = "market_cap"
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")
    limit: int = Field(default=50, ge=1, le=200)


class ScreenerResult(BaseModel):
    """Individual stock result from screener."""
    symbol: str
    company_name: str
    sector: str
    exchange: str
    market_cap: float
    price: float
    pe_ratio: Optional[float] = None
    dividend_yield: Optional[float] = None
    price_change_1d: Optional[float] = None
    price_change_1y: Optional[float] = None
    volume: Optional[int] = None
    score: float


class ScreenerResponse(BaseModel):
    """Response model for screener results."""
    total_results: int
    results: List[ScreenerResult]
    preset_name: Optional[str] = None


class PresetScreener(BaseModel):
    """Predefined screener template."""
    name: str
    description: str
    filters: ScreenerFilter


class SaveScreenerRequest(BaseModel):
    """Request to save a custom screener."""
    name: str
    filters: ScreenerFilter
