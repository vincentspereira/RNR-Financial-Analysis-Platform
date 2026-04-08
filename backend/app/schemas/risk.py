"""
Risk analysis schemas for request/response models.
"""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class RiskAnalysisRequest(BaseModel):
    """Request model for portfolio risk analysis."""
    portfolio_id: str
    method: str = Field(default="historical", pattern="^(historical|parametric|monte_carlo)$")
    confidence_level: float = Field(default=0.95, ge=0.9, le=0.99)
    time_horizon_days: int = Field(default=1, ge=1, le=252)
    include_stress_tests: bool = True


class StressTestRequest(BaseModel):
    """Request model for stress testing."""
    portfolio_id: str
    scenarios: Optional[List[str]] = None


class VaRResult(BaseModel):
    method: str
    confidence_level: float
    time_horizon_days: int
    var_amount: float
    var_percentage: float
    cvar_amount: float
    cvar_percentage: float


class DrawdownResult(BaseModel):
    max_drawdown: float
    max_drawdown_duration_days: int
    current_drawdown: float
    recovery_time_days: Optional[int] = None


class RiskScore(BaseModel):
    overall_score: float
    volatility_risk: float
    concentration_risk: float
    liquidity_risk: float
    market_risk: float
    rating: str


class StressTestResult(BaseModel):
    scenario: str
    description: str
    portfolio_impact_percentage: float
    portfolio_impact_amount: float
    worst_position: str
    worst_position_impact: float


class RiskAnalysisResponse(BaseModel):
    portfolio_id: str
    timestamp: str
    var_analysis: VaRResult
    drawdown: DrawdownResult
    risk_score: RiskScore
    stress_tests: List[StressTestResult]
    risk_factors: Dict[str, float]


class RiskScoreResponse(BaseModel):
    portfolio_id: str
    risk_score: RiskScore


class RiskFactorsResponse(BaseModel):
    portfolio_id: str
    risk_factors: Dict[str, float]
