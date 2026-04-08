"""
Risk Management API endpoints.

Provides endpoints for portfolio risk analysis, stress testing,
risk scoring, and risk factor breakdown.
"""
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.logging import get_logger
from app.schemas.risk import (
    RiskAnalysisRequest,
    RiskAnalysisResponse,
    RiskFactorsResponse,
    RiskScoreResponse,
    StressTestRequest,
)
from app.services.risk.risk_engine import risk_engine
from app.services.auth.auth_service import auth_service

router = APIRouter(prefix="/risk", tags=["risk"])
logger = get_logger("api.risk")


async def get_current_user_from_token(
    authorization: Annotated[Optional[str], Header()] = None,
    db: Annotated[AsyncSession, Depends(get_async_session)] = None,
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization header format")
    access_token = authorization.split(" ")[1]
    user = await auth_service.verify_session(access_token, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account is disabled")
    return user


@router.post("/analyze", response_model=RiskAnalysisResponse)
async def analyze_risk(
    request: RiskAnalysisRequest,
    current_user=Depends(get_current_user_from_token),
):
    """Run full risk analysis on a portfolio."""
    try:
        result = await risk_engine.analyze_portfolio(request)
        return result
    except Exception as e:
        logger.error(f"Risk analysis failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Risk analysis failed. Please try again later.")


@router.post("/stress-test")
async def run_stress_test(
    request: StressTestRequest,
    current_user=Depends(get_current_user_from_token),
):
    """Run stress test scenarios on a portfolio."""
    try:
        from app.services.risk.risk_engine import MOCK_PORTFOLIO, STRESS_SCENARIOS
        positions = MOCK_PORTFOLIO["positions"]
        total_value = MOCK_PORTFOLIO["total_value"]

        scenarios = request.scenarios or list(STRESS_SCENARIOS.keys())
        results = []
        for scenario_name in scenarios:
            result = risk_engine.run_stress_test(positions, scenario_name, total_value)
            if result:
                results.append(result)

        return {"portfolio_id": request.portfolio_id, "stress_tests": results}
    except Exception as e:
        logger.error(f"Stress test failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Stress test failed. Please try again later.")


@router.get("/score/{portfolio_id}", response_model=RiskScoreResponse)
async def get_risk_score(
    portfolio_id: str,
    current_user=Depends(get_current_user_from_token),
):
    """Get current risk score for a portfolio."""
    from app.services.risk.risk_engine import MOCK_PORTFOLIO
    risk_score = risk_engine.calculate_risk_score(MOCK_PORTFOLIO)
    return {"portfolio_id": portfolio_id, "risk_score": risk_score}


@router.get("/factors/{portfolio_id}", response_model=RiskFactorsResponse)
async def get_risk_factors(
    portfolio_id: str,
    current_user=Depends(get_current_user_from_token),
):
    """Get risk factor breakdown for a portfolio."""
    import numpy as np
    returns = risk_engine._get_returns(portfolio_id)
    risk_factors = {
        "sharpe_ratio": round(risk_engine.calculate_sharpe_ratio(returns), 3),
        "sortino_ratio": round(risk_engine.calculate_sortino_ratio(returns), 3),
        "annualized_volatility": round(float(np.std(returns, ddof=1) * np.sqrt(252) * 100), 2),
        "annualized_return": round(float(np.mean(returns) * 252 * 100), 2),
    }
    return {"portfolio_id": portfolio_id, "risk_factors": risk_factors}
