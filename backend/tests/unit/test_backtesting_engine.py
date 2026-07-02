"""
Tests for the backtesting engine.

Drives the public `run_backtest` entry point across all supported strategy
types using synthetic OHLCV data, then exercises the private helpers via
direct calls.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.services.backtesting.engine import (
    BacktestConfig,
    BacktestEngine,
    SlippageConfig,
    StrategyConfig,
    TransactionCostConfig,
)


@pytest.fixture
def engine() -> BacktestEngine:
    return BacktestEngine()


@pytest.fixture
def ohlcv() -> pd.DataFrame:
    """One symbol, 252 bars, mild upward drift with valid OHLC."""
    rng = np.random.default_rng(11)
    n = 252
    base = 100 + np.cumsum(rng.normal(0.05, 1.0, n))
    open_ = base + rng.normal(0.0, 0.2, n)
    close = base + rng.normal(0.0, 0.2, n)
    high = np.maximum(open_, close) + np.abs(rng.normal(0.3, 0.2, n))
    low = np.minimum(open_, close) - np.abs(rng.normal(0.3, 0.2, n))
    volume = rng.integers(1_000_000, 5_000_000, n).astype(float)
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=pd.date_range("2024-01-01", periods=n, freq="D"),
    )


@pytest.fixture
def benchmark(ohlcv) -> pd.DataFrame:
    return ohlcv.copy()


# ---------------------------------------------------------------------------
# Strategy types — run_backtest for each
# ---------------------------------------------------------------------------


STRATEGIES = [
    ("sma_crossover", {"fast_period": 10, "slow_period": 30}),
    ("ema_crossover", {"fast_period": 8, "slow_period": 21}),
    ("rsi", {"period": 14, "oversold": 30, "overbought": 70}),
    ("bollinger", {"period": 20, "num_std": 2}),
    ("macd", {"fast_period": 12, "slow_period": 26, "signal_period": 9}),
    ("dual_momentum", {"lookback": 60}),
]


@pytest.mark.unit
@pytest.mark.asyncio
class TestRunBacktest:
    @pytest.mark.parametrize("strategy,params", STRATEGIES)
    async def test_each_strategy_completes(self, engine, ohlcv, strategy, params):
        config = BacktestConfig(
            symbols=["AAPL"],
            strategy=StrategyConfig(strategy_type=strategy, parameters=params),
            initial_capital=100_000.0,
            benchmark_symbol=None,
        )
        result = await engine.run_backtest({"AAPL": ohlcv}, config)
        assert result.status == "completed", result
        assert result.strategy == strategy
        assert result.initial_capital == 100_000.0
        assert result.final_value is not None
        assert isinstance(result.equity_curve, list)
        # Metrics are populated
        assert result.metrics is not None
        assert result.metrics.total_return is not None

    async def test_empty_price_data_returns_error_status(self, engine):
        config = BacktestConfig(
            symbols=["UNKNOWN"],
            strategy=StrategyConfig(strategy_type="sma_crossover"),
        )
        result = await engine.run_backtest({}, config)
        assert result.status == "error"

    async def test_with_benchmark_data_computes_benchmark_return(
        self, engine, ohlcv, benchmark
    ):
        config = BacktestConfig(
            symbols=["AAPL"],
            strategy=StrategyConfig(strategy_type="sma_crossover"),
            benchmark_symbol="SPY",
        )
        result = await engine.run_backtest(
            {"AAPL": ohlcv}, config, benchmark_data=benchmark
        )
        assert result.status == "completed"
        assert result.benchmark_total_return is not None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCommission:
    def test_percentage_commission(self, engine):
        cfg = TransactionCostConfig(model="percentage", value=0.001)
        fee = engine._calculate_commission(price=100.0, shares=10.0, config=cfg)
        # 0.1% of 1000 = 1.0
        assert fee == pytest.approx(1.0)

    def test_flat_commission(self, engine):
        cfg = TransactionCostConfig(model="flat", value=5.0)
        fee = engine._calculate_commission(price=100.0, shares=10.0, config=cfg)
        assert fee == 5.0

    def test_per_share_commission(self, engine):
        cfg = TransactionCostConfig(model="per_share", value=0.01)
        fee = engine._calculate_commission(price=100.0, shares=10.0, config=cfg)
        assert fee == pytest.approx(0.10)


@pytest.mark.unit
class TestSlippage:
    def test_percentage_slippage(self, engine):
        cfg = SlippageConfig(model="percentage", value=0.001)
        slip = engine._calculate_slippage(shares=10.0, price=100.0, volume=1_000_000, config=cfg)
        assert slip > 0

    def test_fixed_slippage(self, engine):
        cfg = SlippageConfig(model="fixed", value=0.05)
        slip = engine._calculate_slippage(shares=10.0, price=100.0, volume=1_000_000, config=cfg)
        # 10 * 0.05 = 0.5
        assert slip == pytest.approx(0.5)

    def test_volume_based_slippage(self, engine):
        cfg = SlippageConfig(model="volume_based", value=0.001)
        slip = engine._calculate_slippage(shares=10.0, price=100.0, volume=1_000_000, config=cfg)
        assert slip >= 0


@pytest.mark.unit
class TestSignalHelpers:
    def test_sma_crossover_signals_returns_series(self, engine, ohlcv):
        signals = engine._sma_crossover_signals(
            ohlcv, {"fast_period": 10, "slow_period": 30}
        )
        assert isinstance(signals, pd.Series)
        # Should have at least one buy or sell signal somewhere
        assert signals.abs().sum() > 0

    def test_rsi_signals_returns_series(self, engine, ohlcv):
        signals = engine._rsi_signals(
            ohlcv, {"period": 14, "oversold": 30, "overbought": 70}
        )
        assert isinstance(signals, pd.Series)

    def test_bollinger_signals(self, engine, ohlcv):
        signals = engine._bollinger_signals(ohlcv, {"period": 20, "num_std": 2})
        assert isinstance(signals, pd.Series)

    def test_macd_signals(self, engine, ohlcv):
        signals = engine._macd_signals(
            ohlcv, {"fast_period": 12, "slow_period": 26, "signal_period": 9}
        )
        assert isinstance(signals, pd.Series)
