"""
Tests for the TechnicalIndicatorCalculator.

Drives the main entry point (`calculate_indicators`) across every registered
indicator using a deterministic synthetic OHLCV DataFrame, then adds targeted
coverage for validation helpers, edge cases, and serialisation.
"""
from __future__ import annotations

from typing import Any, Dict

import numpy as np
import pandas as pd
import pytest

from app.services.analysis.technical_indicators import TechnicalIndicatorCalculator


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def calc() -> TechnicalIndicatorCalculator:
    return TechnicalIndicatorCalculator()


@pytest.fixture(scope="module")
def ohlcv() -> pd.DataFrame:
    """Deterministic 250-bar OHLCV DataFrame with valid OHLC relationships.

    Generates `open` and `close` from a random walk, then derives `high` and
    `low` so that `low <= min(open, close)` and `high >= max(open, close)`.
    This produces realistic candles where stochastic-style indicators stay
    in [0, 100].
    """
    rng = np.random.default_rng(42)
    n = 250
    base = 100 + np.cumsum(rng.normal(0.05, 1.0, n))  # mild upward drift
    open_ = base + rng.normal(0.0, 0.2, n)
    close = base + rng.normal(0.0, 0.2, n)
    body_low = np.minimum(open_, close)
    body_high = np.maximum(open_, close)
    low = body_low - np.abs(rng.normal(0.3, 0.2, n))
    high = body_high + np.abs(rng.normal(0.3, 0.2, n))
    volume = (rng.integers(1_000_000, 10_000_000, n)).astype(float)
    return pd.DataFrame(
        {
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        },
        index=pd.date_range("2024-01-01", periods=n, freq="D"),
    )


# ---------------------------------------------------------------------------
# Registry & helpers
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRegistryAndHelpers:
    def test_registry_and_method_map_consistent(self, calc):
        assert set(calc.INDICATOR_REGISTRY.keys()) == set(calc._method_map.keys())
        # Every registered method exists on the class
        for name, method_name in calc._method_map.items():
            assert hasattr(calc, method_name), f"missing {method_name} for {name}"

    def test_validate_dataframe_passes_for_complete_df(self, calc, ohlcv):
        # Should not raise
        calc._validate_dataframe(ohlcv, require_volume=True)

    def test_validate_dataframe_raises_for_missing_column(self, calc):
        df = pd.DataFrame({"open": [1], "high": [1], "low": [1]})  # no close
        with pytest.raises(ValueError, match="missing required columns"):
            calc._validate_dataframe(df)

    def test_validate_dataframe_raises_for_empty(self, calc):
        df = pd.DataFrame({"open": [], "high": [], "low": [], "close": []})
        with pytest.raises(ValueError, match="empty"):
            calc._validate_dataframe(df)

    def test_validate_dataframe_volume_optional(self, calc):
        df = pd.DataFrame(
            {"open": [1], "high": [1], "low": [1], "close": [1]}
        )
        calc._validate_dataframe(df, require_volume=False)
        with pytest.raises(ValueError):
            calc._validate_dataframe(df, require_volume=True)

    def test_safe_float_handles_nan_inf_none(self, calc):
        assert calc._safe_float(1.5) == 1.5
        assert calc._safe_float(float("nan")) is None
        assert calc._safe_float(float("inf")) is None
        assert calc._safe_float(float("-inf")) is None
        assert calc._safe_float(None) is None
        assert calc._safe_float("not-a-number") is None

    def test_series_to_list_replaces_nan_with_none(self, calc):
        s = pd.Series([1.0, float("nan"), 3.0, float("inf")])
        result = calc._series_to_list(s)
        assert result == [1.0, None, 3.0, None]


# ---------------------------------------------------------------------------
# Main entry point — drive every registered indicator
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCalculateIndicatorsAll:
    def test_all_registered_indicators_run_without_error(self, calc, ohlcv):
        all_names = list(calc._method_map.keys())
        results = calc.calculate_indicators(ohlcv, all_names)
        # Result must have an entry for every requested name
        assert set(results.keys()) == set(all_names)
        # And NONE should be an error dict
        errored = {n: r for n, r in results.items() if "error" in r}
        assert errored == {}, f"Indicators errored: {errored}"

    def test_unknown_indicator_raises(self, calc, ohlcv):
        with pytest.raises(ValueError, match="Unknown indicator"):
            calc.calculate_indicators(ohlcv, ["sma", "frobnicate"])

    def test_each_indicator_yields_at_least_one_non_none_value(self, calc, ohlcv):
        all_names = list(calc._method_map.keys())
        results = calc.calculate_indicators(ohlcv, all_names)
        empty_results = []
        for name, result in results.items():
            latest = calc.get_latest_value(result)
            if latest is None:
                # Pivot points & fibonacci_retracement can legitimately return
                # only level-keyed scalars; check the raw values instead
                has_any_scalar = any(
                    isinstance(v, (int, float)) and v is not None
                    for v in result.values()
                )
                has_any_list_value = any(
                    isinstance(v, list) and any(x is not None for x in v)
                    for v in result.values()
                )
                if not (has_any_scalar or has_any_list_value):
                    empty_results.append(name)
        assert empty_results == [], f"Indicators with no values: {empty_results}"


# ---------------------------------------------------------------------------
# Spot-check specific indicators have correct shape / numeric properties
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSpecificIndicators:
    def test_sma_smooths_input(self, calc, ohlcv):
        sma = calc.calculate_sma(ohlcv, period=20)
        # First (period-1) values are NaN
        assert sma.iloc[:19].isna().all()
        assert sma.iloc[19:].notna().all()
        # SMA is bounded by min/max of the data window
        assert sma.iloc[19] == pytest.approx(ohlcv["close"].iloc[:20].mean(), abs=1e-9)

    def test_ema_no_warmup_nan(self, calc, ohlcv):
        ema = calc.calculate_ema(ohlcv, period=20)
        # EMA (adjust=False) is defined from the first bar
        assert ema.notna().all()

    def test_macd_columns(self, calc, ohlcv):
        macd = calc.calculate_macd(ohlcv)
        assert {"macd", "signal", "histogram"}.issubset(macd.columns)
        # histogram = macd - signal everywhere it's defined
        diff = macd["macd"] - macd["signal"] - macd["histogram"]
        assert diff.abs().max() < 1e-9

    def test_rsi_in_zero_to_hundred(self, calc, ohlcv):
        rsi = calc.calculate_rsi(ohlcv, period=14)
        valid = rsi.dropna()
        assert (valid >= 0).all() and (valid <= 100).all()

    def test_bollinger_bands_ordering(self, calc, ohlcv):
        bb = calc.calculate_bollinger_bands(ohlcv, period=20)
        # upper >= middle >= lower
        valid = bb.dropna()
        assert (valid["upper"] >= valid["middle"]).all()
        assert (valid["middle"] >= valid["lower"]).all()

    def test_atr_non_negative(self, calc, ohlcv):
        atr = calc.calculate_atr(ohlcv, period=14)
        valid = atr.dropna()
        assert (valid >= 0).all()

    def test_obv_monotone_changes_on_close_direction(self, calc, ohlcv):
        obv = calc.calculate_obv(ohlcv)
        # OBV must change in the same sign as close direction (or be flat)
        close_diff = ohlcv["close"].diff()
        obv_diff = obv.diff()
        # For non-NaN, non-zero close changes, signs must match
        mask = close_diff.abs() > 1e-9
        signs_match = np.sign(close_diff[mask]) == np.sign(obv_diff[mask].replace(0, np.nan)).fillna(np.sign(close_diff[mask]))
        assert signs_match.mean() > 0.95  # essentially always

    def test_stochastic_in_zero_to_hundred(self, calc, ohlcv):
        stoch = calc.calculate_stochastic(ohlcv)
        for col in ("percent_k", "percent_d"):
            valid = stoch[col].dropna()
            assert (valid >= 0).all() and (valid <= 100).all()

    def test_fibonacci_retracement_levels_present(self, calc, ohlcv):
        fib = calc.calculate_fibonacci_retracement(ohlcv)
        # Look for any level keys; format is "level_<pct>"
        level_keys = [k for k in fib.keys() if k.startswith("level_")]
        assert len(level_keys) >= 5  # 0, 23.6, 38.2, 50, 61.8, 78.6, 100 is typical

    def test_pivot_points_relationships(self, calc, ohlcv):
        pp = calc.calculate_pivot_points(ohlcv)
        # Standard ordering: s3 < s2 < s1 < pivot < r1 < r2 < r3
        order = ("s3", "s2", "s1", "pivot", "r1", "r2", "r3")
        vals = [pp[k] for k in order]
        assert all(a <= b for a, b in zip(vals, vals[1:]))

    def test_heikin_ashi_returns_ohlc(self, calc, ohlcv):
        ha = calc.calculate_heikin_ashi(ohlcv)
        # Output uses ha_<col> naming
        assert {"ha_open", "ha_high", "ha_low", "ha_close"}.issubset(ha.columns)
        assert len(ha) == len(ohlcv)


@pytest.mark.unit
class TestGetLatestValue:
    def test_get_latest_value_from_list(self, calc):
        result = {"value": [1.0, None, 2.0, None]}
        assert calc.get_latest_value(result) == 2.0

    def test_get_latest_value_returns_none_for_all_none(self, calc):
        assert calc.get_latest_value({"value": [None, None]}) is None

    def test_get_latest_value_skips_error_key(self, calc):
        # Error key should be ignored
        result = {"error": "oops", "value": [1.0, 2.0]}
        assert calc.get_latest_value(result) == 2.0

    def test_get_latest_value_from_nested_dict(self, calc):
        result = {"nested": {"a": [None, 5.5]}}
        assert calc.get_latest_value(result) == 5.5
