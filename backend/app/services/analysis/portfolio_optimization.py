"""
Portfolio Optimization Service

Implements Modern Portfolio Theory, risk analysis, and Monte Carlo simulation
for portfolio optimization using numpy, pandas, and scipy.
"""
import warnings
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from app.core.logging import get_logger

logger = get_logger("app.services.analysis.portfolio_optimization")

# Try importing scipy for constrained optimization; fall back to grid search if unavailable
try:
    from scipy.optimize import minimize

    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

# Annualization factor (252 trading days)
TRADING_DAYS_PER_YEAR = 252


class PortfolioOptimizer:
    """Portfolio optimization using Modern Portfolio Theory and risk analytics."""

    def calculate_efficient_frontier(
        self,
        returns_df: pd.DataFrame,
        num_portfolios: int = 10000,
        risk_free_rate: float = 0.02,
    ) -> Dict[str, Any]:
        """
        Generate the efficient frontier via Monte Carlo random portfolios.

        Args:
            returns_df: DataFrame of daily returns (columns = symbols).
            num_portfolios: Number of random portfolios to simulate.
            risk_free_rate: Annual risk-free rate (e.g. 0.02 for 2%).

        Returns:
            Dictionary with frontier_points, min_variance_portfolio,
            max_sharpe_portfolio, and optimal_weights.
        """
        if returns_df.empty or len(returns_df.columns) < 2:
            raise ValueError("At least 2 assets with return data are required.")

        symbols = list(returns_df.columns)
        num_assets = len(symbols)

        mean_returns = returns_df.mean() * TRADING_DAYS_PER_YEAR
        cov_matrix = returns_df.cov() * TRADING_DAYS_PER_YEAR

        results: Dict[str, List[float]] = {
            "returns": [],
            "volatilities": [],
            "sharpe_ratios": [],
        }
        weights_list: List[np.ndarray] = []

        for _ in range(num_portfolios):
            w = np.random.random(num_assets)
            w /= np.sum(w)

            port_return = np.dot(w, mean_returns.values)
            port_vol = np.sqrt(np.dot(w.T, np.dot(cov_matrix.values, w)))
            sharpe = (port_return - risk_free_rate) / port_vol if port_vol > 0 else 0.0

            results["returns"].append(port_return)
            results["volatilities"].append(port_vol)
            results["sharpe_ratios"].append(sharpe)
            weights_list.append(w)

        returns_arr = np.array(results["returns"])
        vols_arr = np.array(results["volatilities"])
        sharpe_arr = np.array(results["sharpe_ratios"])

        # Minimum variance portfolio
        min_var_idx = np.argmin(vols_arr)
        min_var_weights = weights_list[min_var_idx]
        min_var_portfolio = {
            "return": float(returns_arr[min_var_idx]),
            "volatility": float(vols_arr[min_var_idx]),
            "sharpe_ratio": float(sharpe_arr[min_var_idx]),
            "weights": {s: float(min_var_weights[i]) for i, s in enumerate(symbols)},
        }

        # Maximum Sharpe ratio portfolio
        max_sharpe_idx = np.argmax(sharpe_arr)
        max_sharpe_weights = weights_list[max_sharpe_idx]
        max_sharpe_portfolio = {
            "return": float(returns_arr[max_sharpe_idx]),
            "volatility": float(vols_arr[max_sharpe_idx]),
            "sharpe_ratio": float(sharpe_arr[max_sharpe_idx]),
            "weights": {s: float(max_sharpe_weights[i]) for i, s in enumerate(symbols)},
        }

        # Build frontier points -- down-sample to at most 500 points for API response
        max_points = 500
        step = max(1, num_portfolios // max_points)
        frontier_points = []
        for i in range(0, num_portfolios, step):
            frontier_points.append(
                {
                    "return": float(returns_arr[i]),
                    "volatility": float(vols_arr[i]),
                    "sharpe_ratio": float(sharpe_arr[i]),
                    "weights": {
                        s: float(weights_list[i][j]) for j, s in enumerate(symbols)
                    },
                }
            )

        return {
            "frontier_points": frontier_points,
            "min_variance_portfolio": min_var_portfolio,
            "max_sharpe_portfolio": max_sharpe_portfolio,
            "optimal_weights": max_sharpe_portfolio["weights"],
            "symbols": symbols,
            "num_portfolios_simulated": num_portfolios,
        }

    def calculate_var(
        self,
        returns: pd.Series,
        confidence_level: float = 0.95,
        method: str = "historical",
        portfolio_value: float = 100000.0,
    ) -> Dict[str, Any]:
        """
        Calculate Value at Risk (VaR).

        Args:
            returns: Series of portfolio daily returns.
            confidence_level: Confidence level (0.90, 0.95, 0.99).
            method: 'historical', 'parametric', or 'monte_carlo'.
            portfolio_value: Current portfolio value for dollar VaR.

        Returns:
            Dictionary with var_value, var_percent, confidence_level, and method.
        """
        if returns.empty:
            raise ValueError("Returns series is empty.")

        if confidence_level not in (0.90, 0.95, 0.99):
            raise ValueError("confidence_level must be 0.90, 0.95, or 0.99.")

        method = method.lower()
        if method == "historical":
            var_percent = float(
                np.percentile(returns.dropna(), (1 - confidence_level) * 100)
            )
        elif method == "parametric":
            mu = returns.mean()
            sigma = returns.std()
            from scipy.stats import norm as scipy_norm

            z_score = scipy_norm.ppf(1 - confidence_level)
            var_percent = float(mu + z_score * sigma)
        elif method == "monte_carlo":
            mu = returns.mean()
            sigma = returns.std()
            np.random.seed(42)
            simulated = np.random.normal(mu, sigma, 10000)
            var_percent = float(
                np.percentile(simulated, (1 - confidence_level) * 100)
            )
        else:
            raise ValueError(
                f"Unknown method '{method}'. Use 'historical', 'parametric', or 'monte_carlo'."
            )

        var_value = abs(var_percent * portfolio_value)

        return {
            "var_value": float(var_value),
            "var_percent": float(abs(var_percent)),
            "confidence_level": confidence_level,
            "method": method,
        }

    def calculate_cvar(
        self,
        returns: pd.Series,
        confidence_level: float = 0.95,
        method: str = "historical",
    ) -> Dict[str, Any]:
        """
        Calculate Conditional Value at Risk (CVaR / Expected Shortfall).

        The average loss beyond the VaR threshold.

        Args:
            returns: Series of portfolio daily returns.
            confidence_level: Confidence level (0.90, 0.95, 0.99).
            method: 'historical', 'parametric', or 'monte_carlo'.

        Returns:
            Dictionary with cvar_value, cvar_percent, confidence_level, and method.
        """
        if returns.empty:
            raise ValueError("Returns series is empty.")

        if confidence_level not in (0.90, 0.95, 0.99):
            raise ValueError("confidence_level must be 0.90, 0.95, or 0.99.")

        method = method.lower()
        if method == "historical":
            threshold = np.percentile(returns.dropna(), (1 - confidence_level) * 100)
            tail_returns = returns[returns <= threshold]
            if tail_returns.empty:
                tail_returns = pd.Series([threshold])
            cvar_percent = float(tail_returns.mean())
        elif method == "parametric":
            mu = returns.mean()
            sigma = returns.std()
            from scipy.stats import norm as scipy_norm

            z = scipy_norm.ppf(1 - confidence_level)
            # Expected Shortfall for normal distribution
            cvar_percent = float(mu - sigma * scipy_norm.pdf(z) / (1 - confidence_level))
        elif method == "monte_carlo":
            mu = returns.mean()
            sigma = returns.std()
            np.random.seed(42)
            simulated = np.random.normal(mu, sigma, 10000)
            threshold = np.percentile(simulated, (1 - confidence_level) * 100)
            tail = simulated[simulated <= threshold]
            cvar_percent = float(tail.mean()) if len(tail) > 0 else float(threshold)
        else:
            raise ValueError(
                f"Unknown method '{method}'. Use 'historical', 'parametric', or 'monte_carlo'."
            )

        return {
            "cvar_value": float(abs(cvar_percent)),
            "cvar_percent": float(abs(cvar_percent)),
            "confidence_level": confidence_level,
            "method": method,
        }

    def calculate_sharpe_ratio(
        self, returns: pd.Series, risk_free_rate: float = 0.02
    ) -> float:
        """
        Calculate annualized Sharpe Ratio.

        Args:
            returns: Series of daily portfolio returns.
            risk_free_rate: Annual risk-free rate.

        Returns:
            Annualized Sharpe Ratio.
        """
        if returns.empty or returns.std() == 0:
            return 0.0
        daily_rf = risk_free_rate / TRADING_DAYS_PER_YEAR
        excess_returns = returns - daily_rf
        sharpe = (excess_returns.mean() / excess_returns.std()) * np.sqrt(
            TRADING_DAYS_PER_YEAR
        )
        return float(sharpe)

    def calculate_sortino_ratio(
        self,
        returns: pd.Series,
        risk_free_rate: float = 0.02,
        target_return: float = 0.0,
    ) -> float:
        """
        Calculate annualized Sortino Ratio using downside deviation.

        Args:
            returns: Series of daily portfolio returns.
            risk_free_rate: Annual risk-free rate.
            target_return: Minimum acceptable return (daily default 0).

        Returns:
            Annualized Sortino Ratio.
        """
        if returns.empty:
            return 0.0
        daily_rf = risk_free_rate / TRADING_DAYS_PER_YEAR
        downside = returns[returns < target_return]
        if downside.empty or downside.std() == 0:
            return 0.0
        downside_std = np.sqrt(np.mean((downside - target_return) ** 2))
        if downside_std == 0:
            return 0.0
        sortino = ((returns.mean() - daily_rf) / downside_std) * np.sqrt(
            TRADING_DAYS_PER_YEAR
        )
        return float(sortino)

    def calculate_treynor_ratio(
        self, returns: pd.Series, beta: float, risk_free_rate: float = 0.02
    ) -> float:
        """
        Calculate annualized Treynor Ratio.

        Args:
            returns: Series of daily portfolio returns.
            beta: Portfolio beta relative to benchmark.
            risk_free_rate: Annual risk-free rate.

        Returns:
            Annualized Treynor Ratio.
        """
        if returns.empty or beta == 0:
            return 0.0
        annualized_return = returns.mean() * TRADING_DAYS_PER_YEAR
        treynor = (annualized_return - risk_free_rate) / beta
        return float(treynor)

    def calculate_portfolio_metrics(
        self, returns: pd.Series, risk_free_rate: float = 0.02
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive portfolio metrics.

        Args:
            returns: Series of daily portfolio returns.
            risk_free_rate: Annual risk-free rate.

        Returns:
            Dictionary with Sharpe, Sortino, max drawdown, Calmar, win rate,
            avg return, volatility, skewness, and kurtosis.
        """
        if returns.empty:
            return {
                "sharpe_ratio": 0.0,
                "sortino_ratio": 0.0,
                "max_drawdown": 0.0,
                "calmar_ratio": 0.0,
                "win_rate": 0.0,
                "average_return": 0.0,
                "annualized_return": 0.0,
                "volatility": 0.0,
                "annualized_volatility": 0.0,
                "skewness": 0.0,
                "kurtosis": 0.0,
                "total_return": 0.0,
            }

        sharpe = self.calculate_sharpe_ratio(returns, risk_free_rate)
        sortino = self.calculate_sortino_ratio(returns, risk_free_rate)

        # Max drawdown
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = float(drawdown.min())

        # Annualized return and volatility
        annualized_return = float(returns.mean() * TRADING_DAYS_PER_YEAR)
        annualized_vol = float(returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR))

        # Calmar ratio: annualized return / abs(max drawdown)
        calmar = (
            annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0.0
        )

        # Win rate
        win_rate = float((returns > 0).sum() / len(returns))

        # Skewness and kurtosis
        skewness = float(returns.skew())
        kurtosis = float(returns.kurtosis())

        # Total return over the period
        total_return = float(cumulative.iloc[-1] - 1)

        return {
            "sharpe_ratio": sharpe,
            "sortino_ratio": sortino,
            "max_drawdown": max_drawdown,
            "calmar_ratio": float(calmar),
            "win_rate": win_rate,
            "average_return": float(returns.mean()),
            "annualized_return": annualized_return,
            "volatility": float(returns.std()),
            "annualized_volatility": annualized_vol,
            "skewness": skewness,
            "kurtosis": kurtosis,
            "total_return": total_return,
        }

    def optimize_portfolio(
        self,
        returns_df: pd.DataFrame,
        target_return: Optional[float] = None,
        risk_tolerance: Optional[float] = None,
        constraints: Optional[Dict[str, Any]] = None,
        method: str = "max_sharpe",
    ) -> Dict[str, Any]:
        """
        Mean-variance portfolio optimization.

        Args:
            returns_df: DataFrame of daily returns (columns = symbols).
            target_return: Target annualized return constraint.
            risk_tolerance: Maximum acceptable annualized volatility.
            constraints: Dict with optional 'min_weight', 'max_weight' (global),
                         or 'per_symbol' dict mapping symbol to min/max weight.
            method: 'max_sharpe', 'min_variance', 'target_return',
                    'equal_weight', or 'risk_parity'.

        Returns:
            Optimized weights and expected metrics.
        """
        if returns_df.empty:
            raise ValueError("Returns DataFrame is empty.")

        symbols = list(returns_df.columns)
        num_assets = len(symbols)
        mean_returns = returns_df.mean() * TRADING_DAYS_PER_YEAR
        cov_matrix = returns_df.cov() * TRADING_DAYS_PER_YEAR

        constraints = constraints or {}

        # Build bounds
        min_weight = constraints.get("min_weight", 0.0)
        max_weight = constraints.get("max_weight", 1.0)
        per_symbol = constraints.get("per_symbol", {})

        bounds = []
        for sym in symbols:
            sym_constraints = per_symbol.get(sym, {})
            lo = sym_constraints.get("min", min_weight)
            hi = sym_constraints.get("max", max_weight)
            bounds.append((lo, hi))

        # Handle equal-weight shortcut
        if method == "equal_weight":
            w = np.ones(num_assets) / num_assets
            return self._build_optimization_result(
                w, symbols, mean_returns, cov_matrix, method, risk_free_rate=0.02
            )

        # Handle risk parity shortcut
        if method == "risk_parity":
            w = self._risk_parity_weights(
                cov_matrix.values, bounds, num_assets
            )
            return self._build_optimization_result(
                w, symbols, mean_returns, cov_matrix, method, risk_free_rate=0.02
            )

        if not SCIPY_AVAILABLE:
            # Fallback: grid search approximation
            return self._grid_search_optimize(
                returns_df,
                symbols,
                mean_returns,
                cov_matrix,
                bounds,
                target_return,
                risk_tolerance,
                method,
            )

        # --- scipy optimization ---
        init_weights = np.ones(num_assets) / num_assets
        risk_free_rate = 0.02

        def _portfolio_volatility(w: np.ndarray) -> float:
            return float(np.sqrt(np.dot(w.T, np.dot(cov_matrix.values, w))))

        def _portfolio_return(w: np.ndarray) -> float:
            return float(np.dot(w, mean_returns.values))

        def _neg_sharpe(w: np.ndarray) -> float:
            ret = _portfolio_return(w)
            vol = _portfolio_volatility(w)
            return -(ret - risk_free_rate) / vol if vol > 1e-10 else 0.0

        scipy_constraints = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}
        ]

        if target_return is not None and method == "target_return":
            scipy_constraints.append(
                {
                    "type": "eq",
                    "fun": lambda w: _portfolio_return(w) - target_return,
                }
            )

        if risk_tolerance is not None:
            scipy_constraints.append(
                {
                    "type": "ineq",
                    "fun": lambda w: risk_tolerance - _portfolio_volatility(w),
                }
            )

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            if method in ("max_sharpe", "target_return"):
                result = minimize(
                    _neg_sharpe,
                    init_weights,
                    method="SLSQP",
                    bounds=bounds,
                    constraints=scipy_constraints,
                    options={"maxiter": 1000, "ftol": 1e-10},
                )
            elif method == "min_variance":
                result = minimize(
                    _portfolio_volatility,
                    init_weights,
                    method="SLSQP",
                    bounds=bounds,
                    constraints=scipy_constraints,
                    options={"maxiter": 1000, "ftol": 1e-10},
                )
            else:
                # Default to max sharpe
                result = minimize(
                    _neg_sharpe,
                    init_weights,
                    method="SLSQP",
                    bounds=bounds,
                    constraints=scipy_constraints,
                    options={"maxiter": 1000, "ftol": 1e-10},
                )

        if not result.success:
            logger.warning(
                "Optimization did not converge: %s. Using last iteration.", result.message
            )

        optimal_w = result.x
        # Ensure weights sum to 1 and clip negatives from numerical noise
        optimal_w = np.clip(optimal_w, 0, 1)
        optimal_w /= optimal_w.sum()

        return self._build_optimization_result(
            optimal_w, symbols, mean_returns, cov_matrix, method, risk_free_rate
        )

    def calculate_correlation_matrix(
        self, returns_df: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Calculate correlation and covariance matrices.

        Args:
            returns_df: DataFrame of daily returns (columns = symbols).

        Returns:
            Dictionary with correlation_matrix, covariance_matrix, and labels.
        """
        if returns_df.empty:
            raise ValueError("Returns DataFrame is empty.")

        symbols = list(returns_df.columns)

        corr = returns_df.corr()
        cov = returns_df.cov()

        correlation_matrix = {
            sym: {col: float(corr.loc[sym, col]) for col in symbols}
            for sym in symbols
        }
        covariance_matrix = {
            sym: {col: float(cov.loc[sym, col]) for col in symbols}
            for sym in symbols
        }

        return {
            "correlation_matrix": correlation_matrix,
            "covariance_matrix": covariance_matrix,
            "labels": symbols,
        }

    def monte_carlo_simulation(
        self,
        returns_df: pd.DataFrame,
        weights: Optional[List[float]] = None,
        num_simulations: int = 1000,
        time_horizon: int = 252,
        initial_value: float = 100000.0,
    ) -> Dict[str, Any]:
        """
        Run Monte Carlo simulation for portfolio path projection.

        Args:
            returns_df: DataFrame of daily returns (columns = symbols).
            weights: Portfolio weights. If None, equal-weight is used.
            num_simulations: Number of simulation paths.
            time_horizon: Number of trading days to simulate.
            initial_value: Starting portfolio value.

        Returns:
            Distribution of final values, percentiles, and probability of loss.
        """
        if returns_df.empty:
            raise ValueError("Returns DataFrame is empty.")

        symbols = list(returns_df.columns)
        num_assets = len(symbols)

        if weights is None:
            w = np.ones(num_assets) / num_assets
        else:
            w = np.array(weights)
            if len(w) != num_assets:
                raise ValueError(
                    f"Expected {num_assets} weights, got {len(w)}."
                )

        mean_daily = returns_df.mean().values
        cov_daily = returns_df.cov().values

        # Simulate correlated daily returns
        np.random.seed(42)
        try:
            L = np.linalg.cholesky(cov_daily)
        except np.linalg.LinAlgError:
            # If covariance matrix is not positive-definite, fall back to diagonal
            logger.warning(
                "Covariance matrix not positive-definite; using diagonal approximation."
            )
            L = np.diag(np.sqrt(np.diag(cov_daily)))

        final_values = np.zeros(num_simulations)
        for i in range(num_simulations):
            z = np.random.standard_normal((time_horizon, num_assets))
            correlated = z @ L.T + mean_daily
            port_returns = correlated @ w
            cumulative = np.prod(1 + port_returns)
            final_values[i] = initial_value * cumulative

        percentiles = {
            "p1": float(np.percentile(final_values, 1)),
            "p5": float(np.percentile(final_values, 5)),
            "p10": float(np.percentile(final_values, 10)),
            "p25": float(np.percentile(final_values, 25)),
            "p50": float(np.percentile(final_values, 50)),
            "p75": float(np.percentile(final_values, 75)),
            "p90": float(np.percentile(final_values, 90)),
            "p95": float(np.percentile(final_values, 95)),
            "p99": float(np.percentile(final_values, 99)),
        }

        prob_loss = float(np.sum(final_values < initial_value) / num_simulations)

        return {
            "mean_final_value": float(np.mean(final_values)),
            "median_final_value": float(np.median(final_values)),
            "p5_final_value": percentiles["p5"],
            "p95_final_value": percentiles["p95"],
            "probability_of_loss": prob_loss,
            "max_value": float(np.max(final_values)),
            "min_value": float(np.min(final_values)),
            "simulations_run": num_simulations,
            "percentiles": percentiles,
            "initial_value": initial_value,
            "time_horizon_days": time_horizon,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_optimization_result(
        self,
        weights: np.ndarray,
        symbols: List[str],
        mean_returns: pd.Series,
        cov_matrix: pd.DataFrame,
        method: str,
        risk_free_rate: float,
    ) -> Dict[str, Any]:
        """Package optimization result into a standard dictionary."""
        expected_return = float(np.dot(weights, mean_returns.values))
        expected_vol = float(
            np.sqrt(np.dot(weights.T, np.dot(cov_matrix.values, weights)))
        )
        sharpe = (
            (expected_return - risk_free_rate) / expected_vol
            if expected_vol > 1e-10
            else 0.0
        )
        return {
            "weights": {s: float(weights[i]) for i, s in enumerate(symbols)},
            "expected_return": expected_return,
            "expected_volatility": expected_vol,
            "sharpe_ratio": float(sharpe),
            "method": method,
            "symbols": symbols,
        }

    def _risk_parity_weights(
        self,
        cov_matrix_np: np.ndarray,
        bounds: List[Tuple[float, float]],
        num_assets: int,
    ) -> np.ndarray:
        """
        Compute risk-parity (equal risk contribution) weights.

        Falls back to inverse-volatility weighting if scipy is unavailable or
        the optimizer does not converge.
        """
        if not SCIPY_AVAILABLE:
            return self._inverse_vol_weights(cov_matrix_np)

        def _risk_parity_objective(w: np.ndarray) -> float:
            port_vol = np.sqrt(np.dot(w.T, np.dot(cov_matrix_np, w)))
            if port_vol < 1e-10:
                return 0.0
            marginal = np.dot(cov_matrix_np, w) / port_vol
            risk_contrib = w * marginal
            target_rc = port_vol / num_assets
            return float(np.sum((risk_contrib - target_rc) ** 2))

        init_w = np.ones(num_assets) / num_assets
        constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = minimize(
                _risk_parity_objective,
                init_w,
                method="SLSQP",
                bounds=bounds,
                constraints=constraints,
                options={"maxiter": 1000, "ftol": 1e-10},
            )

        if result.success:
            w = np.clip(result.x, 0, 1)
            return w / w.sum()
        return self._inverse_vol_weights(cov_matrix_np)

    @staticmethod
    def _inverse_vol_weights(cov_matrix_np: np.ndarray) -> np.ndarray:
        """Inverse-volatility weighting as a fallback for risk parity."""
        vols = np.sqrt(np.diag(cov_matrix_np))
        inv_vols = 1.0 / np.where(vols > 0, vols, 1.0)
        return inv_vols / inv_vols.sum()

    def _grid_search_optimize(
        self,
        returns_df: pd.DataFrame,
        symbols: List[str],
        mean_returns: pd.Series,
        cov_matrix: pd.DataFrame,
        bounds: List[Tuple[float, float]],
        target_return: Optional[float],
        risk_tolerance: Optional[float],
        method: str,
    ) -> Dict[str, Any]:
        """
        Fallback grid-search optimization when scipy is unavailable.

        Generates random portfolios and picks the best one matching criteria.
        """
        num_assets = len(symbols)
        risk_free_rate = 0.02
        best_sharpe = -np.inf
        best_vol = np.inf
        best_weights = np.ones(num_assets) / num_assets
        best_return = 0.0

        for _ in range(10000):
            w = np.random.random(num_assets)
            w /= w.sum()

            # Respect bounds approximately
            for idx, (lo, hi) in enumerate(bounds):
                w[idx] = np.clip(w[idx], lo, hi)
            if w.sum() > 0:
                w /= w.sum()

            port_ret = float(np.dot(w, mean_returns.values))
            port_vol = float(
                np.sqrt(np.dot(w.T, np.dot(cov_matrix.values, w)))
            )

            if target_return is not None and abs(port_ret - target_return) > 0.01:
                continue
            if risk_tolerance is not None and port_vol > risk_tolerance:
                continue

            sharpe = (
                (port_ret - risk_free_rate) / port_vol
                if port_vol > 1e-10
                else 0.0
            )

            if method in ("max_sharpe", "target_return") and sharpe > best_sharpe:
                best_sharpe = sharpe
                best_weights = w.copy()
                best_return = port_ret
                best_vol = port_vol
            elif method == "min_variance" and port_vol < best_vol:
                best_vol = port_vol
                best_weights = w.copy()
                best_return = port_ret
                best_sharpe = sharpe

        return {
            "weights": {s: float(best_weights[i]) for i, s in enumerate(symbols)},
            "expected_return": float(best_return),
            "expected_volatility": float(best_vol),
            "sharpe_ratio": float(best_sharpe),
            "method": method,
            "symbols": symbols,
        }


# Global instance for import convenience
portfolio_optimizer = PortfolioOptimizer()
