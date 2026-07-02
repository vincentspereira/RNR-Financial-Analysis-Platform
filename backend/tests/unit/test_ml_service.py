"""
Tests for app.services.analytics.ml_service.FinancialMLService.

Drives both the mock fallback paths (when sklearn is "unavailable") and the
real ML paths (with historical data and feature engineering helpers).
"""
from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from app.services.analytics.ml_service import (
    FinancialMLService,
    MLPrediction,
    ModelPerformance,
    ModelType,
    PredictionType,
)


@pytest.fixture
def svc() -> FinancialMLService:
    return FinancialMLService()


@pytest.fixture
def synthetic_data() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    n = 200
    base = 100 + np.cumsum(rng.normal(0.05, 1.0, n))
    open_ = base + rng.normal(0.0, 0.2, n)
    close = base + rng.normal(0.0, 0.2, n)
    high = np.maximum(open_, close) + np.abs(rng.normal(0.3, 0.2, n))
    low = np.minimum(open_, close) - np.abs(rng.normal(0.3, 0.2, n))
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close,
         "volume": rng.integers(1_000_000, 5_000_000, n).astype(float)},
        index=pd.date_range("2024-01-01", periods=n, freq="D"),
    )


# ---------------------------------------------------------------------------
# Technical indicator helpers (pure functions)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTechnicalHelpers:
    def test_calculate_rsi_in_zero_to_hundred(self, svc, synthetic_data):
        rsi = svc._calculate_rsi(synthetic_data["close"])
        valid = rsi.dropna()
        assert (valid >= 0).all() and (valid <= 100).all()

    def test_calculate_macd_returns_series(self, svc, synthetic_data):
        macd = svc._calculate_macd(synthetic_data["close"])
        assert isinstance(macd, pd.Series)
        assert len(macd) == len(synthetic_data)

    def test_bollinger_bands_ordering(self, svc, synthetic_data):
        upper, lower = svc._calculate_bollinger_bands(synthetic_data["close"])
        valid_mask = upper.notna() & lower.notna()
        assert (upper[valid_mask] >= lower[valid_mask]).all()

    def test_stochastic_returns_two_series(self, svc, synthetic_data):
        k, d = svc._calculate_stochastic(synthetic_data)
        assert isinstance(k, pd.Series) and isinstance(d, pd.Series)

    def test_max_drawdown_returns_negative_or_zero(self, svc):
        returns = pd.Series([0.01, -0.05, 0.02, -0.10, 0.03])
        dd = svc._calculate_max_drawdown(returns)
        assert dd <= 0

    def test_portfolio_beta(self, svc, synthetic_data):
        # Need a returns DataFrame
        returns_df = pd.DataFrame({
            "A": synthetic_data["close"].pct_change().fillna(0),
            "B": synthetic_data["close"].pct_change().fillna(0) * 1.1,
        }).iloc[1:]
        weights = np.array([0.6, 0.4])
        beta = svc._calculate_portfolio_beta(returns_df, weights)
        assert isinstance(beta, float)


# ---------------------------------------------------------------------------
# Weight optimization / portfolio recommendation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestWeightOptimization:
    def test_optimize_weights_no_target_return(self, svc):
        expected_returns = pd.Series([0.08, 0.10, 0.06])
        cov = pd.DataFrame(
            np.diag([0.04, 0.05, 0.03]),
            index=expected_returns.index,
            columns=expected_returns.index,
        )
        weights = svc._optimize_weights(expected_returns, cov, risk_tolerance=0.3)
        assert abs(weights.sum() - 1.0) < 1e-9
        assert (weights >= 0).all()

    def test_optimize_weights_high_risk_tolerance(self, svc):
        expected_returns = pd.Series([0.08, 0.10, 0.06])
        cov = pd.DataFrame(
            np.diag([0.04, 0.05, 0.03]),
            index=expected_returns.index,
            columns=expected_returns.index,
        )
        weights = svc._optimize_weights(expected_returns, cov, risk_tolerance=0.8)
        assert abs(weights.sum() - 1.0) < 1e-6

    def test_optimize_weights_with_target_return(self, svc):
        expected_returns = pd.Series([0.08, 0.10, 0.06])
        cov = pd.DataFrame(
            np.diag([0.04, 0.05, 0.03]),
            index=expected_returns.index,
            columns=expected_returns.index,
        )
        weights = svc._optimize_weights(expected_returns, cov, risk_tolerance=0.5, target_return=0.09)
        assert abs(weights.sum() - 1.0) < 1e-6

    def test_generate_portfolio_recommendation(self, svc):
        weights = np.array([0.6, 0.3, 0.1])
        symbols = ["AAPL", "MSFT", "GOOG"]
        rec = svc._generate_portfolio_recommendation(weights, symbols, 0.12, 0.18)
        assert "AAPL" in rec  # largest weight
        assert "Medium" in rec or "Low" in rec or "High" in rec


# ---------------------------------------------------------------------------
# Mock fallback paths
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMockFallbacks:
    def test_mock_stock_prediction(self, svc):
        result = svc._mock_stock_prediction("AAPL", days_ahead=30)
        assert isinstance(result, MLPrediction)
        assert result.symbol == "AAPL"
        assert result.metadata.get("mock") is True
        assert result.confidence_score > 0

    def test_mock_risk_analysis(self, svc):
        result = svc._mock_risk_analysis({"AAPL": 0.5, "MSFT": 0.5})
        assert "var_95" in result
        assert "sharpe_ratio" in result
        assert result.get("mock") is True

    def test_mock_trading_signals(self, svc):
        result = svc._mock_trading_signals("AAPL")
        assert result["symbol"] == "AAPL"
        assert result["current_signal"] in ("BUY", "SELL", "HOLD")
        assert 0 < result["signal_strength"] < 1

    def test_mock_portfolio_optimization(self, svc):
        result = svc._mock_portfolio_optimization(["AAPL", "MSFT"], risk_tolerance=0.5)
        assert "optimized_weights" in result
        weights = result["optimized_weights"]
        assert abs(sum(weights.values()) - 1.0) < 1e-9

    def test_generate_mock_historical_data(self, svc):
        df = svc._generate_mock_historical_data("AAPL", days=100)
        assert len(df) == 100
        assert {"open", "high", "low", "close", "volume"}.issubset(df.columns)


# ---------------------------------------------------------------------------
# Public async API (driven via the mock paths or with patched _get_historical_data)
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestPublicAPI:
    async def test_predict_stock_price_with_mock_fallback(self, svc):
        with patch("app.services.analytics.ml_service.ML_AVAILABLE", False):
            result = await svc.predict_stock_price("AAPL", days_ahead=10)
        assert isinstance(result, MLPrediction)

    async def test_analyze_portfolio_risk_with_mock_fallback(self, svc):
        with patch("app.services.analytics.ml_service.ML_AVAILABLE", False):
            result = await svc.analyze_portfolio_risk({"AAPL": 0.6, "MSFT": 0.4})
        assert isinstance(result, dict)

    async def test_generate_trading_signals_with_mock_fallback(self, svc):
        with patch("app.services.analytics.ml_service.ML_AVAILABLE", False):
            result = await svc.generate_trading_signals("AAPL")
        assert "symbol" in result

    async def test_optimize_portfolio_with_mock_fallback(self, svc):
        with patch("app.services.analytics.ml_service.ML_AVAILABLE", False):
            result = await svc.optimize_portfolio(["AAPL", "MSFT", "GOOG"], risk_tolerance=0.5)
        assert "optimized_weights" in result


# ---------------------------------------------------------------------------
# Historical data helper
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestHistoricalData:
    async def test_get_historical_data_falls_back_to_mock(self, svc):
        # YFINANCE_AVAILABLE may be true, but Ticker().history may not actually
        # hit network in test env — let's patch it to return empty so the
        # fallback path runs.
        with patch("app.services.analytics.ml_service.YFINANCE_AVAILABLE", False):
            result = await svc._get_historical_data("AAPL", period="1y")
        assert isinstance(result, pd.DataFrame)
        # Mock data was generated
        assert len(result) > 0


# ---------------------------------------------------------------------------
# Feature preparation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFeaturePreparation:
    def test_prepare_stock_features_returns_dataframe(self, svc, synthetic_data):
        features = svc._prepare_stock_features(synthetic_data)
        assert isinstance(features, pd.DataFrame)
        assert len(features) > 0

    def test_prepare_signal_features_returns_dataframe(self, svc, synthetic_data):
        features = svc._prepare_signal_features(synthetic_data)
        assert isinstance(features, pd.DataFrame)
        assert len(features) > 0
