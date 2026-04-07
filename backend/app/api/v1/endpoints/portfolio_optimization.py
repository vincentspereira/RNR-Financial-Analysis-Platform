"""
Portfolio Optimization API endpoints.

Provides portfolio weight optimization, efficient frontier calculation,
risk analysis (VaR/CVaR), Monte Carlo simulation, and portfolio metrics.
"""
from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.logging import get_logger
from app.models.company import Company, MarketData
from app.models.portfolio import Portfolio, PortfolioHolding
from app.schemas.portfolio_optimization import (
    EfficientFrontierRequest,
    EfficientFrontierResponse,
    EfficientFrontierPoint,
    MonteCarloRequest,
    MonteCarloResponse,
    OptimizedPortfolioResponse,
    PortfolioMetricsResponse,
    PortfolioOptimizationRequest,
    RiskAnalysisRequest,
    RiskMetricsResponse,
)
from app.services.analysis.portfolio_optimization import portfolio_optimizer
from app.services.auth.auth_service import auth_service

router = APIRouter(
    prefix="/analysis/optimization",
    tags=["portfolio-optimization"],
)
logger = get_logger("api.portfolio_optimization")


# ---------------------------------------------------------------------------
# Auth helper (same pattern as data.py)
# ---------------------------------------------------------------------------


async def get_current_user_from_token(
    authorization: Annotated[Optional[str], Header()] = None,
    db: Annotated[AsyncSession, Depends(get_async_session)] = None,
):
    """Validate Bearer token and return the authenticated user."""
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


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------


async def _fetch_returns_for_symbols(
    symbols: List[str],
    lookback_days: int,
    db: AsyncSession,
):
    """
    Build a DataFrame of daily percentage returns from MarketData for the
    given symbols over the requested lookback window.

    Raises HTTPException 404 if any symbol has no data.
    """
    import pandas as pd
    from datetime import date, timedelta

    from sqlalchemy import func as sa_func

    cutoff = date.today() - timedelta(days=int(lookback_days * 1.5))

    # Resolve symbols to company ids
    company_stmt = select(Company.id, Company.symbol).where(
        Company.symbol.in_([s.upper() for s in symbols])
    )
    company_result = await db.execute(company_stmt)
    company_rows = company_result.all()

    found_symbols = {row.symbol for row in company_rows}
    missing = set(s.upper() for s in symbols) - found_symbols
    if missing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No company records found for symbols: {', '.join(sorted(missing))}",
        )

    symbol_to_id = {row.symbol: row.id for row in company_rows}
    company_ids = list(symbol_to_id.values())

    # Fetch market data
    md_stmt = (
        select(
            MarketData.company_id,
            MarketData.price_date,
            MarketData.adjusted_close.label("close"),
        )
        .where(
            and_(
                MarketData.company_id.in_(company_ids),
                MarketData.price_date >= cutoff,
            )
        )
        .order_by(MarketData.price_date)
    )
    md_result = await db.execute(md_stmt)
    rows = md_result.all()

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No market data found for the requested symbols.",
        )

    # Build price DataFrame
    id_to_symbol = {v: k for k, v in symbol_to_id.items()}
    records = [
        {"date": row.price_date, "symbol": id_to_symbol[row.company_id], "close": float(row.close)}
        for row in rows
        if row.close is not None
    ]

    if not records:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="All market data rows had null adjusted_close values.",
        )

    price_df = pd.DataFrame(records)
    price_df = price_df.pivot(index="date", columns="symbol", values="close").sort_index()

    returns_df = price_df.pct_change().dropna()

    if returns_df.empty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Insufficient price data to compute returns.",
        )

    # Trim to requested lookback
    if len(returns_df) > lookback_days:
        returns_df = returns_df.iloc[-lookback_days:]

    return returns_df


async def _symbols_from_portfolio(
    portfolio_id: str,
    db: AsyncSession,
) -> List[str]:
    """Return the list of symbols held in a portfolio."""
    pid = portfolio_id if isinstance(portfolio_id, UUID) else UUID(portfolio_id)
    stmt = select(PortfolioHolding.symbol).where(
        PortfolioHolding.portfolio_id == pid
    )
    result = await db.execute(stmt)
    symbols = [row.symbol for row in result.all()]
    if not symbols:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Portfolio {portfolio_id} has no holdings.",
        )
    return symbols


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/optimize",
    response_model=OptimizedPortfolioResponse,
    summary="Optimize portfolio weights",
    description="Run mean-variance optimization to find optimal asset weights.",
    responses={
        200: {"description": "Portfolio optimized successfully"},
        400: {"description": "Invalid request parameters"},
        404: {"description": "Symbols or portfolio not found"},
        500: {"description": "Internal server error"},
    },
)
async def optimize_portfolio(
    request: PortfolioOptimizationRequest,
    db: Annotated[AsyncSession, Depends(get_async_session)],
    current_user=Depends(get_current_user_from_token),
):
    """
    Optimize portfolio allocation using the specified method.

    Supports: max_sharpe, min_variance, target_return, equal_weight, risk_parity.
    Either *portfolio_id* or *symbols* must be provided.
    """
    try:
        # Resolve symbols
        if request.portfolio_id and not request.symbols:
            symbols = await _symbols_from_portfolio(request.portfolio_id, db)
        elif request.symbols:
            symbols = [s.upper() for s in request.symbols]
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either portfolio_id or symbols must be provided.",
            )

        if len(symbols) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least 2 symbols are required for optimization.",
            )

        returns_df = await _fetch_returns_for_symbols(
            symbols, request.lookback_days or 252, db
        )

        result = portfolio_optimizer.optimize_portfolio(
            returns_df=returns_df,
            target_return=request.target_return,
            risk_tolerance=request.risk_tolerance,
            constraints=request.constraints,
            method=request.optimization_method,
        )

        return OptimizedPortfolioResponse(
            weights=result["weights"],
            expected_return=result["expected_return"],
            expected_volatility=result["expected_volatility"],
            sharpe_ratio=result["sharpe_ratio"],
            method=result["method"],
        )

    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error("Portfolio optimization error: %s", str(exc), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Optimization failed. Please try again later.",
        )


@router.post(
    "/efficient-frontier",
    response_model=EfficientFrontierResponse,
    summary="Calculate efficient frontier",
    description="Generate the efficient frontier via Monte Carlo simulation.",
    responses={
        200: {"description": "Efficient frontier calculated successfully"},
        400: {"description": "Invalid request parameters"},
        404: {"description": "Insufficient data for symbols"},
        500: {"description": "Internal server error"},
    },
)
async def calculate_efficient_frontier(
    request: EfficientFrontierRequest,
    db: Annotated[AsyncSession, Depends(get_async_session)],
    current_user=Depends(get_current_user_from_token),
):
    """
    Generate the efficient frontier for a set of assets.

    Returns the full frontier, the minimum variance portfolio,
    and the maximum Sharpe ratio portfolio.
    """
    try:
        symbols = [s.upper() for s in request.symbols]
        returns_df = await _fetch_returns_for_symbols(
            symbols, request.lookback_days or 252, db
        )

        result = portfolio_optimizer.calculate_efficient_frontier(
            returns_df=returns_df,
            num_portfolios=request.num_portfolios or 5000,
            risk_free_rate=request.risk_free_rate or 0.02,
        )

        def _to_point(p: dict) -> EfficientFrontierPoint:
            return EfficientFrontierPoint(
                **{"return": p["return"]},
                volatility=p["volatility"],
                sharpe_ratio=p["sharpe_ratio"],
                weights=p["weights"],
            )

        return EfficientFrontierResponse(
            frontier=[_to_point(p) for p in result["frontier_points"]],
            min_variance=_to_point(result["min_variance_portfolio"]),
            max_sharpe=_to_point(result["max_sharpe_portfolio"]),
            symbols=symbols,
            risk_free_rate=request.risk_free_rate or 0.02,
        )

    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error("Efficient frontier error: %s", str(exc), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Efficient frontier calculation failed. Please try again later.",
        )


@router.post(
    "/risk-analysis",
    response_model=RiskMetricsResponse,
    summary="Calculate risk metrics (VaR, CVaR, etc.)",
    description="Compute Value at Risk, Conditional VaR, and other risk metrics.",
    responses={
        200: {"description": "Risk analysis completed successfully"},
        400: {"description": "Invalid request parameters"},
        404: {"description": "Insufficient data"},
        500: {"description": "Internal server error"},
    },
)
async def risk_analysis(
    request: RiskAnalysisRequest,
    db: Annotated[AsyncSession, Depends(get_async_session)],
    current_user=Depends(get_current_user_from_token),
):
    """
    Calculate VaR, CVaR, and comprehensive risk metrics for a portfolio.

    Supports historical, parametric, and Monte Carlo VaR methods.
    """
    try:
        # Resolve symbols
        if request.portfolio_id and not request.symbols:
            symbols = await _symbols_from_portfolio(request.portfolio_id, db)
        elif request.symbols:
            symbols = [s.upper() for s in request.symbols]
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either portfolio_id or symbols must be provided.",
            )

        returns_df = await _fetch_returns_for_symbols(
            symbols, request.lookback_days or 252, db
        )

        # Equal-weighted portfolio returns
        portfolio_returns = returns_df.mean(axis=1)

        confidence = request.confidence_level or 0.95
        method = request.method or "historical"
        portfolio_value = request.portfolio_value or 100000.0
        risk_free_rate = 0.02

        var_result = portfolio_optimizer.calculate_var(
            returns=portfolio_returns,
            confidence_level=confidence,
            method=method,
            portfolio_value=portfolio_value,
        )

        cvar_result = portfolio_optimizer.calculate_cvar(
            returns=portfolio_returns,
            confidence_level=confidence,
            method=method,
        )

        sharpe = portfolio_optimizer.calculate_sharpe_ratio(
            portfolio_returns, risk_free_rate
        )
        sortino = portfolio_optimizer.calculate_sortino_ratio(
            portfolio_returns, risk_free_rate
        )
        metrics = portfolio_optimizer.calculate_portfolio_metrics(
            portfolio_returns, risk_free_rate
        )

        return RiskMetricsResponse(
            var_value=var_result["var_value"],
            var_percent=var_result["var_percent"],
            cvar_value=cvar_result["cvar_value"],
            cvar_percent=cvar_result["cvar_percent"],
            confidence_level=confidence,
            method=method,
            portfolio_value=portfolio_value,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            max_drawdown=metrics["max_drawdown"],
            volatility=metrics["annualized_volatility"],
        )

    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error("Risk analysis error: %s", str(exc), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Risk analysis failed. Please try again later.",
        )


@router.post(
    "/monte-carlo",
    response_model=MonteCarloResponse,
    summary="Run Monte Carlo simulation",
    description="Simulate portfolio value paths and return distribution statistics.",
    responses={
        200: {"description": "Monte Carlo simulation completed successfully"},
        400: {"description": "Invalid request parameters"},
        404: {"description": "Insufficient data for symbols"},
        500: {"description": "Internal server error"},
    },
)
async def monte_carlo_simulation(
    request: MonteCarloRequest,
    db: Annotated[AsyncSession, Depends(get_async_session)],
    current_user=Depends(get_current_user_from_token),
):
    """
    Run Monte Carlo simulation for portfolio value projection.

    Simulates correlated asset paths based on historical return statistics
    and returns the distribution of final portfolio values.
    """
    try:
        symbols = [s.upper() for s in request.symbols]
        returns_df = await _fetch_returns_for_symbols(
            symbols, request.lookback_days or 252, db
        )

        result = portfolio_optimizer.monte_carlo_simulation(
            returns_df=returns_df,
            weights=request.weights,
            num_simulations=request.num_simulations or 1000,
            time_horizon=request.time_horizon or 252,
            initial_value=request.initial_value or 100000.0,
        )

        return MonteCarloResponse(
            mean_final_value=result["mean_final_value"],
            median_final_value=result["median_final_value"],
            p5_final_value=result["p5_final_value"],
            p95_final_value=result["p95_final_value"],
            probability_of_loss=result["probability_of_loss"],
            max_value=result["max_value"],
            min_value=result["min_value"],
            simulations_run=result["simulations_run"],
            percentiles=result["percentiles"],
        )

    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error("Monte Carlo simulation error: %s", str(exc), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Monte Carlo simulation failed. Please try again later.",
        )


@router.get(
    "/portfolio-metrics/{portfolio_id}",
    response_model=PortfolioMetricsResponse,
    summary="Get metrics for an existing portfolio",
    description="Calculate comprehensive performance metrics for a user's portfolio.",
    responses={
        200: {"description": "Metrics calculated successfully"},
        404: {"description": "Portfolio not found or insufficient data"},
        500: {"description": "Internal server error"},
    },
)
async def get_portfolio_metrics(
    portfolio_id: str,
    db: Annotated[AsyncSession, Depends(get_async_session)],
    current_user=Depends(get_current_user_from_token),
    lookback_days: int = 252,
):
    """
    Calculate comprehensive performance metrics for an existing portfolio.

    Metrics include Sharpe ratio, Sortino ratio, max drawdown, Calmar ratio,
    win rate, annualized return and volatility, skewness, and kurtosis.
    """
    try:
        symbols = await _symbols_from_portfolio(portfolio_id, db)
        returns_df = await _fetch_returns_for_symbols(symbols, lookback_days, db)

        # Fetch portfolio holdings to compute weighted returns
        pid = portfolio_id if isinstance(portfolio_id, UUID) else UUID(portfolio_id)
        holdings_stmt = select(PortfolioHolding).where(
            PortfolioHolding.portfolio_id == pid
        )
        holdings_result = await db.execute(holdings_stmt)
        holdings = list(holdings_result.all())

        # Build weights from current market values (or share counts as fallback)
        weights_dict: dict = {}
        for h in holdings:
            val = (float(h.shares) * float(h.current_price)) if h.current_price else float(h.shares)
            weights_dict[h.symbol] = val
        total_weight = sum(weights_dict.values())
        if total_weight > 0:
            weights = [weights_dict.get(s, 0) / total_weight for s in returns_df.columns]
        else:
            weights = None

        # Weighted portfolio returns
        if weights:
            w_arr = [weights[i] for i, _ in enumerate(returns_df.columns)]
            portfolio_returns = returns_df.dot(w_arr)
        else:
            portfolio_returns = returns_df.mean(axis=1)

        metrics = portfolio_optimizer.calculate_portfolio_metrics(
            portfolio_returns, risk_free_rate=0.02
        )

        return PortfolioMetricsResponse(**metrics)

    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error("Portfolio metrics error: %s", str(exc), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Portfolio metrics calculation failed. Please try again later.",
        )
