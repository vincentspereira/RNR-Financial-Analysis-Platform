"""
Technical Indicator Calculator for the RNR Financial Analysis Platform.

Computes 50+ technical analysis indicators using pure numpy/pandas.
Each method accepts a DataFrame with columns: open, high, low, close, volume
and returns indicator values as dicts, Series, or DataFrames.

Categories:
    - Trend Indicators (SMA, EMA, MACD, ADX, Ichimoku, etc.)
    - Momentum Indicators (RSI, Stochastic, CCI, ROC, etc.)
    - Volatility Indicators (Bollinger Bands, ATR, Keltner, etc.)
    - Volume Indicators (OBV, VWAP, CMF, etc.)
    - Other Indicators (Fibonacci, Pivot Points, Heikin-Ashi)
"""
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd

from app.core.logging import get_logger

logger = get_logger("app.services.analysis.technical_indicators")

# Type alias for indicator output
IndicatorOutput = Union[pd.Series, pd.DataFrame, Dict[str, Any]]


class TechnicalIndicatorCalculator:
    """
    Comprehensive technical indicator calculator.

    Provides 50+ indicators grouped by category. All methods accept a
    pandas DataFrame with OHLCV columns and return indicator values.

    The main entry point is ``calculate_indicators`` which takes a list of
    indicator names and returns all requested results in a single call.
    """

    # ------------------------------------------------------------------ #
    #  Indicator registry                                                 #
    # ------------------------------------------------------------------ #

    INDICATOR_REGISTRY: Dict[str, Dict[str, str]] = {
        # Trend
        "sma": {"category": "trend", "description": "Simple Moving Average"},
        "ema": {"category": "trend", "description": "Exponential Moving Average"},
        "wma": {"category": "trend", "description": "Weighted Moving Average"},
        "dema": {"category": "trend", "description": "Double Exponential Moving Average"},
        "tema": {"category": "trend", "description": "Triple Exponential Moving Average"},
        "macd": {"category": "trend", "description": "Moving Average Convergence Divergence"},
        "adx": {"category": "trend", "description": "Average Directional Index"},
        "ichimoku": {"category": "trend", "description": "Ichimoku Cloud"},
        "parabolic_sar": {"category": "trend", "description": "Parabolic SAR"},
        "supertrend": {"category": "trend", "description": "Supertrend"},
        "aroon": {"category": "trend", "description": "Aroon Up/Down Oscillator"},
        "linear_regression": {"category": "trend", "description": "Linear Regression / Least Squares"},
        # Momentum
        "rsi": {"category": "momentum", "description": "Relative Strength Index"},
        "stochastic": {"category": "momentum", "description": "Stochastic Oscillator (%K, %D)"},
        "williams_r": {"category": "momentum", "description": "Williams %R"},
        "cci": {"category": "momentum", "description": "Commodity Channel Index"},
        "roc": {"category": "momentum", "description": "Rate of Change"},
        "momentum": {"category": "momentum", "description": "Momentum"},
        "tsi": {"category": "momentum", "description": "True Strength Index"},
        "ultimate_oscillator": {"category": "momentum", "description": "Ultimate Oscillator"},
        "roc_volume": {"category": "momentum", "description": "Rate of Change of Volume"},
        "mfi": {"category": "momentum", "description": "Money Flow Index"},
        "stochastic_rsi": {"category": "momentum", "description": "Stochastic RSI"},
        "awesome_oscillator": {"category": "momentum", "description": "Awesome Oscillator"},
        # Volatility
        "bollinger_bands": {"category": "volatility", "description": "Bollinger Bands (upper, middle, lower, bandwidth, %B)"},
        "keltner_channels": {"category": "volatility", "description": "Keltner Channels"},
        "donchian_channels": {"category": "volatility", "description": "Donchian Channels"},
        "atr": {"category": "volatility", "description": "Average True Range"},
        "std_dev": {"category": "volatility", "description": "Rolling Standard Deviation"},
        "true_range": {"category": "volatility", "description": "True Range"},
        "chaikin_volatility": {"category": "volatility", "description": "Chaikin Volatility"},
        "bollinger_bandwidth": {"category": "volatility", "description": "Bollinger Band Width"},
        "bollinger_pct_b": {"category": "volatility", "description": "Bollinger Band %B"},
        # Volume
        "obv": {"category": "volume", "description": "On Balance Volume"},
        "vwap": {"category": "volume", "description": "Volume Weighted Average Price"},
        "adl": {"category": "volume", "description": "Accumulation/Distribution Line"},
        "cmf": {"category": "volume", "description": "Chaikin Money Flow"},
        "force_index": {"category": "volume", "description": "Force Index"},
        "vpt": {"category": "volume", "description": "Volume Price Trend"},
        "ease_of_movement": {"category": "volume", "description": "Ease of Movement"},
        "volume_oscillator": {"category": "volume", "description": "Volume Oscillator"},
        "nvi": {"category": "volume", "description": "Negative Volume Index"},
        "pvi": {"category": "volume", "description": "Positive Volume Index"},
        # Other
        "fibonacci_retracement": {"category": "other", "description": "Fibonacci Retracement Levels"},
        "pivot_points": {"category": "other", "description": "Pivot Points (Standard)"},
        "vwap_bands": {"category": "other", "description": "VWAP Bands"},
        "heikin_ashi": {"category": "other", "description": "Heikin-Ashi Candlesticks"},
        # Additional indicators (to reach 50+)
        "hma": {"category": "trend", "description": "Hull Moving Average"},
        "choppiness_index": {"category": "momentum", "description": "Choppiness Index (CHOP)"},
        "elder_ray": {"category": "momentum", "description": "Elder Ray Bull/Bear Power"},
        "coppock_curve": {"category": "momentum", "description": "Coppock Curve (long-term buy signal)"},
        # Professional-grade additions
        "vwap_std_bands": {"category": "volume", "description": "VWAP with Standard Deviation Bands"},
        "mass_index": {"category": "volatility", "description": "Mass Index (reversal detection)"},
        "connors_rsi": {"category": "momentum", "description": "Connors RSI (3-component composite)"},
        "klinger_oscillator": {"category": "volume", "description": "Klinger Volume Oscillator (KVO)"},
        "mcginley_dynamic": {"category": "trend", "description": "McGinley Dynamic (adaptive moving average)"},
        "trix": {"category": "momentum", "description": "TRIX (triple-smoothed EMA rate of change)"},
        "alma": {"category": "trend", "description": "Arnaud Legoux Moving Average"},
        "chande_kroll_stop": {"category": "volatility", "description": "Chande Kroll Stop (stop-loss placement)"},
        "relative_vigor_index": {"category": "momentum", "description": "Relative Vigor Index (RVI)"},
    }

    # ------------------------------------------------------------------ #
    #  Constructor & helpers                                              #
    # ------------------------------------------------------------------ #

    def __init__(self) -> None:
        self._method_map: Dict[str, str] = {
            "sma": "calculate_sma",
            "ema": "calculate_ema",
            "wma": "calculate_wma",
            "dema": "calculate_dema",
            "tema": "calculate_tema",
            "macd": "calculate_macd",
            "adx": "calculate_adx",
            "ichimoku": "calculate_ichimoku",
            "parabolic_sar": "calculate_parabolic_sar",
            "supertrend": "calculate_supertrend",
            "aroon": "calculate_aroon",
            "linear_regression": "calculate_linear_regression",
            "rsi": "calculate_rsi",
            "stochastic": "calculate_stochastic",
            "williams_r": "calculate_williams_r",
            "cci": "calculate_cci",
            "roc": "calculate_roc",
            "momentum": "calculate_momentum",
            "tsi": "calculate_tsi",
            "ultimate_oscillator": "calculate_ultimate_oscillator",
            "roc_volume": "calculate_roc_volume",
            "mfi": "calculate_mfi",
            "stochastic_rsi": "calculate_stochastic_rsi",
            "awesome_oscillator": "calculate_awesome_oscillator",
            "bollinger_bands": "calculate_bollinger_bands",
            "keltner_channels": "calculate_keltner_channels",
            "donchian_channels": "calculate_donchian_channels",
            "atr": "calculate_atr",
            "std_dev": "calculate_std_dev",
            "true_range": "calculate_true_range",
            "chaikin_volatility": "calculate_chaikin_volatility",
            "bollinger_bandwidth": "calculate_bollinger_bandwidth",
            "bollinger_pct_b": "calculate_bollinger_pct_b",
            "obv": "calculate_obv",
            "vwap": "calculate_vwap",
            "adl": "calculate_adl",
            "cmf": "calculate_cmf",
            "force_index": "calculate_force_index",
            "vpt": "calculate_vpt",
            "ease_of_movement": "calculate_ease_of_movement",
            "volume_oscillator": "calculate_volume_oscillator",
            "nvi": "calculate_nvi",
            "pvi": "calculate_pvi",
            "fibonacci_retracement": "calculate_fibonacci_retracement",
            "pivot_points": "calculate_pivot_points",
            "vwap_bands": "calculate_vwap_bands",
            "heikin_ashi": "calculate_heikin_ashi",
            "hma": "calculate_hma",
            "choppiness_index": "calculate_choppiness_index",
            "elder_ray": "calculate_elder_ray",
            "coppock_curve": "calculate_coppock_curve",
            "vwap_std_bands": "calculate_vwap_std_bands",
            "mass_index": "calculate_mass_index",
            "connors_rsi": "calculate_connors_rsi",
            "klinger_oscillator": "calculate_klinger_oscillator",
            "mcginley_dynamic": "calculate_mcginley_dynamic",
            "trix": "calculate_trix",
            "alma": "calculate_alma",
            "chande_kroll_stop": "calculate_chande_kroll_stop",
            "relative_vigor_index": "calculate_relative_vigor_index",
        }

    @staticmethod
    def _validate_dataframe(df: pd.DataFrame, require_volume: bool = False) -> None:
        """Validate that the DataFrame has the required OHLCV columns."""
        required = ["open", "high", "low", "close"]
        if require_volume:
            required.append("volume")
        missing = [col for col in required if col not in df.columns]
        if missing:
            raise ValueError(f"DataFrame missing required columns: {missing}")
        if df.empty:
            raise ValueError("DataFrame is empty")

    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        """Convert a value to float, returning None for NaN/inf."""
        if value is None:
            return None
        try:
            f = float(value)
            if np.isnan(f) or np.isinf(f):
                return None
            return f
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _series_to_list(series: pd.Series) -> List[Optional[float]]:
        """Convert a pandas Series to a list of floats, replacing NaN with None."""
        return [
            None if pd.isna(v) or np.isinf(v) else float(v)
            for v in series.values
        ]

    def _df_to_dict(self, result: IndicatorOutput) -> Dict[str, Any]:
        """Convert indicator output to a serializable dict."""
        if isinstance(result, pd.DataFrame):
            return {
                col: self._series_to_list(result[col]) for col in result.columns
            }
        if isinstance(result, pd.Series):
            return {"value": self._series_to_list(result)}
        if isinstance(result, dict):
            out: Dict[str, Any] = {}
            for key, val in result.items():
                if isinstance(val, pd.Series):
                    out[key] = self._series_to_list(val)
                elif isinstance(val, pd.DataFrame):
                    out[key] = {
                        c: self._series_to_list(val[c]) for c in val.columns
                    }
                elif isinstance(val, (np.integer,)):
                    out[key] = int(val)
                elif isinstance(val, (np.floating,)):
                    out[key] = self._safe_float(val)
                else:
                    out[key] = val
            return out
        return {"value": result}

    # ------------------------------------------------------------------ #
    #  Main entry point                                                   #
    # ------------------------------------------------------------------ #

    def calculate_indicators(
        self,
        df: pd.DataFrame,
        indicators: List[str],
    ) -> Dict[str, Dict[str, Any]]:
        """
        Calculate multiple technical indicators at once.

        Args:
            df: DataFrame with columns open, high, low, close, volume.
            indicators: List of indicator names to calculate.

        Returns:
            Dictionary mapping indicator name to its computed values.

        Raises:
            ValueError: If an unknown indicator name is provided.
        """
        self._validate_dataframe(df, require_volume=True)

        unknown = [i for i in indicators if i not in self._method_map]
        if unknown:
            raise ValueError(
                f"Unknown indicator(s): {unknown}. "
                f"Available: {list(self._method_map.keys())}"
            )

        results: Dict[str, Dict[str, Any]] = {}
        for name in indicators:
            method_name = self._method_map[name]
            method = getattr(self, method_name)
            try:
                raw = method(df.copy())
                results[name] = self._df_to_dict(raw)
            except Exception as exc:
                logger.error(f"Error calculating {name}: {exc}")
                results[name] = {"error": str(exc)}
        return results

    def get_latest_value(self, indicator_result: Dict[str, Any]) -> Optional[float]:
        """Extract the latest scalar value from an indicator result dict."""
        for key, val in indicator_result.items():
            if key == "error":
                continue
            if isinstance(val, list):
                # Walk backwards to find last non-None
                for item in reversed(val):
                    if item is not None:
                        return item
            elif isinstance(val, dict):
                # Nested: take the last non-None from the first sub-key
                for sub_key, sub_val in val.items():
                    if isinstance(sub_val, list):
                        for item in reversed(sub_val):
                            if item is not None:
                                return item
        return None

    # ================================================================== #
    #  TREND INDICATORS                                                   #
    # ================================================================== #

    def calculate_sma(
        self, df: pd.DataFrame, period: int = 20
    ) -> pd.Series:
        """
        Simple Moving Average.

        The average closing price over the last *period* bars.

        Args:
            df: OHLCV DataFrame.
            period: Lookback window (default 20).

        Returns:
            Series of SMA values.
        """
        return df["close"].rolling(window=period, min_periods=period).mean()

    def calculate_ema(
        self, df: pd.DataFrame, period: int = 20
    ) -> pd.Series:
        """
        Exponential Moving Average.

        Weighted moving average giving more weight to recent prices.

        Args:
            df: OHLCV DataFrame.
            period: Span parameter (default 20).

        Returns:
            Series of EMA values.
        """
        return df["close"].ewm(span=period, adjust=False).mean()

    def calculate_wma(
        self, df: pd.DataFrame, period: int = 20
    ) -> pd.Series:
        """
        Weighted Moving Average.

        Linearly weighted moving average where recent prices carry more weight.

        Args:
            df: OHLCV DataFrame.
            period: Lookback window (default 20).

        Returns:
            Series of WMA values.
        """
        weights = np.arange(1, period + 1, dtype=float)
        return df["close"].rolling(window=period, min_periods=period).apply(
            lambda x: np.dot(x, weights) / weights.sum(), raw=True
        )

    def calculate_dema(
        self, df: pd.DataFrame, period: int = 20
    ) -> pd.Series:
        """
        Double Exponential Moving Average.

        DEMA = 2 * EMA - EMA(EMA), reducing lag.

        Args:
            df: OHLCV DataFrame.
            period: Span parameter (default 20).

        Returns:
            Series of DEMA values.
        """
        ema1 = df["close"].ewm(span=period, adjust=False).mean()
        ema2 = ema1.ewm(span=period, adjust=False).mean()
        return 2 * ema1 - ema2

    def calculate_tema(
        self, df: pd.DataFrame, period: int = 20
    ) -> pd.Series:
        """
        Triple Exponential Moving Average.

        TEMAm further reduces lag compared to DEMA.

        Args:
            df: OHLCV DataFrame.
            period: Span parameter (default 20).

        Returns:
            Series of TEMA values.
        """
        ema1 = df["close"].ewm(span=period, adjust=False).mean()
        ema2 = ema1.ewm(span=period, adjust=False).mean()
        ema3 = ema2.ewm(span=period, adjust=False).mean()
        return 3 * (ema1 - ema2) + ema3

    def calculate_macd(
        self,
        df: pd.DataFrame,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
    ) -> pd.DataFrame:
        """
        Moving Average Convergence Divergence.

        Computes MACD line, signal line, and histogram.

        Args:
            df: OHLCV DataFrame.
            fast_period: Fast EMA period (default 12).
            slow_period: Slow EMA period (default 26).
            signal_period: Signal EMA period (default 9).

        Returns:
            DataFrame with columns macd, signal, histogram.
        """
        fast_ema = df["close"].ewm(span=fast_period, adjust=False).mean()
        slow_ema = df["close"].ewm(span=slow_period, adjust=False).mean()
        macd_line = fast_ema - slow_ema
        signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
        histogram = macd_line - signal_line
        return pd.DataFrame(
            {"macd": macd_line, "signal": signal_line, "histogram": histogram},
            index=df.index,
        )

    def calculate_adx(
        self, df: pd.DataFrame, period: int = 14
    ) -> pd.DataFrame:
        """
        Average Directional Index with +DI and -DI.

        Measures trend strength regardless of direction.

        Args:
            df: OHLCV DataFrame.
            period: Lookback window (default 14).

        Returns:
            DataFrame with columns adx, plus_di, minus_di.
        """
        high = df["high"]
        low = df["low"]
        close = df["close"]

        # True range
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # Directional movement
        up_move = high - high.shift(1)
        down_move = low.shift(1) - low

        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

        plus_dm = pd.Series(plus_dm, index=df.index)
        minus_dm = pd.Series(minus_dm, index=df.index)

        atr = tr.ewm(span=period, adjust=False).mean()
        plus_di = 100 * (plus_dm.ewm(span=period, adjust=False).mean() / atr)
        minus_di = 100 * (minus_dm.ewm(span=period, adjust=False).mean() / atr)

        dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan))
        adx = dx.ewm(span=period, adjust=False).mean()

        return pd.DataFrame(
            {"adx": adx, "plus_di": plus_di, "minus_di": minus_di},
            index=df.index,
        )

    def calculate_ichimoku(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Ichimoku Cloud.

        Computes Tenkan-sen, Kijun-sen, Senkou Span A/B, and Chikou Span.

        Args:
            df: OHLCV DataFrame.

        Returns:
            DataFrame with Ichimoku components.
        """
        high = df["high"]
        low = df["low"]
        close = df["close"]

        def _midpoint(series: pd.Series, period: int) -> pd.Series:
            return (series.rolling(window=period, min_periods=period).max() +
                    series.rolling(window=period, min_periods=period).min()) / 2.0

        tenkan = _midpoint(high, 9)
        kijun = _midpoint(high, 26)
        senkou_a = ((tenkan + kijun) / 2.0).shift(26)
        senkou_b = _midpoint(high, 52).shift(26)
        chikou = close.shift(-26)

        return pd.DataFrame(
            {
                "tenkan": tenkan,
                "kijun": kijun,
                "senkou_a": senkou_a,
                "senkou_b": senkou_b,
                "chikou": chikou,
            },
            index=df.index,
        )

    def calculate_parabolic_sar(
        self,
        df: pd.DataFrame,
        step: float = 0.02,
        max_step: float = 0.20,
    ) -> pd.Series:
        """
        Parabolic SAR (Stop and Reverse).

        Trailing stop that follows price, used to identify trend direction.

        Args:
            df: OHLCV DataFrame.
            step: Acceleration factor increment (default 0.02).
            max_step: Maximum acceleration factor (default 0.20).

        Returns:
            Series of SAR values.
        """
        high = df["high"].values.astype(float)
        low = df["low"].values.astype(float)
        close = df["close"].values.astype(float)
        n = len(df)

        sar = np.full(n, np.nan)
        if n < 2:
            return pd.Series(sar, index=df.index)

        # Initialize
        is_long = close[1] > close[0]
        af = step
        if is_long:
            sar[1] = low[0]
            ep = high[1]
        else:
            sar[1] = high[0]
            ep = low[1]

        for i in range(2, n):
            prev_sar = sar[i - 1]

            if is_long:
                new_sar = prev_sar + af * (ep - prev_sar)
                new_sar = min(new_sar, low[i - 1], low[i - 2] if i >= 2 else low[i - 1])

                if low[i] < new_sar:
                    is_long = False
                    sar[i] = ep
                    af = step
                    ep = low[i]
                else:
                    sar[i] = new_sar
                    if high[i] > ep:
                        ep = high[i]
                        af = min(af + step, max_step)
            else:
                new_sar = prev_sar + af * (ep - prev_sar)
                new_sar = max(new_sar, high[i - 1], high[i - 2] if i >= 2 else high[i - 1])

                if high[i] > new_sar:
                    is_long = True
                    sar[i] = ep
                    af = step
                    ep = high[i]
                else:
                    sar[i] = new_sar
                    if low[i] < ep:
                        ep = low[i]
                        af = min(af + step, max_step)

        return pd.Series(sar, index=df.index, name="parabolic_sar")

    def calculate_supertrend(
        self,
        df: pd.DataFrame,
        period: int = 10,
        multiplier: float = 3.0,
    ) -> pd.DataFrame:
        """
        Supertrend indicator.

        A trend-following indicator based on ATR.

        Args:
            df: OHLCV DataFrame.
            period: ATR period (default 10).
            multiplier: ATR multiplier for bands (default 3.0).

        Returns:
            DataFrame with columns supertrend, direction.
        """
        atr = self.calculate_atr(df, period)
        hl2 = (df["high"] + df["low"]) / 2.0

        upper_band = hl2 + multiplier * atr
        lower_band = hl2 - multiplier * atr

        n = len(df)
        supertrend = np.full(n, np.nan)
        direction = np.full(n, np.nan)  # 1 = up, -1 = down

        if n < 2:
            return pd.DataFrame(
                {"supertrend": supertrend, "direction": direction}, index=df.index
            )

        # Initialize first valid direction based on close vs upper/lower
        close = df["close"].values
        supertrend[0] = 0.0
        direction[0] = 1.0

        for i in range(1, n):
            # Adjust bands: lower can only rise, upper can only fall
            if pd.notna(lower_band.iloc[i]):
                prev_lower = lower_band.iloc[i - 1] if pd.notna(lower_band.iloc[i - 1]) else lower_band.iloc[i]
                lower_band.iloc[i] = (
                    lower_band.iloc[i]
                    if close[i - 1] > prev_lower
                    else max(lower_band.iloc[i], prev_lower)
                )

            if pd.notna(upper_band.iloc[i]):
                prev_upper = upper_band.iloc[i - 1] if pd.notna(upper_band.iloc[i - 1]) else upper_band.iloc[i]
                upper_band.iloc[i] = (
                    upper_band.iloc[i]
                    if close[i - 1] < prev_upper
                    else min(upper_band.iloc[i], prev_upper)
                )

            if direction[i - 1] == 1.0:
                if close[i] < lower_band.iloc[i]:
                    direction[i] = -1.0
                    supertrend[i] = upper_band.iloc[i]
                else:
                    direction[i] = 1.0
                    supertrend[i] = lower_band.iloc[i]
            else:
                if close[i] > upper_band.iloc[i]:
                    direction[i] = 1.0
                    supertrend[i] = lower_band.iloc[i]
                else:
                    direction[i] = -1.0
                    supertrend[i] = upper_band.iloc[i]

        return pd.DataFrame(
            {"supertrend": supertrend, "direction": direction}, index=df.index
        )

    def calculate_aroon(
        self, df: pd.DataFrame, period: int = 25
    ) -> pd.DataFrame:
        """
        Aroon Up/Down oscillator.

        Measures time since the highest high and lowest low.

        Args:
            df: OHLCV DataFrame.
            period: Lookback window (default 25).

        Returns:
            DataFrame with columns aroon_up, aroon_down.
        """
        n = len(df)
        aroon_up = np.full(n, np.nan)
        aroon_down = np.full(n, np.nan)

        high_vals = df["high"].values
        low_vals = df["low"].values

        for i in range(period, n):
            window_high = high_vals[i - period: i + 1]
            window_low = low_vals[i - period: i + 1]
            days_since_high = period - np.argmax(window_high)
            days_since_low = period - np.argmin(window_low)
            aroon_up[i] = ((period - days_since_high) / period) * 100.0
            aroon_down[i] = ((period - days_since_low) / period) * 100.0

        return pd.DataFrame(
            {"aroon_up": aroon_up, "aroon_down": aroon_down},
            index=df.index,
        )

    def calculate_linear_regression(
        self, df: pd.DataFrame, period: int = 14
    ) -> pd.DataFrame:
        """
        Linear Regression (Least Squares Moving Average).

        Fits a straight line to the close prices over the window.

        Args:
            df: OHLCV DataFrame.
            period: Regression window (default 14).

        Returns:
            DataFrame with columns lr_value, lr_slope.
        """
        close = df["close"]

        def _lr_slope(values: np.ndarray) -> float:
            x = np.arange(len(values), dtype=float)
            y = values
            slope, _ = np.polyfit(x, y, 1)
            return slope

        def _lr_end(values: np.ndarray) -> float:
            x = np.arange(len(values), dtype=float)
            y = values
            coeffs = np.polyfit(x, y, 1)
            return coeffs[0] * (len(values) - 1) + coeffs[1]

        lr_value = close.rolling(window=period, min_periods=period).apply(
            _lr_end, raw=True
        )
        lr_slope = close.rolling(window=period, min_periods=period).apply(
            _lr_slope, raw=True
        )

        return pd.DataFrame(
            {"lr_value": lr_value, "lr_slope": lr_slope}, index=df.index
        )

    # ================================================================== #
    #  MOMENTUM INDICATORS                                                #
    # ================================================================== #

    def calculate_rsi(
        self, df: pd.DataFrame, period: int = 14
    ) -> pd.Series:
        """
        Relative Strength Index.

        Momentum oscillator (0-100) comparing average gains to average losses.

        Args:
            df: OHLCV DataFrame.
            period: Lookback window (default 14).

        Returns:
            Series of RSI values.
        """
        delta = df["close"].diff()
        gain = delta.clip(lower=0)
        loss = (-delta).clip(lower=0)

        avg_gain = gain.ewm(span=period, adjust=False).mean()
        avg_loss = loss.ewm(span=period, adjust=False).mean()

        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100.0 - (100.0 / (1.0 + rs))
        return rsi

    def calculate_stochastic(
        self, df: pd.DataFrame, k_period: int = 14, d_period: int = 3
    ) -> pd.DataFrame:
        """
        Stochastic Oscillator (%K and %D).

        Compares the close to the high-low range over *k_period*.

        Args:
            df: OHLCV DataFrame.
            k_period: %K lookback (default 14).
            d_period: %D smoothing (default 3).

        Returns:
            DataFrame with columns percent_k, percent_d.
        """
        low_min = df["low"].rolling(window=k_period, min_periods=k_period).min()
        high_max = df["high"].rolling(window=k_period, min_periods=k_period).max()

        denominator = high_max - low_min
        percent_k = np.where(denominator != 0, 100 * (df["close"] - low_min) / denominator, 50.0)
        percent_k = pd.Series(percent_k, index=df.index)
        percent_d = percent_k.rolling(window=d_period, min_periods=d_period).mean()

        return pd.DataFrame(
            {"percent_k": percent_k, "percent_d": percent_d}, index=df.index
        )

    def calculate_williams_r(
        self, df: pd.DataFrame, period: int = 14
    ) -> pd.Series:
        """
        Williams %R.

        Momentum indicator measuring overbought/oversold levels (-100 to 0).

        Args:
            df: OHLCV DataFrame.
            period: Lookback window (default 14).

        Returns:
            Series of Williams %R values.
        """
        high_max = df["high"].rolling(window=period, min_periods=period).max()
        low_min = df["low"].rolling(window=period, min_periods=period).min()
        denom = high_max - low_min
        return pd.Series(
            np.where(denom != 0, -100 * (high_max - df["close"]) / denom, -50.0),
            index=df.index,
        )

    def calculate_cci(
        self, df: pd.DataFrame, period: int = 20
    ) -> pd.Series:
        """
        Commodity Channel Index.

        Measures deviation of typical price from its average.

        Args:
            df: OHLCV DataFrame.
            period: Lookback window (default 20).

        Returns:
            Series of CCI values.
        """
        typical_price = (df["high"] + df["low"] + df["close"]) / 3.0
        sma_tp = typical_price.rolling(window=period, min_periods=period).mean()
        mad = typical_price.rolling(window=period, min_periods=period).apply(
            lambda x: np.abs(x - x.mean()).mean(), raw=True
        )
        return (typical_price - sma_tp) / (0.015 * mad.replace(0, np.nan))

    def calculate_roc(
        self, df: pd.DataFrame, period: int = 12
    ) -> pd.Series:
        """
        Rate of Change.

        Percentage change in close price over *period* bars.

        Args:
            df: OHLCV DataFrame.
            period: Lookback window (default 12).

        Returns:
            Series of ROC values.
        """
        return df["close"].pct_change(periods=period) * 100.0

    def calculate_momentum(
        self, df: pd.DataFrame, period: int = 10
    ) -> pd.Series:
        """
        Momentum.

        Close price minus the close *period* bars ago.

        Args:
            df: OHLCV DataFrame.
            period: Lookback window (default 10).

        Returns:
            Series of momentum values.
        """
        return df["close"] - df["close"].shift(period)

    def calculate_tsi(
        self,
        df: pd.DataFrame,
        fast_period: int = 13,
        slow_period: int = 25,
    ) -> pd.Series:
        """
        True Strength Index.

        Double-smoothed momentum divided by double-smoothed absolute momentum.

        Args:
            df: OHLCV DataFrame.
            fast_period: First smoothing (default 13).
            slow_period: Second smoothing (default 25).

        Returns:
            Series of TSI values.
        """
        momentum = df["close"].diff()
        abs_momentum = momentum.abs()

        smoothed_momentum = momentum.ewm(span=slow_period, adjust=False).mean()
        smoothed_abs = abs_momentum.ewm(span=slow_period, adjust=False).mean()

        double_smoothed_momentum = smoothed_momentum.ewm(span=fast_period, adjust=False).mean()
        double_smoothed_abs = smoothed_abs.ewm(span=fast_period, adjust=False).mean()

        return 100.0 * (double_smoothed_momentum / double_smoothed_abs.replace(0, np.nan))

    def calculate_ultimate_oscillator(
        self,
        df: pd.DataFrame,
        period1: int = 7,
        period2: int = 14,
        period3: int = 28,
    ) -> pd.Series:
        """
        Ultimate Oscillator.

        Weighted average of three buying-pressure oscillators.

        Args:
            df: OHLCV DataFrame.
            period1: Short period (default 7).
            period2: Medium period (default 14).
            period3: Long period (default 28).

        Returns:
            Series of Ultimate Oscillator values.
        """
        low = df["low"]
        high = df["high"]
        close = df["close"]

        # True range
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # Buying pressure
        bp = close - pd.concat(
            [low, close.shift(1)], axis=1
        ).min(axis=1)

        avg1 = bp.rolling(window=period1, min_periods=period1).sum() / tr.rolling(window=period1, min_periods=period1).sum().replace(0, np.nan)
        avg2 = bp.rolling(window=period2, min_periods=period2).sum() / tr.rolling(window=period2, min_periods=period2).sum().replace(0, np.nan)
        avg3 = bp.rolling(window=period3, min_periods=period3).sum() / tr.rolling(window=period3, min_periods=period3).sum().replace(0, np.nan)

        uo = 100 * (
            (4 * avg1 + 2 * avg2 + avg3) / (4 + 2 + 1)
        )
        return uo

    def calculate_roc_volume(
        self, df: pd.DataFrame, period: int = 12
    ) -> pd.Series:
        """
        Rate of Change of Volume.

        Percentage change in volume over *period* bars.

        Args:
            df: OHLCV DataFrame.
            period: Lookback window (default 12).

        Returns:
            Series of volume ROC values.
        """
        return df["volume"].pct_change(periods=period) * 100.0

    def calculate_mfi(
        self, df: pd.DataFrame, period: int = 14
    ) -> pd.Series:
        """
        Money Flow Index.

        Volume-weighted RSI, oscillates between 0 and 100.

        Args:
            df: OHLCV DataFrame.
            period: Lookback window (default 14).

        Returns:
            Series of MFI values.
        """
        typical_price = (df["high"] + df["low"] + df["close"]) / 3.0
        money_flow = typical_price * df["volume"]

        positive_flow = np.where(typical_price > typical_price.shift(1), money_flow, 0.0)
        negative_flow = np.where(typical_price < typical_price.shift(1), money_flow, 0.0)

        pos_sum = pd.Series(positive_flow, index=df.index).rolling(window=period, min_periods=period).sum()
        neg_sum = pd.Series(negative_flow, index=df.index).rolling(window=period, min_periods=period).sum()

        mfi_ratio = pos_sum / neg_sum.replace(0, np.nan)
        return 100.0 - (100.0 / (1.0 + mfi_ratio))

    def calculate_stochastic_rsi(
        self, df: pd.DataFrame, rsi_period: int = 14, stoch_period: int = 14
    ) -> pd.DataFrame:
        """
        Stochastic RSI.

        Applies the Stochastic formula to RSI values.

        Args:
            df: OHLCV DataFrame.
            rsi_period: Period for RSI calculation (default 14).
            stoch_period: Period for Stochastic on RSI (default 14).

        Returns:
            DataFrame with columns stoch_rsi_k, stoch_rsi_d.
        """
        rsi = self.calculate_rsi(df, rsi_period)

        rsi_min = rsi.rolling(window=stoch_period, min_periods=stoch_period).min()
        rsi_max = rsi.rolling(window=stoch_period, min_periods=stoch_period).max()
        denom = rsi_max - rsi_min

        stoch_rsi = np.where(denom != 0, (rsi - rsi_min) / denom * 100.0, 50.0)
        stoch_rsi = pd.Series(stoch_rsi, index=df.index)
        stoch_rsi_d = stoch_rsi.rolling(window=3, min_periods=3).mean()

        return pd.DataFrame(
            {"stoch_rsi_k": stoch_rsi, "stoch_rsi_d": stoch_rsi_d}, index=df.index
        )

    def calculate_awesome_oscillator(
        self, df: pd.DataFrame
    ) -> pd.Series:
        """
        Awesome Oscillator.

        Difference between 34-period and 5-period simple moving averages
        of the median price.

        Args:
            df: OHLCV DataFrame.

        Returns:
            Series of Awesome Oscillator values.
        """
        median_price = (df["high"] + df["low"]) / 2.0
        sma5 = median_price.rolling(window=5, min_periods=5).mean()
        sma34 = median_price.rolling(window=34, min_periods=34).mean()
        return sma5 - sma34

    # ================================================================== #
    #  VOLATILITY INDICATORS                                              #
    # ================================================================== #

    def calculate_bollinger_bands(
        self,
        df: pd.DataFrame,
        period: int = 20,
        num_std: float = 2.0,
    ) -> pd.DataFrame:
        """
        Bollinger Bands.

        SMA envelope with bands at *num_std* standard deviations.

        Args:
            df: OHLCV DataFrame.
            period: SMA period (default 20).
            num_std: Standard deviation multiplier (default 2.0).

        Returns:
            DataFrame with columns upper, middle, lower.
        """
        middle = df["close"].rolling(window=period, min_periods=period).mean()
        std = df["close"].rolling(window=period, min_periods=period).std()
        upper = middle + num_std * std
        lower = middle - num_std * std
        return pd.DataFrame(
            {"upper": upper, "middle": middle, "lower": lower}, index=df.index
        )

    def calculate_keltner_channels(
        self,
        df: pd.DataFrame,
        ema_period: int = 20,
        atr_period: int = 10,
        multiplier: float = 2.0,
    ) -> pd.DataFrame:
        """
        Keltner Channels.

        EMA-based channels using ATR for band width.

        Args:
            df: OHLCV DataFrame.
            ema_period: EMA period (default 20).
            atr_period: ATR period (default 10).
            multiplier: ATR multiplier (default 2.0).

        Returns:
            DataFrame with columns upper, middle, lower.
        """
        middle = df["close"].ewm(span=ema_period, adjust=False).mean()
        atr = self.calculate_atr(df, atr_period)
        upper = middle + multiplier * atr
        lower = middle - multiplier * atr
        return pd.DataFrame(
            {"upper": upper, "middle": middle, "lower": lower}, index=df.index
        )

    def calculate_donchian_channels(
        self, df: pd.DataFrame, period: int = 20
    ) -> pd.DataFrame:
        """
        Donchian Channels.

        Highest high and lowest low over *period* bars.

        Args:
            df: OHLCV DataFrame.
            period: Lookback window (default 20).

        Returns:
            DataFrame with columns upper, middle, lower.
        """
        upper = df["high"].rolling(window=period, min_periods=period).max()
        lower = df["low"].rolling(window=period, min_periods=period).min()
        middle = (upper + lower) / 2.0
        return pd.DataFrame(
            {"upper": upper, "middle": middle, "lower": lower}, index=df.index
        )

    def calculate_atr(
        self, df: pd.DataFrame, period: int = 14
    ) -> pd.Series:
        """
        Average True Range.

        Measures volatility by averaging the true range.

        Args:
            df: OHLCV DataFrame.
            period: Lookback window (default 14).

        Returns:
            Series of ATR values.
        """
        tr = self.calculate_true_range(df)
        return tr.ewm(span=period, adjust=False).mean()

    def calculate_std_dev(
        self, df: pd.DataFrame, period: int = 20
    ) -> pd.Series:
        """
        Rolling Standard Deviation of close prices.

        Args:
            df: OHLCV DataFrame.
            period: Lookback window (default 20).

        Returns:
            Series of standard deviation values.
        """
        return df["close"].rolling(window=period, min_periods=period).std()

    def calculate_true_range(self, df: pd.DataFrame) -> pd.Series:
        """
        True Range.

        Largest of: high-low, |high-prev_close|, |low-prev_close|.

        Args:
            df: OHLCV DataFrame.

        Returns:
            Series of true range values.
        """
        tr1 = df["high"] - df["low"]
        tr2 = (df["high"] - df["close"].shift(1)).abs()
        tr3 = (df["low"] - df["close"].shift(1)).abs()
        return pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    def calculate_chaikin_volatility(
        self, df: pd.DataFrame, ema_period: int = 10, roc_period: int = 10
    ) -> pd.Series:
        """
        Chaikin Volatility.

        Rate of change of the high-low spread EMA.

        Args:
            df: OHLCV DataFrame.
            ema_period: EMA period for spread (default 10).
            roc_period: ROC period (default 10).

        Returns:
            Series of Chaikin Volatility values.
        """
        spread = df["high"] - df["low"]
        ema_spread = spread.ewm(span=ema_period, adjust=False).mean()
        return ((ema_spread - ema_spread.shift(roc_period)) / ema_spread.shift(roc_period).replace(0, np.nan)) * 100.0

    def calculate_bollinger_bandwidth(
        self,
        df: pd.DataFrame,
        period: int = 20,
        num_std: float = 2.0,
    ) -> pd.Series:
        """
        Bollinger Band Width.

        Normalized width of the Bollinger Bands.

        Args:
            df: OHLCV DataFrame.
            period: SMA period (default 20).
            num_std: Standard deviation multiplier (default 2.0).

        Returns:
            Series of bandwidth values.
        """
        bb = self.calculate_bollinger_bands(df, period, num_std)
        return ((bb["upper"] - bb["lower"]) / bb["middle"].replace(0, np.nan)) * 100.0

    def calculate_bollinger_pct_b(
        self,
        df: pd.DataFrame,
        period: int = 20,
        num_std: float = 2.0,
    ) -> pd.Series:
        """
        Bollinger Band %B.

        Where the close sits relative to the Bollinger Bands (0 = lower, 1 = upper).

        Args:
            df: OHLCV DataFrame.
            period: SMA period (default 20).
            num_std: Standard deviation multiplier (default 2.0).

        Returns:
            Series of %B values.
        """
        bb = self.calculate_bollinger_bands(df, period, num_std)
        denom = bb["upper"] - bb["lower"]
        return (df["close"] - bb["lower"]) / denom.replace(0, np.nan)

    # ================================================================== #
    #  VOLUME INDICATORS                                                  #
    # ================================================================== #

    def calculate_obv(self, df: pd.DataFrame) -> pd.Series:
        """
        On Balance Volume.

        Cumulative volume that adds on up-days and subtracts on down-days.

        Args:
            df: OHLCV DataFrame.

        Returns:
            Series of OBV values.
        """
        direction = np.sign(df["close"].diff())
        direction.iloc[0] = 0
        return (direction * df["volume"]).cumsum()

    def calculate_vwap(self, df: pd.DataFrame) -> pd.Series:
        """
        Volume Weighted Average Price.

        Cumulative typical price weighted by volume.

        Args:
            df: OHLCV DataFrame.

        Returns:
            Series of VWAP values.
        """
        typical_price = (df["high"] + df["low"] + df["close"]) / 3.0
        return (typical_price * df["volume"]).cumsum() / df["volume"].cumsum().replace(0, np.nan)

    def calculate_adl(self, df: pd.DataFrame) -> pd.Series:
        """
        Accumulation/Distribution Line.

        Volume flow indicator based on the close location within the bar's range.

        Args:
            df: OHLCV DataFrame.

        Returns:
            Series of ADL values.
        """
        high_low_range = df["high"] - df["low"]
        clv = np.where(
            high_low_range != 0,
            ((df["close"] - df["low"]) - (df["high"] - df["close"])) / high_low_range,
            0.0,
        )
        adl = (pd.Series(clv, index=df.index) * df["volume"]).cumsum()
        return adl

    def calculate_cmf(
        self, df: pd.DataFrame, period: int = 20
    ) -> pd.Series:
        """
        Chaikin Money Flow.

        Rolling average of the money flow multiplier times volume.

        Args:
            df: OHLCV DataFrame.
            period: Lookback window (default 20).

        Returns:
            Series of CMF values.
        """
        high_low_range = df["high"] - df["low"]
        mfm = np.where(
            high_low_range != 0,
            ((df["close"] - df["low"]) - (df["high"] - df["close"])) / high_low_range,
            0.0,
        )
        mfv = pd.Series(mfm, index=df.index) * df["volume"]
        return mfv.rolling(window=period, min_periods=period).sum() / df["volume"].rolling(window=period, min_periods=period).sum().replace(0, np.nan)

    def calculate_force_index(
        self, df: pd.DataFrame, period: int = 13
    ) -> pd.Series:
        """
        Force Index.

        Close change multiplied by volume, smoothed by EMA.

        Args:
            df: OHLCV DataFrame.
            period: EMA smoothing period (default 13).

        Returns:
            Series of Force Index values.
        """
        fi = df["close"].diff() * df["volume"]
        return fi.ewm(span=period, adjust=False).mean()

    def calculate_vpt(self, df: pd.DataFrame) -> pd.Series:
        """
        Volume Price Trend.

        Cumulative volume adjusted by the percentage price change.

        Args:
            df: OHLCV DataFrame.

        Returns:
            Series of VPT values.
        """
        pct_change = df["close"].pct_change().fillna(0)
        return (pct_change * df["volume"]).cumsum()

    def calculate_ease_of_movement(
        self, df: pd.DataFrame, period: int = 14
    ) -> pd.Series:
        """
        Ease of Movement.

        Relates price range to volume, showing how easily price moves.

        Args:
            df: OHLCV DataFrame.
            period: Smoothing period (default 14).

        Returns:
            Series of EMV values.
        """
        high = df["high"]
        low = df["low"]
        volume = df["volume"]

        distance = ((high + low) / 2.0) - ((high.shift(1) + low.shift(1)) / 2.0)
        box_ratio = (volume / 1_000_000) / (high - low).replace(0, np.nan)
        emv = distance / box_ratio
        return emv.rolling(window=period, min_periods=period).mean()

    def calculate_volume_oscillator(
        self,
        df: pd.DataFrame,
        fast_period: int = 5,
        slow_period: int = 10,
    ) -> pd.Series:
        """
        Volume Oscillator.

        Difference between fast and slow volume SMAs.

        Args:
            df: OHLCV DataFrame.
            fast_period: Fast SMA period (default 5).
            slow_period: Slow SMA period (default 10).

        Returns:
            Series of Volume Oscillator values.
        """
        fast_sma = df["volume"].rolling(window=fast_period, min_periods=fast_period).mean()
        slow_sma = df["volume"].rolling(window=slow_period, min_periods=slow_period).mean()
        return ((fast_sma - slow_sma) / slow_sma.replace(0, np.nan)) * 100.0

    def calculate_nvi(self, df: pd.DataFrame) -> pd.Series:
        """
        Negative Volume Index.

        Cumulative index that only changes on days when volume decreases.

        Args:
            df: OHLCV DataFrame.

        Returns:
            Series of NVI values.
        """
        close = df["close"]
        volume = df["volume"]

        pct_change = close.pct_change().fillna(0)
        volume_decreased = volume < volume.shift(1)

        nvi = pd.Series(np.where(volume_decreased, pct_change, 0.0), index=df.index)
        nvi.iloc[0] = 1000.0  # Starting base
        return nvi.cumsum() + 1000.0

    def calculate_pvi(self, df: pd.DataFrame) -> pd.Series:
        """
        Positive Volume Index.

        Cumulative index that only changes on days when volume increases.

        Args:
            df: OHLCV DataFrame.

        Returns:
            Series of PVI values.
        """
        close = df["close"]
        volume = df["volume"]

        pct_change = close.pct_change().fillna(0)
        volume_increased = volume > volume.shift(1)

        pvi = pd.Series(np.where(volume_increased, pct_change, 0.0), index=df.index)
        pvi.iloc[0] = 1000.0
        return pvi.cumsum() + 1000.0

    # ================================================================== #
    #  OTHER INDICATORS                                                   #
    # ================================================================== #

    def calculate_fibonacci_retracement(self, df: pd.DataFrame) -> Dict[str, Optional[float]]:
        """
        Fibonacci Retracement Levels.

        Computes key Fibonacci levels based on the high and low of the
        entire data window.

        Args:
            df: OHLCV DataFrame.

        Returns:
            Dictionary of level name to price value.
        """
        high = float(df["high"].max())
        low = float(df["low"].min())
        diff = high - low

        return {
            "high": self._safe_float(high),
            "level_0.0": self._safe_float(high),
            "level_23.6": self._safe_float(high - 0.236 * diff),
            "level_38.2": self._safe_float(high - 0.382 * diff),
            "level_50.0": self._safe_float(high - 0.5 * diff),
            "level_61.8": self._safe_float(high - 0.618 * diff),
            "level_78.6": self._safe_float(high - 0.786 * diff),
            "low": self._safe_float(low),
        }

    def calculate_pivot_points(self, df: pd.DataFrame) -> Dict[str, Optional[float]]:
        """
        Standard Pivot Points.

        Calculates pivot, support (S1-S3), and resistance (R1-R3) levels
        based on the most recent bar's OHLC.

        Args:
            df: OHLCV DataFrame.

        Returns:
            Dictionary of level name to price value.
        """
        if df.empty:
            return {k: None for k in ["pivot", "r1", "r2", "r3", "s1", "s2", "s3"]}

        h = float(df["high"].iloc[-1])
        l = float(df["low"].iloc[-1])
        c = float(df["close"].iloc[-1])

        pivot = (h + l + c) / 3.0
        r1 = 2 * pivot - l
        s1 = 2 * pivot - h
        r2 = pivot + (h - l)
        s2 = pivot - (h - l)
        r3 = h + 2 * (pivot - l)
        s3 = l - 2 * (h - pivot)

        return {
            "pivot": self._safe_float(pivot),
            "r1": self._safe_float(r1),
            "r2": self._safe_float(r2),
            "r3": self._safe_float(r3),
            "s1": self._safe_float(s1),
            "s2": self._safe_float(s2),
            "s3": self._safe_float(s3),
        }

    def calculate_vwap_bands(
        self,
        df: pd.DataFrame,
        num_std: float = 2.0,
    ) -> pd.DataFrame:
        """
        VWAP Bands.

        VWAP with upper and lower bands at *num_std* standard deviations
        of the typical price.

        Args:
            df: OHLCV DataFrame.
            num_std: Standard deviation multiplier (default 2.0).

        Returns:
            DataFrame with columns upper, middle, lower.
        """
        typical_price = (df["high"] + df["low"] + df["close"]) / 3.0
        cum_vol = df["volume"].cumsum()
        cum_tp_vol = (typical_price * df["volume"]).cumsum()
        vwap = cum_tp_vol / cum_vol.replace(0, np.nan)

        cum_tp_sq_vol = (typical_price ** 2 * df["volume"]).cumsum()
        variance = (cum_tp_sq_vol / cum_vol.replace(0, np.nan)) - vwap ** 2
        std = np.sqrt(variance.clip(lower=0))

        upper = vwap + num_std * std
        lower = vwap - num_std * std

        return pd.DataFrame(
            {"upper": upper, "middle": vwap, "lower": lower}, index=df.index
        )

    def calculate_heikin_ashi(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Heikin-Ashi Candlesticks.

        Smoothed OHLC using average-based calculations for trend identification.

        Args:
            df: OHLCV DataFrame.

        Returns:
            DataFrame with columns ha_open, ha_high, ha_low, ha_close.
        """
        close_vals = df["close"].values.astype(float)
        open_vals = df["open"].values.astype(float)
        high_vals = df["high"].values.astype(float)
        low_vals = df["low"].values.astype(float)

        n = len(df)
        ha_close = np.full(n, np.nan)
        ha_open = np.full(n, np.nan)
        ha_high = np.full(n, np.nan)
        ha_low = np.full(n, np.nan)

        for i in range(n):
            ha_close[i] = (open_vals[i] + high_vals[i] + low_vals[i] + close_vals[i]) / 4.0
            if i == 0:
                ha_open[i] = (open_vals[i] + close_vals[i]) / 2.0
            else:
                ha_open[i] = (ha_open[i - 1] + ha_close[i - 1]) / 2.0
            ha_high[i] = max(high_vals[i], ha_open[i], ha_close[i])
            ha_low[i] = min(low_vals[i], ha_open[i], ha_close[i])

        return pd.DataFrame(
            {
                "ha_open": ha_open,
                "ha_high": ha_high,
                "ha_low": ha_low,
                "ha_close": ha_close,
            },
            index=df.index,
        )

    # ================================================================== #
    #  SIGNAL GENERATION (for summary endpoint)                           #
    # ================================================================== #

    def generate_signal(
        self, indicator_name: str, indicator_result: Dict[str, Any]
    ) -> Optional[str]:
        """
        Generate a simple bullish/bearish/neutral signal from indicator values.

        Uses standard threshold rules for each indicator type.

        Args:
            indicator_name: Name of the indicator.
            indicator_result: Computed indicator values dict.

        Returns:
            "bullish", "bearish", or "neutral".
        """
        try:
            latest = self.get_latest_value(indicator_result)
            if latest is None:
                return "neutral"

            if indicator_name == "rsi":
                if latest > 70:
                    return "bearish"
                elif latest < 30:
                    return "bullish"
                return "neutral"

            if indicator_name == "macd":
                hist = indicator_result.get("histogram", [])
                if hist:
                    latest_hist = None
                    for v in reversed(hist):
                        if v is not None:
                            latest_hist = v
                            break
                    if latest_hist is not None:
                        return "bullish" if latest_hist > 0 else "bearish"
                return "neutral"

            if indicator_name == "stochastic":
                k = indicator_result.get("percent_k", [])
                latest_k = None
                for v in reversed(k):
                    if v is not None:
                        latest_k = v
                        break
                if latest_k is not None:
                    if latest_k > 80:
                        return "bearish"
                    elif latest_k < 20:
                        return "bullish"
                return "neutral"

            if indicator_name == "williams_r":
                if latest < -80:
                    return "bullish"
                elif latest > -20:
                    return "bearish"
                return "neutral"

            if indicator_name == "cci":
                if latest > 100:
                    return "bearish"
                elif latest < -100:
                    return "bullish"
                return "neutral"

            if indicator_name == "adx":
                if latest > 25:
                    return "bullish"
                return "neutral"

            if indicator_name == "mfi":
                if latest > 80:
                    return "bearish"
                elif latest < 20:
                    return "bullish"
                return "neutral"

            return "neutral"

        except Exception as exc:
            logger.error(f"Error generating signal for {indicator_name}: {exc}")
            return "neutral"

    # ------------------------------------------------------------------ #
    #  Additional indicators (50+)                                        #
    # ------------------------------------------------------------------ #

    def calculate_hma(self, df: pd.DataFrame, period: int = 20) -> Dict[str, Any]:
        """
        Hull Moving Average (HMA).

        A smoother, more responsive moving average that reduces lag
        compared to SMA and EMA. Uses weighted moving averages with
        a square-root period adjustment.

        Args:
            df: OHLCV DataFrame.
            period: Lookback period (default 20).

        Returns:
            Dict with 'hma' key containing the HMA values.
        """
        self._validate_dataframe(df)
        close = df["close"]

        # HMA = WMA(2 * WMA(n/2) - WMA(n), sqrt(n))
        half_period = max(1, period // 2)
        sqrt_period = max(1, int(np.sqrt(period)))

        wma_half = self._compute_wma(close, half_period)
        wma_full = self._compute_wma(close, period)
        diff = 2 * wma_half - wma_full
        hma = self._compute_wma(diff, sqrt_period)

        latest = None
        clean = hma.dropna()
        if not clean.empty:
            latest = float(clean.iloc[-1])

        return {"hma": hma.tolist(), "latest": latest}

    def calculate_choppiness_index(
        self, df: pd.DataFrame, period: int = 14
    ) -> Dict[str, Any]:
        """
        Choppiness Index (CHOP).

        Measures the degree of trend vs. choppy (range-bound) market
        conditions. Values range from 0 to 100.
        - Above 61.8: Market is choppy / consolidating.
        - Below 38.2: Market is trending strongly.

        Args:
            df: OHLCV DataFrame.
            period: Lookback period (default 14).

        Returns:
            Dict with 'chop' key containing the index values.
        """
        self._validate_dataframe(df)
        high = df["high"]
        low = df["low"]
        close = df["close"]

        # True range
        tr = pd.concat(
            [high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()],
            axis=1,
        ).max(axis=1)

        # Sum of true ranges over period
        atr_sum = tr.rolling(window=period).sum()

        # Highest high and lowest low over period
        hh = high.rolling(window=period).max()
        ll = low.rolling(window=period).min()

        # Choppiness Index
        chop = 100 * np.log(atr_sum / (hh - ll)) / np.log(period)
        chop = chop.replace([np.inf, -np.inf], np.nan)

        latest = None
        clean = chop.dropna()
        if not clean.empty:
            latest = float(clean.iloc[-1])

        return {"choppiness_index": chop.tolist(), "latest": latest}

    def calculate_elder_ray(
        self, df: pd.DataFrame, ema_period: int = 13
    ) -> Dict[str, Any]:
        """
        Elder Ray Bull/Bear Power.

        Developed by Alexander Elder, measures the distance between
        price and an EMA to gauge buying/selling pressure.
        - Bull Power = High - EMA
        - Bear Power = Low - EMA

        Args:
            df: OHLCV DataFrame.
            ema_period: EMA period (default 13).

        Returns:
            Dict with 'bull_power' and 'bear_power' lists.
        """
        self._validate_dataframe(df)
        high = df["high"]
        low = df["low"]
        close = df["close"]

        ema = close.ewm(span=ema_period, adjust=False).mean()

        bull_power = high - ema
        bear_power = low - ema

        bull_latest = None
        bear_latest = None
        bull_clean = bull_power.dropna()
        bear_clean = bear_power.dropna()
        if not bull_clean.empty:
            bull_latest = float(bull_clean.iloc[-1])
        if not bear_clean.empty:
            bear_latest = float(bear_clean.iloc[-1])

        return {
            "bull_power": bull_power.tolist(),
            "bear_power": bear_power.tolist(),
            "bull_power_latest": bull_latest,
            "bear_power_latest": bear_latest,
        }

    def calculate_coppock_curve(
        self, df: pd.DataFrame, long_roc: int = 14, short_roc: int = 11,
        wma_period: int = 10,
    ) -> Dict[str, Any]:
        """
        Coppock Curve.

        A long-term momentum indicator designed to identify major
        market bottoms. When the curve crosses above zero from below,
        it generates a buy signal. Uses the sum of two rates of change
        smoothed with a WMA.

        Args:
            df: OHLCV DataFrame.
            long_roc: Long rate-of-change period (default 14).
            short_roc: Short rate-of-change period (default 11).
            wma_period: WMA smoothing period (default 10).

        Returns:
            Dict with 'coppock' key containing the curve values.
        """
        self._validate_dataframe(df)
        close = df["close"]

        roc_long = close.pct_change(periods=long_roc) * 100
        roc_short = close.pct_change(periods=short_roc) * 100
        roc_sum = roc_long + roc_short

        coppock = self._compute_wma(roc_sum, wma_period)

        latest = None
        clean = coppock.dropna()
        if not clean.empty:
            latest = float(clean.iloc[-1])

        return {"coppock": coppock.tolist(), "latest": latest}

    def calculate_vwap_std_bands(
        self, df: pd.DataFrame, num_std: float = 2.0
    ) -> Dict[str, Any]:
        """
        VWAP with Standard Deviation Bands.

        Computes the Volume-Weighted Average Price and overlays standard
        deviation bands for intraday mean-reversion and breakout analysis.

        Args:
            df: OHLCV DataFrame.
            num_std: Number of standard deviations for bands (default 2.0).

        Returns:
            Dict with 'vwap', 'upper_band', 'lower_band', 'bandwidth'.
        """
        self._validate_dataframe(df, require_volume=True)
        typical = (df["high"] + df["low"] + df["close"]) / 3.0
        vol = df["volume"].astype(float)

        cum_tp_vol = (typical * vol).cumsum()
        cum_vol = vol.cumsum()

        vwap = cum_tp_vol / cum_vol.replace(0, np.nan)
        deviation = ((typical - vwap) ** 2 * vol).cumsum()
        std = np.sqrt(deviation / cum_vol.replace(0, np.nan))

        upper = vwap + num_std * std
        lower = vwap - num_std * std
        bandwidth = ((upper - lower) / vwap.replace(0, np.nan)) * 100

        def _latest(series: pd.Series) -> Optional[float]:
            clean = series.dropna()
            return float(clean.iloc[-1]) if not clean.empty else None

        return {
            "vwap": vwap.tolist(),
            "upper_band": upper.tolist(),
            "lower_band": lower.tolist(),
            "bandwidth": bandwidth.tolist(),
            "vwap_latest": _latest(vwap),
            "upper_latest": _latest(upper),
            "lower_latest": _latest(lower),
        }

    def calculate_mass_index(
        self, df: pd.DataFrame, ema_period: int = 9, sum_period: int = 25
    ) -> Dict[str, Any]:
        """
        Mass Index.

        Detects trend reversals by measuring the narrowing and widening
        of the trading range between two EMAs. When the Mass Index
        rises above 27 and then falls below 26.5, a "reversal bulge"
        signals a potential price reversal.

        Args:
            df: OHLCV DataFrame.
            ema_period: EMA period for range calculation (default 9).
            sum_period: Summation period (default 25).

        Returns:
            Dict with 'mass_index' values.
        """
        self._validate_dataframe(df)
        high = df["high"]
        low = df["low"]

        price_range = high - low
        ema1 = price_range.ewm(span=ema_period, adjust=False).mean()
        ema2 = ema1.ewm(span=ema_period, adjust=False).mean()
        ratio = ema1 / ema2.replace(0, np.nan)
        mass = ratio.rolling(window=sum_period).sum()

        latest = None
        clean = mass.dropna()
        if not clean.empty:
            latest = float(clean.iloc[-1])

        return {"mass_index": mass.tolist(), "latest": latest}

    def calculate_connors_rsi(
        self, df: pd.DataFrame, rsi_period: int = 3,
        streak_period: int = 2, roc_period: int = 100,
    ) -> Dict[str, Any]:
        """
        Connors RSI (CRSI).

        A composite oscillator developed by Larry Connors combining
        three components:
        1. RSI of price (standard RSI)
        2. RSI of streak length (up/down day count)
        3. Percent rank of current return

        CRSI = (RSI + Streak RSI + Percent Rank) / 3
        Values < 20 suggest oversold; > 80 suggest overbought.

        Args:
            df: OHLCV DataFrame.
            rsi_period: Period for price RSI (default 3).
            streak_period: Period for streak RSI (default 2).
            roc_period: Lookback for percent rank (default 100).

        Returns:
            Dict with 'connors_rsi', 'price_rsi', 'streak_rsi', 'percent_rank'.
        """
        self._validate_dataframe(df)
        close = df["close"]

        # Component 1: Standard RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)
        avg_gain = gain.ewm(com=rsi_period - 1, adjust=False).mean()
        avg_loss = loss.ewm(com=rsi_period - 1, adjust=False).mean()
        rs = avg_gain / avg_loss.replace(0, 1e-10)
        price_rsi = 100 - (100 / (1 + rs))

        # Component 2: RSI of streak
        direction = np.sign(close.diff())
        streak = pd.Series(0.0, index=close.index)
        for i in range(1, len(close)):
            if direction.iloc[i] == direction.iloc[i - 1] and direction.iloc[i] != 0:
                streak.iloc[i] = streak.iloc[i - 1] + direction.iloc[i]
            else:
                streak.iloc[i] = direction.iloc[i]

        streak_gain = streak.where(streak > 0, 0.0)
        streak_loss = (-streak).where(streak < 0, 0.0)
        sg_avg = streak_gain.ewm(com=streak_period - 1, adjust=False).mean()
        sl_avg = streak_loss.ewm(com=streak_period - 1, adjust=False).mean()
        streak_rs = sg_avg / sl_avg.replace(0, 1e-10)
        streak_rsi = 100 - (100 / (1 + streak_rs))

        # Component 3: Percent rank of current return
        returns = close.pct_change()
        pct_rank = returns.rolling(window=roc_period).apply(
            lambda x: (x.iloc[-1] > x.iloc[:-1]).sum() / max(1, len(x) - 1), raw=False
        ) * 100

        # Composite
        crsi = (price_rsi + streak_rsi + pct_rank) / 3.0

        latest = None
        clean = crsi.dropna()
        if not clean.empty:
            latest = float(clean.iloc[-1])

        return {
            "connors_rsi": crsi.tolist(),
            "price_rsi": price_rsi.tolist(),
            "streak_rsi": streak_rsi.tolist(),
            "percent_rank": pct_rank.tolist(),
            "latest": latest,
        }

    def calculate_klinger_oscillator(
        self, df: pd.DataFrame, fast_period: int = 34, slow_period: int = 55,
        signal_period: int = 13,
    ) -> Dict[str, Any]:
        """
        Klinger Volume Oscillator (KVO).

        Developed by Stephen Klinger, uses volume force (combining
        volume, price trend, and price range) to predict price
        reversals. Divergences between KVO and price are significant.

        Args:
            df: OHLCV DataFrame.
            fast_period: Fast EMA period (default 34).
            slow_period: Slow EMA period (default 55).
            signal_period: Signal line period (default 13).

        Returns:
            Dict with 'kvo', 'signal', 'histogram'.
        """
        self._validate_dataframe(df, require_volume=True)
        high = df["high"]
        low = df["low"]
        close = df["close"]
        volume = df["volume"].astype(float)

        # Typical price and trend direction
        tp = (high + low + close) / 3.0
        trend = pd.Series(0, index=df.index)
        for i in range(1, len(df)):
            if tp.iloc[i] > tp.iloc[i - 1]:
                trend.iloc[i] = 1
            elif tp.iloc[i] < tp.iloc[i - 1]:
                trend.iloc[i] = -1
            else:
                trend.iloc[i] = trend.iloc[i - 1]

        # Volume force
        dm = high - low
        cm = dm.rolling(window=2).sum()
        vf = volume * trend * abs(2 * dm / cm.replace(0, np.nan) - 1) * 100

        # KVO = fast EMA of VF - slow EMA of VF
        fast_ema = vf.ewm(span=fast_period, adjust=False).mean()
        slow_ema = vf.ewm(span=slow_period, adjust=False).mean()
        kvo = fast_ema - slow_ema

        signal = kvo.ewm(span=signal_period, adjust=False).mean()
        histogram = kvo - signal

        def _latest(s: pd.Series) -> Optional[float]:
            clean = s.dropna()
            return float(clean.iloc[-1]) if not clean.empty else None

        return {
            "kvo": kvo.tolist(),
            "signal": signal.tolist(),
            "histogram": histogram.tolist(),
            "kvo_latest": _latest(kvo),
            "signal_latest": _latest(signal),
        }

    def calculate_mcginley_dynamic(
        self, df: pd.DataFrame, period: int = 10
    ) -> Dict[str, Any]:
        """
        McGinley Dynamic.

        An adaptive moving average invented by John McGinley that
        automatically adjusts its speed based on market conditions.
        It speeds up in trending markets and slows in ranging markets,
        avoiding whipsaws that plague fixed-period moving averages.

        Formula: MD = MD_prev + (close - MD_prev) / (k * period * (close/MD_prev)^4)

        Args:
            df: OHLCV DataFrame.
            period: Reference period (default 10).

        Returns:
            Dict with 'mcginley_dynamic' values.
        """
        self._validate_dataframe(df)
        close = df["close"]
        k = 0.6  # McGinley's constant

        md = pd.Series(np.nan, index=close.index)
        first_valid = close.first_valid_index()
        if first_valid is None:
            return {"mcginley_dynamic": md.tolist(), "latest": None}

        start_idx = close.index.get_loc(first_valid)
        md.iloc[start_idx] = close.iloc[start_idx]

        for i in range(start_idx + 1, len(close)):
            prev = md.iloc[i - 1]
            c = close.iloc[i]
            if not np.isnan(prev) and prev != 0 and not np.isnan(c):
                ratio = c / prev
                divisor = k * period * (ratio ** 4)
                md.iloc[i] = prev + (c - prev) / divisor
            else:
                md.iloc[i] = prev

        latest = None
        clean = md.dropna()
        if not clean.empty:
            latest = float(clean.iloc[-1])

        return {"mcginley_dynamic": md.tolist(), "latest": latest}

    def calculate_trix(
        self, df: pd.DataFrame, period: int = 15, signal_period: int = 9
    ) -> Dict[str, Any]:
        """
        TRIX.

        A triple-smoothed EMA rate-of-change oscillator. Filters out
        insignificant price cycles and noise. Triple smoothing
        eliminates cycles shorter than the specified period.

        - Positive TRIX: bullish momentum
        - Negative TRIX: bearish momentum
        - Signal line crossovers generate trade signals

        Args:
            df: OHLCV DataFrame.
            period: Triple EMA period (default 15).
            signal_period: Signal line period (default 9).

        Returns:
            Dict with 'trix', 'signal', 'histogram'.
        """
        self._validate_dataframe(df)
        close = df["close"]

        # Triple-smoothed EMA
        ema1 = close.ewm(span=period, adjust=False).mean()
        ema2 = ema1.ewm(span=period, adjust=False).mean()
        ema3 = ema2.ewm(span=period, adjust=False).mean()

        # Rate of change of triple EMA
        trix = (ema3 - ema3.shift(1)) / ema3.shift(1).replace(0, np.nan) * 10000

        signal = trix.ewm(span=signal_period, adjust=False).mean()
        histogram = trix - signal

        def _latest(s: pd.Series) -> Optional[float]:
            clean = s.dropna()
            return float(clean.iloc[-1]) if not clean.empty else None

        return {
            "trix": trix.tolist(),
            "signal": signal.tolist(),
            "histogram": histogram.tolist(),
            "trix_latest": _latest(trix),
            "signal_latest": _latest(signal),
        }

    def calculate_alma(
        self, df: pd.DataFrame, period: int = 20,
        offset: float = 0.85, sigma: float = 6.0,
    ) -> Dict[str, Any]:
        """
        Arnaud Legoux Moving Average (ALMA).

        A moving average that uses a Gaussian distribution as a
        weighting scheme combined with an offset parameter. Provides
        superior smoothness and responsiveness compared to SMA/EMA.
        Commonly used in algorithmic trading for signal generation.

        Args:
            df: OHLCV DataFrame.
            period: Window period (default 20).
            offset: Gaussian offset 0-1 (default 0.85, weighted to recent).
            sigma: Gaussian sigma (default 6.0).

        Returns:
            Dict with 'alma' values.
        """
        self._validate_dataframe(df)
        close = df["close"]

        # Gaussian weights
        m = offset * (period - 1)
        s = period / sigma
        weights = np.array(
            [np.exp(-((i - m) ** 2) / (2 * s * s)) for i in range(period)]
        )
        weights /= weights.sum()

        alma = close.rolling(window=period).apply(
            lambda x: np.dot(x, weights), raw=True
        )

        latest = None
        clean = alma.dropna()
        if not clean.empty:
            latest = float(clean.iloc[-1])

        return {"alma": alma.tolist(), "latest": latest}

    def calculate_chande_kroll_stop(
        self, df: pd.DataFrame, atr_period: int = 10,
        atr_mult: float = 2.0, period: int = 9,
    ) -> Dict[str, Any]:
        """
        Chande Kroll Stop.

        A stop-loss placement indicator developed by Tushar Chande
        and Stanley Kroll. Uses ATR to compute upper and lower stop
        levels that adapt to volatility. Widens in volatile markets,
        tightens in calm markets.

        Args:
            df: OHLCV DataFrame.
            atr_period: ATR period (default 10).
            atr_mult: ATR multiplier (default 2.0).
            period: Smoothing period for high/low stops (default 9).

        Returns:
            Dict with 'stop_long', 'stop_short'.
        """
        self._validate_dataframe(df)
        high = df["high"]
        low = df["low"]
        close = df["close"]

        # ATR
        tr = pd.concat(
            [high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()],
            axis=1,
        ).max(axis=1)
        atr = tr.ewm(span=atr_period, adjust=False).mean()

        # First high/low stops
        high_stop = high.rolling(window=period).max() - atr_mult * atr
        low_stop = low.rolling(window=period).min() + atr_mult * atr

        # Smoothed stops
        stop_long = high_stop.rolling(window=period).max()
        stop_short = low_stop.rolling(window=period).min()

        def _latest(s: pd.Series) -> Optional[float]:
            clean = s.dropna()
            return float(clean.iloc[-1]) if not clean.empty else None

        return {
            "stop_long": stop_long.tolist(),
            "stop_short": stop_short.tolist(),
            "stop_long_latest": _latest(stop_long),
            "stop_short_latest": _latest(stop_short),
        }

    def calculate_relative_vigor_index(
        self, df: pd.DataFrame, period: int = 10, signal_period: int = 4
    ) -> Dict[str, Any]:
        """
        Relative Vigor Index (RVI).

        Measures the conviction of a recent price action by comparing
        closing prices to opening prices, normalized by the trading
        range. The idea: prices tend to close higher than they open
        in bull markets and lower in bear markets.

        Args:
            df: OHLCV DataFrame.
            period: Smoothing period (default 10).
            signal_period: Signal line period (default 4).

        Returns:
            Dict with 'rvi', 'signal', 'histogram'.
        """
        self._validate_dataframe(df)
        o, h, l, c = df["open"], df["high"], df["low"], df["close"]

        # Numerator: close - open (smoothed)
        num_raw = c - o
        num = (
            num_raw
            + 2 * num_raw.shift(1)
            + 2 * num_raw.shift(2)
            + num_raw.shift(3)
        ) / 6.0
        num_smooth = num.rolling(window=period).mean()

        # Denominator: high - low (smoothed)
        den_raw = h - l
        den = (
            den_raw
            + 2 * den_raw.shift(1)
            + 2 * den_raw.shift(2)
            + den_raw.shift(3)
        ) / 6.0
        den_smooth = den.rolling(window=period).mean()

        rvi = num_smooth / den_smooth.replace(0, np.nan)

        # Signal line
        sig = (
            rvi
            + 2 * rvi.shift(1)
            + 2 * rvi.shift(2)
            + rvi.shift(3)
        ) / 6.0

        histogram = rvi - sig

        def _latest(s: pd.Series) -> Optional[float]:
            clean = s.dropna()
            return float(clean.iloc[-1]) if not clean.empty else None

        return {
            "rvi": rvi.tolist(),
            "signal": sig.tolist(),
            "histogram": histogram.tolist(),
            "rvi_latest": _latest(rvi),
            "signal_latest": _latest(sig),
        }

    @staticmethod
    def _compute_wma(series: pd.Series, period: int) -> pd.Series:
        """
        Compute Weighted Moving Average for a Series.

        Uses linear weighting: period, period-1, ..., 1
        """
        if len(series) < period:
            return pd.Series(np.nan, index=series.index)
        weights = np.arange(1, period + 1, dtype=float)
        return series.rolling(window=period).apply(
            lambda x: np.dot(x, weights) / weights.sum(), raw=True
        )


# Module-level singleton for easy import
technical_indicator_calculator = TechnicalIndicatorCalculator()
