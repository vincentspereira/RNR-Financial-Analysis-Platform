"""
Event-driven backtesting engine for strategy evaluation.

Supports multiple strategy types, slippage models, transaction cost models,
and comprehensive performance metrics calculation.
"""
import warnings
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from app.core.logging import get_logger

logger = get_logger("app.services.backtesting.engine")

TRADING_DAYS_PER_YEAR = 252


@dataclass
class SlippageConfig:
    """Slippage model configuration."""
    model: str = "percentage"  # fixed, percentage, volume_based
    value: float = 0.001  # 0.1% default for percentage, $0.01 for fixed


@dataclass
class TransactionCostConfig:
    """Transaction cost model configuration."""
    model: str = "percentage"  # flat, per_share, percentage
    value: float = 0.001  # 0.1% default


@dataclass
class StrategyConfig:
    """Strategy configuration."""
    strategy_type: str = "sma_crossover"
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BacktestConfig:
    """Full backtest configuration."""
    symbols: List[str] = field(default_factory=list)
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    initial_capital: float = 100000.0
    lookback_days: int = 504
    slippage: SlippageConfig = field(default_factory=SlippageConfig)
    transaction_costs: TransactionCostConfig = field(default_factory=TransactionCostConfig)
    benchmark_symbol: Optional[str] = "SPY"
    position_size_pct: float = 1.0


@dataclass
class TradeRecord:
    """Record of a single trade execution."""
    symbol: str
    action: str  # buy, sell
    date: date
    price: float
    shares: float
    commission: float
    slippage_cost: float
    pnl: Optional[float] = None


@dataclass
class BacktestMetrics:
    """Comprehensive backtest performance metrics."""
    total_return: float = 0.0
    annualized_return: float = 0.0
    cagr: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_duration_days: int = 0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    total_trades: int = 0
    avg_holding_period_days: float = 0.0
    alpha: Optional[float] = None
    beta: Optional[float] = None
    information_ratio: Optional[float] = None


@dataclass
class BacktestResult:
    """Complete backtest result."""
    status: str = "completed"
    strategy: str = ""
    symbols: List[str] = field(default_factory=list)
    initial_capital: float = 100000.0
    final_value: float = 100000.0
    metrics: BacktestMetrics = field(default_factory=BacktestMetrics)
    equity_curve: List[Dict[str, Any]] = field(default_factory=list)
    trades: List[TradeRecord] = field(default_factory=list)
    benchmark_total_return: Optional[float] = None
    run_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class BacktestEngine:
    """
    Event-driven backtesting engine.

    Evaluates trading strategies against historical data with configurable
    slippage, transaction costs, and comprehensive performance metrics.
    """

    AVAILABLE_STRATEGIES = {
        "sma_crossover": {
            "description": "Simple Moving Average crossover (fast/slow)",
            "default_params": {"fast_period": 20, "slow_period": 50},
        },
        "ema_crossover": {
            "description": "Exponential Moving Average crossover",
            "default_params": {"fast_period": 12, "slow_period": 26},
        },
        "rsi_oversold_overbought": {
            "description": "RSI-based buy at oversold, sell at overbought",
            "default_params": {"period": 14, "oversold": 30, "overbought": 70},
        },
        "bollinger_breakout": {
            "description": "Bollinger Band breakout strategy",
            "default_params": {"period": 20, "num_std": 2.0},
        },
        "macd_signal": {
            "description": "MACD signal line crossover",
            "default_params": {"fast": 12, "slow": 26, "signal": 9},
        },
        "dual_momentum": {
            "description": "Dual momentum (relative + absolute)",
            "default_params": {"lookback": 12, "benchmark_threshold": 0.0},
        },
    }

    async def run_backtest(
        self,
        price_data: Dict[str, pd.DataFrame],
        config: BacktestConfig,
        benchmark_data: Optional[pd.DataFrame] = None,
    ) -> BacktestResult:
        """
        Run a full backtest with the given configuration.

        Args:
            price_data: Dict of symbol -> DataFrame with OHLCV columns.
            config: Backtest configuration.
            benchmark_data: Optional benchmark price DataFrame.

        Returns:
            BacktestResult with metrics, equity curve, and trade records.
        """
        try:
            # Combine all symbol data into a single DataFrame
            combined = self._combine_symbol_data(price_data, config.symbols)

            if combined.empty:
                return BacktestResult(
                    status="error",
                    strategy=config.strategy.strategy_type,
                    symbols=config.symbols,
                    initial_capital=config.initial_capital,
                )

            # Generate signals
            signals = self._generate_signals(combined, config.strategy)

            # Simulate trades
            trades = self._simulate_trades(
                combined, signals, config
            )

            # Build equity curve
            equity_curve = self._calculate_equity_curve(
                combined, trades, config.initial_capital
            )

            # Calculate benchmark returns
            benchmark_returns = None
            benchmark_total_return = None
            if benchmark_data is not None and not benchmark_data.empty:
                benchmark_returns = benchmark_data["close"].pct_change().dropna()
                if not benchmark_returns.empty:
                    benchmark_total_return = float(
                        (benchmark_data["close"].iloc[-1] / benchmark_data["close"].iloc[0]) - 1
                    )

            # Calculate metrics
            metrics = self._calculate_metrics(equity_curve, benchmark_returns)

            # Build result
            final_value = float(equity_curve.iloc[-1]) if not equity_curve.empty else config.initial_capital

            equity_list = []
            for i, (dt, val) in enumerate(equity_curve.items()):
                equity_list.append({"date": str(dt.date()) if hasattr(dt, "date") else str(dt), "value": float(val)})

            return BacktestResult(
                status="completed",
                strategy=config.strategy.strategy_type,
                symbols=config.symbols,
                initial_capital=config.initial_capital,
                final_value=final_value,
                metrics=metrics,
                equity_curve=equity_list,
                trades=trades,
                benchmark_total_return=benchmark_total_return,
                run_date=datetime.now(timezone.utc),
            )

        except Exception as exc:
            logger.error(f"Backtest error: {exc}", exc_info=True)
            return BacktestResult(
                status="error",
                strategy=config.strategy.strategy_type,
                symbols=config.symbols,
                initial_capital=config.initial_capital,
            )

    def _combine_symbol_data(
        self, price_data: Dict[str, pd.DataFrame], symbols: List[str]
    ) -> pd.DataFrame:
        """Combine multi-symbol data into a single DataFrame with multi-level columns."""
        frames = {}
        for symbol in symbols:
            df = price_data.get(symbol)
            if df is not None and not df.empty:
                frames[symbol] = df

        if not frames:
            return pd.DataFrame()

        if len(frames) == 1:
            sym = list(frames.keys())[0]
            df = frames[sym].copy()
            df.columns = [f"{col}_{sym}" for col in df.columns]
            return df

        combined = pd.concat(frames, axis=1, names=["symbol", "field"])
        combined = combined.dropna(how="all")
        return combined

    def _generate_signals(
        self, data: pd.DataFrame, strategy: StrategyConfig
    ) -> pd.Series:
        """
        Generate buy (1), sell (-1), or hold (0) signals.

        Returns a Series of signals aligned with data index.
        """
        strategy_type = strategy.strategy_type
        params = strategy.parameters or {}
        defaults = self.AVAILABLE_STRATEGIES.get(strategy_type, {}).get("default_params", {})
        params = {**defaults, **params}

        if strategy_type == "sma_crossover":
            return self._sma_crossover_signals(data, params)
        elif strategy_type == "ema_crossover":
            return self._ema_crossover_signals(data, params)
        elif strategy_type == "rsi_oversold_overbought":
            return self._rsi_signals(data, params)
        elif strategy_type == "bollinger_breakout":
            return self._bollinger_signals(data, params)
        elif strategy_type == "macd_signal":
            return self._macd_signals(data, params)
        elif strategy_type == "dual_momentum":
            return self._dual_momentum_signals(data, params)
        else:
            logger.warning(f"Unknown strategy: {strategy_type}, defaulting to SMA crossover")
            return self._sma_crossover_signals(data, params)

    def _get_close_series(self, data: pd.DataFrame) -> pd.Series:
        """Extract close price series from potentially multi-level DataFrame."""
        if isinstance(data.columns, pd.MultiIndex):
            first_symbol = data.columns.get_level_values(0).unique()[0]
            return data[(first_symbol, "close")]
        # Single symbol - find close column
        for col in data.columns:
            if "close" in str(col).lower():
                return data[col]
        return data.iloc[:, -1]  # fallback to last column

    def _get_volume_series(self, data: pd.DataFrame) -> pd.Series:
        """Extract volume series."""
        if isinstance(data.columns, pd.MultiIndex):
            first_symbol = data.columns.get_level_values(0).unique()[0]
            return data[(first_symbol, "volume")]
        for col in data.columns:
            if "volume" in str(col).lower():
                return data[col]
        return pd.Series(0, index=data.index)

    def _sma_crossover_signals(self, data: pd.DataFrame, params: dict) -> pd.Series:
        fast_period = params.get("fast_period", 20)
        slow_period = params.get("slow_period", 50)
        close = self._get_close_series(data)

        fast_sma = close.rolling(window=fast_period).mean()
        slow_sma = close.rolling(window=slow_period).mean()

        signals = pd.Series(0, index=data.index)
        signals[fast_sma > slow_sma] = 1
        signals[fast_sma < slow_sma] = -1

        # Generate trade signals only on crossovers
        diff = fast_sma - slow_sma
        trade_signals = pd.Series(0, index=data.index)
        trade_signals[(diff > 0) & (diff.shift(1) <= 0)] = 1
        trade_signals[(diff < 0) & (diff.shift(1) >= 0)] = -1

        return trade_signals

    def _ema_crossover_signals(self, data: pd.DataFrame, params: dict) -> pd.Series:
        fast_period = params.get("fast_period", 12)
        slow_period = params.get("slow_period", 26)
        close = self._get_close_series(data)

        fast_ema = close.ewm(span=fast_period, adjust=False).mean()
        slow_ema = close.ewm(span=slow_period, adjust=False).mean()

        diff = fast_ema - slow_ema
        signals = pd.Series(0, index=data.index)
        signals[(diff > 0) & (diff.shift(1) <= 0)] = 1
        signals[(diff < 0) & (diff.shift(1) >= 0)] = -1
        return signals

    def _rsi_signals(self, data: pd.DataFrame, params: dict) -> pd.Series:
        period = params.get("period", 14)
        oversold = params.get("oversold", 30)
        overbought = params.get("overbought", 70)
        close = self._get_close_series(data)

        delta = close.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)

        avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
        avg_loss = loss.ewm(com=period - 1, adjust=False).mean()

        rs = avg_gain / avg_loss.replace(0, 1e-10)
        rsi = 100 - (100 / (1 + rs))

        signals = pd.Series(0, index=data.index)
        signals[(rsi < oversold) & (rsi.shift(1) >= oversold)] = 1
        signals[(rsi > overbought) & (rsi.shift(1) <= overbought)] = -1
        return signals

    def _bollinger_signals(self, data: pd.DataFrame, params: dict) -> pd.Series:
        period = params.get("period", 20)
        num_std = params.get("num_std", 2.0)
        close = self._get_close_series(data)

        sma = close.rolling(window=period).mean()
        std = close.rolling(window=period).std()
        upper = sma + num_std * std
        lower = sma - num_std * std

        signals = pd.Series(0, index=data.index)
        # Buy when price crosses below lower band
        signals[(close < lower) & (close.shift(1) >= lower.shift(1))] = 1
        # Sell when price crosses above upper band
        signals[(close > upper) & (close.shift(1) <= upper.shift(1))] = -1
        return signals

    def _macd_signals(self, data: pd.DataFrame, params: dict) -> pd.Series:
        fast = params.get("fast", 12)
        slow = params.get("slow", 26)
        signal_period = params.get("signal", 9)
        close = self._get_close_series(data)

        fast_ema = close.ewm(span=fast, adjust=False).mean()
        slow_ema = close.ewm(span=slow, adjust=False).mean()
        macd_line = fast_ema - slow_ema
        signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()

        diff = macd_line - signal_line
        signals = pd.Series(0, index=data.index)
        signals[(diff > 0) & (diff.shift(1) <= 0)] = 1
        signals[(diff < 0) & (diff.shift(1) >= 0)] = -1
        return signals

    def _dual_momentum_signals(self, data: pd.DataFrame, params: dict) -> pd.Series:
        lookback = params.get("lookback", 12)
        threshold = params.get("benchmark_threshold", 0.0)
        close = self._get_close_series(data)

        momentum = close.pct_change(lookback)

        signals = pd.Series(0, index=data.index)
        signals[(momentum > threshold) & (momentum.shift(1) <= threshold)] = 1
        signals[(momentum < threshold) & (momentum.shift(1) >= threshold)] = -1
        return signals

    def _simulate_trades(
        self,
        data: pd.DataFrame,
        signals: pd.Series,
        config: BacktestConfig,
    ) -> List[TradeRecord]:
        """Simulate trade executions from signals with costs."""
        close = self._get_close_series(data)
        volume = self._get_volume_series(data)

        trades: List[TradeRecord] = []
        position: Optional[Dict[str, Any]] = None  # current open position

        for i in range(len(signals)):
            signal = signals.iloc[i]
            if signal == 0:
                continue

            current_date = data.index[i]
            price = float(close.iloc[i])

            if signal == 1 and position is None:
                # Buy
                shares = (config.initial_capital * config.position_size_pct) / price if price > 0 else 0
                commission = self._calculate_commission(shares, price, config.transaction_costs)
                slippage = self._calculate_slippage(shares, price, volume.iloc[i], config.slippage)

                position = {
                    "entry_date": current_date,
                    "entry_price": price,
                    "shares": shares,
                    "commission_paid": commission,
                    "slippage_paid": slippage,
                }

            elif signal == -1 and position is not None:
                # Sell
                commission = self._calculate_commission(position["shares"], price, config.transaction_costs)
                slippage = self._calculate_slippage(position["shares"], price, volume.iloc[i], config.slippage)

                pnl = (price - position["entry_price"]) * position["shares"]
                pnl -= commission + slippage + position["commission_paid"] + position["slippage_paid"]

                dt = current_date.date() if hasattr(current_date, "date") else current_date
                trades.append(TradeRecord(
                    symbol=config.symbols[0] if config.symbols else "UNKNOWN",
                    action="sell",
                    date=dt,
                    price=price,
                    shares=position["shares"],
                    commission=commission,
                    slippage_cost=slippage,
                    pnl=pnl,
                ))

                # Also record the buy
                entry_dt = position["entry_date"].date() if hasattr(position["entry_date"], "date") else position["entry_date"]
                trades.insert(len(trades) - 1, TradeRecord(
                    symbol=config.symbols[0] if config.symbols else "UNKNOWN",
                    action="buy",
                    date=entry_dt,
                    price=position["entry_price"],
                    shares=position["shares"],
                    commission=position["commission_paid"],
                    slippage_cost=position["slippage_paid"],
                ))

                position = None

        return trades

    def _calculate_commission(
        self, shares: float, price: float, config: TransactionCostConfig
    ) -> float:
        """Calculate transaction commission."""
        if config.model == "flat":
            return config.value
        elif config.model == "per_share":
            return abs(shares) * config.value
        else:  # percentage
            return abs(shares * price) * config.value

    def _calculate_slippage(
        self, shares: float, price: float, volume: float, config: SlippageConfig
    ) -> float:
        """Calculate slippage cost."""
        if config.model == "fixed":
            return abs(shares) * config.value
        elif config.model == "volume_based":
            if volume > 0:
                participation = shares / volume
                return abs(shares * price) * participation * config.value
            return 0.0
        else:  # percentage
            return abs(shares * price) * config.value

    def _calculate_equity_curve(
        self,
        data: pd.DataFrame,
        trades: List[TradeRecord],
        initial_capital: float,
    ) -> pd.Series:
        """Build equity curve from data and executed trades."""
        close = self._get_close_series(data)

        if not trades:
            # No trades - return flat equity curve
            return pd.Series(initial_capital, index=data.index)

        # Build trade lookup by date
        trade_lookup: Dict[Any, List[TradeRecord]] = {}
        for trade in trades:
            key = trade.date
            if key not in trade_lookup:
                trade_lookup[key] = []
            trade_lookup[key].append(trade)

        equity = [initial_capital]
        cash = initial_capital
        position_shares = 0.0
        position_cost = 0.0
        dates = [data.index[0]]

        for i in range(1, len(data)):
            dt = data.index[i]
            dt_key = dt.date() if hasattr(dt, "date") else dt

            # Process trades on this date
            for trade in trade_lookup.get(dt_key, []):
                if trade.action == "buy":
                    cash -= trade.shares * trade.price + trade.commission + trade.slippage_cost
                    position_shares += trade.shares
                    position_cost += trade.shares * trade.price
                elif trade.action == "sell":
                    cash += trade.shares * trade.price - trade.commission - trade.slippage_cost
                    position_shares -= trade.shares
                    position_cost -= trade.shares * trade.price

            # Current portfolio value
            current_price = float(close.iloc[i])
            portfolio_value = cash + position_shares * current_price

            equity.append(portfolio_value)
            dates.append(dt)

        return pd.Series(equity, index=dates)

    def _calculate_metrics(
        self,
        equity_curve: pd.Series,
        benchmark_returns: Optional[pd.Series] = None,
    ) -> BacktestMetrics:
        """Calculate comprehensive performance metrics."""
        if len(equity_curve) < 2:
            return BacktestMetrics()

        returns = equity_curve.pct_change().dropna()

        # Total return
        total_return = float((equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1)

        # CAGR
        num_years = len(equity_curve) / TRADING_DAYS_PER_YEAR
        if num_years > 0 and equity_curve.iloc[0] > 0:
            cagr = (equity_curve.iloc[-1] / equity_curve.iloc[0]) ** (1 / num_years) - 1
        else:
            cagr = 0.0

        # Annualized return
        annualized_return = float(returns.mean() * TRADING_DAYS_PER_YEAR)

        # Max drawdown
        cumulative = equity_curve / equity_curve.iloc[0]
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = float(drawdown.min())

        # Max drawdown duration
        in_drawdown = drawdown < 0
        max_dd_duration = 0
        current_dd = 0
        for val in in_drawdown:
            if val:
                current_dd += 1
                max_dd_duration = max(max_dd_duration, current_dd)
            else:
                current_dd = 0

        # Sharpe ratio
        if returns.std() > 0:
            sharpe = float((returns.mean() / returns.std()) * np.sqrt(TRADING_DAYS_PER_YEAR))
        else:
            sharpe = 0.0

        # Sortino ratio
        downside = returns[returns < 0]
        if len(downside) > 0 and downside.std() > 0:
            sortino = float((returns.mean() / downside.std()) * np.sqrt(TRADING_DAYS_PER_YEAR))
        else:
            sortino = 0.0

        # Calmar ratio
        calmar = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0.0

        # Win/loss analysis from equity changes
        daily_changes = equity_curve.diff().dropna()
        wins = daily_changes[daily_changes > 0]
        losses = daily_changes[daily_changes < 0]
        win_rate = float(len(wins) / len(daily_changes)) if len(daily_changes) > 0 else 0.0
        avg_win = float(wins.mean()) if len(wins) > 0 else 0.0
        avg_loss = float(abs(losses.mean())) if len(losses) > 0 else 0.0
        profit_factor = (float(wins.sum()) / float(abs(losses.sum()))) if len(losses) > 0 and losses.sum() != 0 else 0.0

        # Beta and alpha vs benchmark
        alpha = None
        beta = None
        information_ratio = None
        if benchmark_returns is not None and len(benchmark_returns) > 0:
            aligned_returns = returns.reindex(benchmark_returns.index).dropna()
            aligned_bench = benchmark_returns.reindex(aligned_returns.index).dropna()

            if len(aligned_returns) > 1 and aligned_bench.var() > 0:
                covariance = float(aligned_returns.cov(aligned_bench))
                benchmark_var = float(aligned_bench.var())
                beta = covariance / benchmark_var

                risk_free_daily = 0.02 / TRADING_DAYS_PER_YEAR
                alpha = float(
                    (aligned_returns.mean() - risk_free_daily)
                    - beta * (aligned_bench.mean() - risk_free_daily)
                ) * TRADING_DAYS_PER_YEAR

                # Information ratio
                excess = aligned_returns - aligned_bench
                if excess.std() > 0:
                    information_ratio = float(excess.mean() / excess.std() * np.sqrt(TRADING_DAYS_PER_YEAR))

        return BacktestMetrics(
            total_return=total_return,
            annualized_return=annualized_return,
            cagr=float(cagr),
            max_drawdown=max_drawdown,
            max_drawdown_duration_days=max_dd_duration,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            calmar_ratio=float(calmar),
            win_rate=win_rate,
            profit_factor=profit_factor,
            avg_win=avg_win,
            avg_loss=avg_loss,
            total_trades=len(equity_curve),
            avg_holding_period_days=len(equity_curve) / max(1, 1),  # simplified
            alpha=alpha,
            beta=beta,
            information_ratio=information_ratio,
        )
