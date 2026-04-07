"""
Backtesting API endpoints.

Provides endpoints for running strategy backtests, comparing strategies,
and listing available strategy types.
"""
from datetime import date, timedelta
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.logging import get_logger
from app.models.company import Company, MarketData
from app.schemas.backtesting import (
    BacktestCompareRequest,
    BacktestCompareResponse,
    BacktestMetricsResponse,
    BacktestRequest,
    BacktestResponse,
    StrategiesListResponse,
    StrategyInfo,
    TradeRecordResponse,
)
from app.services.backtesting.engine import (
    BacktestConfig,
    BacktestEngine,
    SlippageConfig,
    StrategyConfig as EngineStrategyConfig,
    TransactionCostConfig,
)
from app.services.auth.auth_service import auth_service

router = APIRouter(prefix="/backtesting", tags=["backtesting"])
logger = get_logger("api.backtesting")

backtest_engine = BacktestEngine()


# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Data helper
# ---------------------------------------------------------------------------


async def _fetch_ohlcv(
    symbol: str,
    lookback_days: int,
    db: AsyncSession,
):
    """Fetch OHLCV DataFrame for a symbol."""
    import pandas as pd

    company_stmt = select(Company.id).where(Company.symbol == symbol.upper())
    result = await db.execute(company_stmt)
    company = result.first()
    if not company:
        raise HTTPException(status_code=404, detail=f"Company not found: {symbol}")

    cutoff = date.today() - timedelta(days=int(lookback_days * 1.5))
    md_stmt = (
        select(
            MarketData.price_date,
            MarketData.open_price,
            MarketData.high_price,
            MarketData.low_price,
            MarketData.close_price,
            MarketData.volume,
        )
        .where(and_(MarketData.company_id == company.id, MarketData.price_date >= cutoff))
        .order_by(MarketData.price_date)
    )
    md_result = await db.execute(md_stmt)
    rows = md_result.all()

    if not rows:
        raise HTTPException(status_code=404, detail=f"No market data for: {symbol}")

    df = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"])
    df = df.dropna().sort_values("date").tail(lookback_days)

    if len(df) < 20:
        raise HTTPException(status_code=400, detail=f"Insufficient data for {symbol} ({len(df)} rows)")

    df = df.set_index("date")
    return df


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/run",
    response_model=BacktestResponse,
    summary="Run a backtest",
    description="Run a strategy backtest against historical data.",
)
async def run_backtest(
    request: BacktestRequest,
    db: Annotated[AsyncSession, Depends(get_async_session)],
    current_user=Depends(get_current_user_from_token),
):
    """Run a single strategy backtest."""
    try:
        price_data = {}
        for symbol in request.symbols:
            price_data[symbol.upper()] = await _fetch_ohlcv(
                symbol, request.lookback_days or 504, db
            )

        # Fetch benchmark
        benchmark_data = None
        if request.benchmark_symbol:
            try:
                benchmark_data = await _fetch_ohlcv(
                    request.benchmark_symbol, request.lookback_days or 504, db
                )
            except HTTPException:
                benchmark_data = None

        # Build config
        slippage = SlippageConfig()
        if request.slippage:
            slippage = SlippageConfig(model=request.slippage.model, value=request.slippage.value)

        tc = TransactionCostConfig()
        if request.transaction_costs:
            tc = TransactionCostConfig(model=request.transaction_costs.model, value=request.transaction_costs.value)

        config = BacktestConfig(
            symbols=[s.upper() for s in request.symbols],
            strategy=EngineStrategyConfig(
                strategy_type=request.strategy.strategy_type,
                parameters=request.strategy.parameters,
            ),
            initial_capital=request.initial_capital,
            lookback_days=request.lookback_days or 504,
            slippage=slippage,
            transaction_costs=tc,
            benchmark_symbol=request.benchmark_symbol,
            position_size_pct=request.position_size_pct,
        )

        result = await backtest_engine.run_backtest(price_data, config, benchmark_data)

        return BacktestResponse(
            status=result.status,
            strategy=result.strategy,
            symbols=result.symbols,
            initial_capital=result.initial_capital,
            final_value=result.final_value,
            metrics=BacktestMetricsResponse(
                total_return=result.metrics.total_return,
                annualized_return=result.metrics.annualized_return,
                cagr=result.metrics.cagr,
                max_drawdown=result.metrics.max_drawdown,
                max_drawdown_duration_days=result.metrics.max_drawdown_duration_days,
                sharpe_ratio=result.metrics.sharpe_ratio,
                sortino_ratio=result.metrics.sortino_ratio,
                calmar_ratio=result.metrics.calmar_ratio,
                win_rate=result.metrics.win_rate,
                profit_factor=result.metrics.profit_factor,
                avg_win=result.metrics.avg_win,
                avg_loss=result.metrics.avg_loss,
                total_trades=result.metrics.total_trades,
                avg_holding_period_days=result.metrics.avg_holding_period_days,
                alpha=result.metrics.alpha,
                beta=result.metrics.beta,
                information_ratio=result.metrics.information_ratio,
            ),
            equity_curve=result.equity_curve,
            trades=[
                TradeRecordResponse(
                    symbol=t.symbol, action=t.action, date=t.date,
                    price=t.price, shares=t.shares, commission=t.commission,
                    slippage_cost=t.slippage_cost, pnl=t.pnl,
                )
                for t in result.trades
            ],
            benchmark_total_return=result.benchmark_total_return,
            run_date=result.run_date,
        )

    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error(f"Backtest error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Backtest failed. Please try again later.")


@router.post(
    "/compare",
    response_model=BacktestCompareResponse,
    summary="Compare strategies",
    description="Compare multiple strategies against the same data.",
)
async def compare_strategies(
    request: BacktestCompareRequest,
    db: Annotated[AsyncSession, Depends(get_async_session)],
    current_user=Depends(get_current_user_from_token),
):
    """Compare multiple strategies side by side."""
    try:
        price_data = {}
        for symbol in request.symbols:
            price_data[symbol.upper()] = await _fetch_ohlcv(
                symbol, request.lookback_days or 504, db
            )

        results = []
        comparison_metrics = {}

        for strat in request.strategies:
            config = BacktestConfig(
                symbols=[s.upper() for s in request.symbols],
                strategy=EngineStrategyConfig(
                    strategy_type=strat.strategy_type,
                    parameters=strat.parameters,
                ),
                initial_capital=request.initial_capital,
                lookback_days=request.lookback_days or 504,
            )

            result = await backtest_engine.run_backtest(price_data, config)

            results.append(BacktestResponse(
                status=result.status,
                strategy=result.strategy,
                symbols=result.symbols,
                initial_capital=result.initial_capital,
                final_value=result.final_value,
                metrics=BacktestMetricsResponse(
                    total_return=result.metrics.total_return,
                    annualized_return=result.metrics.annualized_return,
                    cagr=result.metrics.cagr,
                    max_drawdown=result.metrics.max_drawdown,
                    max_drawdown_duration_days=result.metrics.max_drawdown_duration_days,
                    sharpe_ratio=result.metrics.sharpe_ratio,
                    sortino_ratio=result.metrics.sortino_ratio,
                    calmar_ratio=result.metrics.calmar_ratio,
                    win_rate=result.metrics.win_rate,
                    profit_factor=result.metrics.profit_factor,
                    avg_win=result.metrics.avg_win,
                    avg_loss=result.metrics.avg_loss,
                    total_trades=result.metrics.total_trades,
                    avg_holding_period_days=result.metrics.avg_holding_period_days,
                    alpha=result.metrics.alpha,
                    beta=result.metrics.beta,
                    information_ratio=result.metrics.information_ratio,
                ),
                equity_curve=result.equity_curve,
                trades=[
                    TradeRecordResponse(
                        symbol=t.symbol, action=t.action, date=t.date,
                        price=t.price, shares=t.shares, commission=t.commission,
                        slippage_cost=t.slippage_cost, pnl=t.pnl,
                    )
                    for t in result.trades
                ],
                benchmark_total_return=result.benchmark_total_return,
                run_date=result.run_date,
            ))

            comparison_metrics[strat.strategy_type] = {
                "total_return": result.metrics.total_return,
                "sharpe_ratio": result.metrics.sharpe_ratio,
                "max_drawdown": result.metrics.max_drawdown,
                "win_rate": result.metrics.win_rate,
            }

        return BacktestCompareResponse(
            results=results,
            comparison_metrics=comparison_metrics,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Strategy comparison error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Comparison failed. Please try again later.")


@router.get(
    "/strategies",
    response_model=StrategiesListResponse,
    summary="List available strategies",
    description="Get all available backtesting strategy types.",
)
async def list_strategies(
    current_user=Depends(get_current_user_from_token),
):
    """List available backtesting strategies."""
    strategies = []
    for key, info in BacktestEngine.AVAILABLE_STRATEGIES.items():
        strategies.append(StrategyInfo(
            strategy_type=key,
            description=info["description"],
            default_parameters=info.get("default_params", {}),
        ))

    return StrategiesListResponse(total=len(strategies), strategies=strategies)
