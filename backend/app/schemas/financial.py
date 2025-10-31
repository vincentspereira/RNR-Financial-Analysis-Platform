"""
Pydantic schemas for financial calculation endpoints
"""
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class FinancialRatiosRequest(BaseModel):
    """Request schema for financial ratios calculation"""
    company_id: UUID = Field(..., description="Company UUID")
    period_type: str = Field(..., description="Period type: 'quarterly' or 'annual'")
    fiscal_year: int = Field(..., description="Fiscal year")
    fiscal_quarter: Optional[int] = Field(None, description="Fiscal quarter (1-4, required for quarterly)")


class FinancialRatiosResponse(BaseModel):
    """Response schema for financial ratios"""
    model_config = ConfigDict(from_attributes=True)
    
    company_id: UUID
    period_type: str
    fiscal_year: int
    fiscal_quarter: Optional[int]
    calculation_date: date
    ratios: Dict[str, Optional[Decimal]]


class ValuationRequest(BaseModel):
    """Request schema for company valuation"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "company_id": "123e4567-e89b-12d3-a456-426614174000",
                "assumptions": {
                    "free_cash_flows": [1000000, 1100000, 1210000, 1331000, 1464100],
                    "terminal_growth_rate": 0.03,
                    "discount_rate": 0.10,
                    "shares_outstanding": 1000000,
                    "dividend_growth_rate": 0.05,
                    "required_return": 0.12,
                    "earnings_growth_rate": 15.0
                }
            }
        }
    )
    
    company_id: UUID = Field(..., description="Company UUID")
    assumptions: Dict[str, float] = Field(..., description="Valuation assumptions")


class ValuationResponse(BaseModel):
    """Response schema for company valuation"""
    company_id: UUID
    company_name: str
    company_symbol: str
    valuation_date: date
    fair_value_estimates: Dict[str, Optional[Decimal]]
    quality_scores: Dict[str, Optional[Decimal]]
    assumptions_used: Dict[str, float]


class PeerComparisonRequest(BaseModel):
    """Request schema for peer comparison"""
    company_id: UUID = Field(..., description="Target company UUID")
    peer_company_ids: List[UUID] = Field(..., description="List of peer company UUIDs")
    period_type: str = Field(..., description="Period type: 'quarterly' or 'annual'")
    fiscal_year: int = Field(..., description="Fiscal year")


class PeerStatistics(BaseModel):
    """Peer statistics for a single ratio"""
    count: int
    average: float
    median: float
    min: float
    max: float
    percentile_25: float
    percentile_75: float


class PeerComparisonResponse(BaseModel):
    """Response schema for peer comparison"""
    target_company: FinancialRatiosResponse
    peer_companies: List[FinancialRatiosResponse]
    peer_statistics: Dict[str, PeerStatistics]


class CompanyFinancialDataResponse(BaseModel):
    """Response schema for company financial data"""
    company_id: UUID
    period_type: str
    fiscal_year: int
    fiscal_quarter: Optional[int]
    financial_data: Dict[str, float]
    market_data: Optional[Dict[str, float]]


class RatioCalculationResponse(BaseModel):
    """Response schema for individual ratio calculations"""
    ratio_name: str
    ratio_value: Optional[Decimal]
    ratio_category: str
    description: str
    interpretation: Optional[str]


class FinancialHealthScore(BaseModel):
    """Financial health score response"""
    company_id: UUID
    company_symbol: str
    overall_score: int = Field(..., ge=0, le=100, description="Overall financial health score (0-100)")
    liquidity_score: int = Field(..., ge=0, le=100)
    profitability_score: int = Field(..., ge=0, le=100)
    leverage_score: int = Field(..., ge=0, le=100)
    efficiency_score: int = Field(..., ge=0, le=100)
    valuation_score: int = Field(..., ge=0, le=100)
    quality_indicators: Dict[str, Optional[Decimal]]
    score_date: date


class BatchRatiosRequest(BaseModel):
    """Request schema for batch ratio calculations"""
    company_ids: List[UUID] = Field(..., description="List of company UUIDs")
    period_type: str = Field(..., description="Period type: 'quarterly' or 'annual'")
    fiscal_year: int = Field(..., description="Fiscal year")
    fiscal_quarter: Optional[int] = Field(None, description="Fiscal quarter (for quarterly data)")


class BatchRatiosResponse(BaseModel):
    """Response schema for batch ratio calculations"""
    successful_calculations: List[FinancialRatiosResponse]
    failed_calculations: List[Dict[str, str]]  # company_id and error message
    total_requested: int
    total_successful: int
    total_failed: int