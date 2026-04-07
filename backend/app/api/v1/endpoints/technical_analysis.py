"""
Technical Analysis API endpoints.

Provides REST endpoints for computing 50+ technical indicators,
generating buy/sell summaries, listing available indicators, and
batch-processing multiple symbols.

All endpoints require authentication.
"""
from datetime import date, datetime
from typing import Annotated, Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.logging import get_logger
from app.models.company import Company, MarketData
from app.models.user import User
from app.schemas.technical_analysis import (
    AvailableIndicatorsResponse,
    BatchTechnicalAnalysisRequest,
    BatchTechnicalAnalysisResponse,
    IndicatorInfo,
    IndicatorResult,
    TechnicalAnalysisRequest,
    TechnicalAnalysisResponse,
    TechnicalSummaryRequest,
    TechnicalSummaryResponse,
)
from app.services.analysis.technical_indicators import (
    TechnicalIndicatorCalculator,
    technical_indicator_calculator,
)

# Auth dependency -- follows the same pattern used by the data endpoints
from app.services.auth.auth_service import auth_service


router = APIRouter(prefix="/analysis/technical", tags=["technical-analysis"])
logger = get_logger("api.technical_analysis")

# Reusable calculator instance
calculator = technical_indicator_calculator


# ------------------------------------------------------------------ #
#  Auth dependency (local, mirrors data.py pattern)                   #
# ------------------------------------------------------------------ #


async def get_current_user_from_token(
    authorization: Annotated[Optional[str], None] = None,
    db: Annotated[AsyncSession, Depends(get_async_session)] = None,
) -> User:
    """Extract and validate the current user from the Bearer token."""
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
    return user


# ------------------------------------------------------------------ #
#  Helper functions                                                   #
# ------------------------------------------------------------------ #


async def _fetch_market_data(
    symbol: str,
    period: int,
    db: AsyncSession,
) -> tuple[List[MarketData], Company]:
    """
    Fetch OHLCV market data from the database for the given symbol.

    Args:
        symbol: Ticker symbol (e.g. 'AAPL').
        period: Number of most recent trading days to fetch.
        db: Async database session.

    Returns:
        Tuple of (list of MarketData rows, Company instance).

    Raises:
        HTTPException: If the company or data is not found.
    """
    # Look up the company
    company_result = await db.execute(
        select(Company).where(
            and_(Company.symbol == symbol.upper(), Company.is_active == True)
        )
    )
    company = company_result.scalar_one_or_none()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with symbol '{symbol}' not found",
        )

    # Fetch market data ordered by date descending, limited to *period* rows
    data_result = await db.execute(
        select(MarketData)
        .where(MarketData.company_id == company.id)
        .order_by(MarketData.price_date.desc())
        .limit(period)
    )
    rows = list(data_result.scalars().all())
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No market data found for symbol '{symbol}'",
        )

    # Return in chronological order (oldest first)
    rows.reverse()
    return rows, company


def _ohlcv_to_dataframe(rows: List[MarketData]) -> "pandas.DataFrame":
    """Convert MarketData ORM rows to a pandas DataFrame."""
    import pandas as pd  # local import to avoid top-level cost

    records = [
        {
            "date": row.price_date,
            "open": float(row.open_price) if row.open_price is not None else None,
            "high": float(row.high_price) if row.high_price is not None else None,
            "low": float(row.low_price) if row.low_price is not None else None,
            "close": float(row.close_price),
            "volume": int(row.volume),
        }
        for row in rows
    ]

    df = pd.DataFrame(records)
    if not df.empty:
        df.set_index("date", inplace=True)
        # Drop rows with any NaN in OHLCV columns
        df.dropna(subset=["open", "high", "low", "close", "volume"], inplace=True)

    return df


# ------------------------------------------------------------------ #
#  Endpoints                                                          #
# ------------------------------------------------------------------ #


@router.post(
    "/calculate",
    response_model=TechnicalAnalysisResponse,
    summary="Calculate technical indicators",
    description="Calculate specified technical indicators for a given stock symbol.",
    responses={
        200: {"description": "Indicators calculated successfully"},
        401: {"description": "Authentication required"},
        404: {"description": "Company or market data not found"},
        400: {"description": "Invalid indicator name"},
        500: {"description": "Internal server error"},
    },
)
async def calculate_indicators(
    request: TechnicalAnalysisRequest,
    db: Annotated[AsyncSession, Depends(get_async_session)],
    current_user: User = Depends(get_current_user_from_token),
) -> TechnicalAnalysisResponse:
    """
    Calculate specified technical indicators for a stock symbol.

    Accepts a list of indicator names (up to 50) and returns computed
    values along with latest values and simple signals.
    """
    logger.info(
        f"Calculating indicators for {request.symbol}: {request.indicators}"
    )

    # Validate indicator names early
    unknown = [
        i for i in request.indicators if i not in calculator.INDICATOR_REGISTRY
    ]
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown indicator(s): {unknown}. "
            f"Use GET /analysis/technical/indicators to see available options.",
        )

    rows, company = await _fetch_market_data(request.symbol, request.period, db)
    df = _ohlcv_to_dataframe(rows)

    if df.empty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Insufficient valid market data for '{request.symbol}'",
        )

    results = calculator.calculate_indicators(df, request.indicators)

    indicator_results: List[IndicatorResult] = []
    for name, values in results.items():
        latest = calculator.get_latest_value(values)
        signal = calculator.generate_signal(name, values)
        indicator_results.append(
            IndicatorResult(name=name, values=values, latest_value=latest, signal=signal)
        )

    dates = df.index.tolist()
    return TechnicalAnalysisResponse(
        symbol=request.symbol.upper(),
        indicators=indicator_results,
        data_points=len(df),
        period_start=dates[0] if dates else None,
        period_end=dates[-1] if dates else None,
        calculated_at=datetime.utcnow(),
    )


@router.post(
    "/summary",
    response_model=TechnicalSummaryResponse,
    summary="Technical analysis summary",
    description="Get a consolidated technical analysis summary with buy/sell signal.",
    responses={
        200: {"description": "Summary generated successfully"},
        401: {"description": "Authentication required"},
        404: {"description": "Company or market data not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_technical_summary(
    request: TechnicalSummaryRequest,
    db: Annotated[AsyncSession, Depends(get_async_session)],
    current_user: User = Depends(get_current_user_from_token),
) -> TechnicalSummaryResponse:
    """
    Generate a comprehensive technical analysis summary.

    Runs a curated set of trend, momentum, volatility, and volume indicators
    then aggregates them into an overall signal.
    """
    logger.info(f"Generating technical summary for {request.symbol}")

    rows, company = await _fetch_market_data(request.symbol, request.period, db)
    df = _ohlcv_to_dataframe(rows)

    if df.empty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Insufficient valid market data for '{request.symbol}'",
        )

    # Core indicators for the summary
    summary_indicators = [
        # Trend
        "sma", "ema", "macd", "adx", "supertrend",
        # Momentum
        "rsi", "stochastic", "cci", "williams_r", "mfi",
        # Volatility
        "bollinger_bands", "atr",
        # Volume
        "obv", "cmf",
        # Levels
        "fibonacci_retracement", "pivot_points",
    ]

    results = calculator.calculate_indicators(df, summary_indicators)

    # -- Collect per-indicator signals --
    indicator_signals: List[Dict[str, str]] = []
    bullish_count = 0
    bearish_count = 0

    for name in summary_indicators:
        values = results.get(name, {})
        signal = calculator.generate_signal(name, values) or "neutral"

        desc = calculator.INDICATOR_REGISTRY.get(name, {}).get("description", "")
        indicator_signals.append(
            {"name": name, "signal": signal, "description": desc}
        )

        if signal == "bullish":
            bullish_count += 1
        elif signal == "bearish":
            bearish_count += 1

    total = len(summary_indicators)
    neutral_count = total - bullish_count - bearish_count

    # -- Overall signal --
    net = bullish_count - bearish_count
    if net >= total * 0.3:
        overall_signal = "strong_buy"
    elif net > 0:
        overall_signal = "buy"
    elif net <= -total * 0.3:
        overall_signal = "strong_sell"
    elif net < 0:
        overall_signal = "sell"
    else:
        overall_signal = "neutral"

    # Signal strength: 0-100, higher means more agreement
    signal_strength = round((max(bullish_count, bearish_count) / total) * 100, 1)

    # -- Trend --
    adx_val = calculator.get_latest_value(results.get("adx", {}))
    sma_val = calculator.get_latest_value(results.get("sma", {}))
    ema_val = calculator.get_latest_value(results.get("ema", {}))
    close_val = float(df["close"].iloc[-1])

    if adx_val is not None and adx_val > 25:
        trend = "bullish" if close_val > (sma_val or close_val) else "bearish"
    else:
        trend = "sideways"

    # -- Momentum --
    rsi_val = calculator.get_latest_value(results.get("rsi", {}))
    if rsi_val is not None:
        if rsi_val > 60:
            momentum = "bullish"
        elif rsi_val < 40:
            momentum = "bearish"
        else:
            momentum = "neutral"
    else:
        momentum = "neutral"

    # -- Volatility --
    atr_val = calculator.get_latest_value(results.get("atr", {}))
    if atr_val is not None and close_val != 0:
        atr_pct = (atr_val / close_val) * 100
        if atr_pct > 3:
            volatility = "high"
        elif atr_pct > 1.5:
            volatility = "medium"
        else:
            volatility = "low"
    else:
        volatility = "medium"

    # -- Key levels --
    fib = results.get("fibonacci_retracement", {})
    pivots = results.get("pivot_points", {})

    key_levels: Dict[str, Optional[float]] = {
        "support": pivots.get("s1"),
        "support_2": pivots.get("s2"),
        "resistance": pivots.get("r1"),
        "resistance_2": pivots.get("r2"),
        "pivot": pivots.get("pivot"),
        "fibonacci_38.2": fib.get("level_38.2"),
        "fibonacci_61.8": fib.get("level_61.8"),
    }

    return TechnicalSummaryResponse(
        symbol=request.symbol.upper(),
        overall_signal=overall_signal,
        signal_strength=signal_strength,
        trend=trend,
        momentum=momentum,
        volatility=volatility,
        key_levels=key_levels,
        indicator_signals=indicator_signals,
    )


@router.get(
    "/indicators",
    response_model=AvailableIndicatorsResponse,
    summary="List available indicators",
    description="List all available technical indicators grouped by category.",
)
async def list_available_indicators(
    current_user: User = Depends(get_current_user_from_token),
) -> AvailableIndicatorsResponse:
    """
    Return all available indicator names, categories, and descriptions.
    """
    categories: Dict[str, List[IndicatorInfo]] = {}

    for name, meta in calculator.INDICATOR_REGISTRY.items():
        cat = meta["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(
            IndicatorInfo(
                name=name,
                category=cat,
                description=meta["description"],
            )
        )

    return AvailableIndicatorsResponse(
        total=len(calculator.INDICATOR_REGISTRY),
        categories=categories,
    )


@router.post(
    "/batch",
    response_model=BatchTechnicalAnalysisResponse,
    summary="Batch calculate technical indicators",
    description="Calculate technical indicators for multiple symbols (max 10).",
    responses={
        200: {"description": "Batch calculation completed"},
        401: {"description": "Authentication required"},
        400: {"description": "Invalid request"},
        500: {"description": "Internal server error"},
    },
)
async def batch_calculate_indicators(
    request: BatchTechnicalAnalysisRequest,
    db: Annotated[AsyncSession, Depends(get_async_session)],
    current_user: User = Depends(get_current_user_from_token),
) -> BatchTechnicalAnalysisResponse:
    """
    Calculate specified technical indicators for multiple symbols.

    Processes up to 10 symbols per request. Symbols that fail (not found,
    insufficient data) are reported in the errors list.
    """
    logger.info(
        f"Batch technical analysis for {len(request.symbols)} symbols: "
        f"{request.symbols}"
    )

    # Validate indicator names early
    unknown = [
        i for i in request.indicators if i not in calculator.INDICATOR_REGISTRY
    ]
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown indicator(s): {unknown}",
        )

    # Deduplicate while preserving order
    seen = set()
    unique_symbols: List[str] = []
    for s in request.symbols:
        s_upper = s.upper()
        if s_upper not in seen:
            seen.add(s_upper)
            unique_symbols.append(s_upper)

    successful_results: List[TechnicalAnalysisResponse] = []
    errors: List[Dict[str, str]] = []

    for symbol in unique_symbols:
        try:
            rows, company = await _fetch_market_data(symbol, request.period, db)
            df = _ohlcv_to_dataframe(rows)

            if df.empty:
                errors.append(
                    {"symbol": symbol, "error": "Insufficient valid market data"}
                )
                continue

            results = calculator.calculate_indicators(df, request.indicators)

            indicator_results: List[IndicatorResult] = []
            for name, values in results.items():
                latest = calculator.get_latest_value(values)
                signal = calculator.generate_signal(name, values)
                indicator_results.append(
                    IndicatorResult(
                        name=name, values=values, latest_value=latest, signal=signal
                    )
                )

            dates = df.index.tolist()
            successful_results.append(
                TechnicalAnalysisResponse(
                    symbol=symbol,
                    indicators=indicator_results,
                    data_points=len(df),
                    period_start=dates[0] if dates else None,
                    period_end=dates[-1] if dates else None,
                    calculated_at=datetime.utcnow(),
                )
            )

        except HTTPException as exc:
            errors.append({"symbol": symbol, "error": exc.detail})
        except Exception as exc:
            logger.error(f"Error processing symbol {symbol}: {exc}")
            errors.append({"symbol": symbol, "error": str(exc)})

    return BatchTechnicalAnalysisResponse(
        results=successful_results,
        successful=len(successful_results),
        failed=len(errors),
        errors=errors,
    )
