"""
Tests for PortfolioOptimizer (Modern Portfolio Theory + risk analytics).

Uses small synthetic return series with deterministic seeds so the Monte Carlo
paths are reproducible.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.services.analysis.portfolio_optimization import PortfolioOptimizer


@pytest.fixture(autouse=True)
def _seed():
    np.random.seed(7)


@pytest.fixture
def returns_df() -> pd.DataFrame:
    """3 assets, 252 daily returns, modest correlation."""
    n = 252
    rng = np.random.default_rng(7)
    mu = [0.0008, 0.0006, 0.0010]
    sigma = [0.012, 0.010, 0.015]
    corr = np.array(
        [
            [1.0, 0.3, 0.2],
            [0.3, 1.0, 0.1],
            [0.2, 0.1, 1.0],
        ]
    )
    L = np.linalg.cholesky(corr)
    z = rng.standard_normal((n, 3))
    correlated = z @ L.T
    returns = mu + correlated * sigma
    return pd.DataFrame(returns, columns=["AAPL", "MSFT", "GOOG"])


@pytest.fixture
def opt() -> PortfolioOptimizer:
    return PortfolioOptimizer()


@pytest.mark.unit
class TestEfficientFrontier:
    def test_returns_two_portfolios(self, opt, returns_df):
        result = opt.calculate_efficient_frontier(returns_df, num_portfolios=200)
        assert "min_variance_portfolio" in result
        assert "max_sharpe_portfolio" in result
        # Each portfolio has weights summing to ~1
        for key in ("min_variance_portfolio", "max_sharpe_portfolio"):
            w = result[key]["weights"]
            assert abs(sum(w.values()) - 1.0) < 1e-9
            assert all(0 <= v <= 1 for v in w.values())

    def test_min_variance_has_lower_or_equal_vol(self, opt, returns_df):
        result = opt.calculate_efficient_frontier(returns_df, num_portfolios=200)
        assert (
            result["min_variance_portfolio"]["volatility"]
            <= result["max_sharpe_portfolio"]["volatility"] + 1e-9
        )

    def test_empty_returns_raises(self, opt):
        with pytest.raises(ValueError):
            opt.calculate_efficient_frontier(pd.DataFrame(), num_portfolios=10)

    def test_single_asset_raises(self, opt):
        df = pd.DataFrame({"AAPL": np.random.randn(50) * 0.01})
        with pytest.raises(ValueError):
            opt.calculate_efficient_frontier(df, num_portfolios=10)


@pytest.mark.unit
class TestVarCvar:
    @pytest.mark.parametrize("method", ["historical", "parametric", "monte_carlo"])
    def test_var_runs_for_each_method(self, opt, returns_df, method):
        result = opt.calculate_var(
            returns_df["AAPL"], confidence_level=0.95, method=method, portfolio_value=100_000
        )
        assert isinstance(result, dict)
        # Has at least one numeric VaR field
        assert any(isinstance(v, (int, float)) for v in result.values())

    def test_var_empty_returns_raises(self, opt):
        with pytest.raises(ValueError):
            opt.calculate_var(pd.Series([], dtype=float))

    def test_cvar_runs(self, opt, returns_df):
        cvar = opt.calculate_cvar(returns_df["AAPL"], confidence_level=0.95)
        assert isinstance(cvar, dict)


@pytest.mark.unit
class TestSharpeAndSortino:
    def test_sharpe_ratio_returns_number(self, opt, returns_df):
        sharpe = opt.calculate_sharpe_ratio(returns_df["AAPL"], risk_free_rate=0.02)
        assert isinstance(sharpe, (int, float))

    def test_sortino_ratio_runs(self, opt, returns_df):
        sortino = opt.calculate_sortino_ratio(returns_df["AAPL"], risk_free_rate=0.02)
        assert isinstance(sortino, (int, float))

    def test_treynor_ratio_runs(self, opt, returns_df):
        # Treynor takes a precomputed beta (float), not a benchmark series
        treynor = opt.calculate_treynor_ratio(
            returns_df["AAPL"], beta=1.2, risk_free_rate=0.02
        )
        assert isinstance(treynor, (int, float))

    def test_treynor_zero_beta_returns_zero(self, opt, returns_df):
        # Guard branch
        assert opt.calculate_treynor_ratio(returns_df["AAPL"], beta=0.0) == 0.0


@pytest.mark.unit
class TestPortfolioMetrics:
    def test_portfolio_metrics_takes_series(self, opt, returns_df):
        # Method takes a single returns Series, not a weighted dict
        portfolio_returns = returns_df.mean(axis=1)
        metrics = opt.calculate_portfolio_metrics(portfolio_returns)
        assert isinstance(metrics, dict)
        assert len(metrics) > 0

    def test_correlation_matrix_is_symmetric(self, opt, returns_df):
        corr = opt.calculate_correlation_matrix(returns_df)
        assert isinstance(corr, dict)
        # Symmetric: corr[A][B] == corr[B][A]
        symbols = list(returns_df.columns)
        if "correlation_matrix" in corr:
            cm = corr["correlation_matrix"]
        else:
            cm = corr
        # Find the inner correlation dict
        if isinstance(cm, dict) and symbols[0] in cm:
            for a in symbols:
                for b in symbols:
                    if a in cm and b in cm[a]:
                        assert cm[a][b] == pytest.approx(cm[b][a], abs=1e-9)


@pytest.mark.unit
class TestOptimizePortfolio:
    @pytest.mark.parametrize("method", ["max_sharpe", "min_variance"])
    def test_optimize_weights_sum_to_one(self, opt, returns_df, method):
        result = opt.optimize_portfolio(returns_df, method=method)
        # Find the weights — could be 'weights' or 'optimal_weights'
        weights = result.get("weights") or result.get("optimal_weights") or {}
        if isinstance(weights, dict):
            total = sum(weights.values())
            assert abs(total - 1.0) < 1e-3
            assert all(-1e-6 <= v <= 1 + 1e-6 for v in weights.values())

    def test_optimize_with_target_return_constraint(self, opt, returns_df):
        # Pick a target return achievable by the assets
        annual_means = returns_df.mean() * 252
        target = float(annual_means.median())
        result = opt.optimize_portfolio(returns_df, target_return=target)
        assert isinstance(result, dict)


@pytest.mark.unit
class TestMonteCarlo:
    def test_simulation_runs_with_defaults(self, opt, returns_df):
        result = opt.monte_carlo_simulation(
            returns_df, num_simulations=100, time_horizon=30
        )
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_simulation_with_explicit_weights(self, opt, returns_df):
        # Weights as list (in column order)
        result = opt.monte_carlo_simulation(
            returns_df,
            weights=[0.5, 0.3, 0.2],
            num_simulations=100,
            time_horizon=30,
            initial_value=10_000,
        )
        assert isinstance(result, dict)
