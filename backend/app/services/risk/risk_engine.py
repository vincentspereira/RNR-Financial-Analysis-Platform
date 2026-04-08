"""
Risk analysis engine for portfolio risk management.

Provides VaR calculations (historical, parametric, Monte Carlo),
stress testing, drawdown analysis, and composite risk scoring.
"""
import hashlib
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from app.core.logging import get_logger

logger = get_logger("app.services.risk.engine")

# Predefined stress test scenarios
STRESS_SCENARIOS = {
    "market_crash": {
        "description": "Severe market downturn similar to 2008 financial crisis",
        "impacts": {
            "Technology": -0.35, "Healthcare": -0.20, "Financials": -0.40,
            "Consumer Discretionary": -0.30, "Energy": -0.25, "Industrials": -0.30,
            "default": -0.30,
        },
    },
    "interest_rate_hike": {
        "description": "Aggressive interest rate hikes by central bank",
        "impacts": {
            "Technology": -0.08, "Healthcare": -0.05, "Financials": -0.02,
            "Real Estate": -0.20, "Utilities": -0.15, "default": -0.10,
        },
    },
    "recession": {
        "description": "Economic recession with declining GDP and rising unemployment",
        "impacts": {
            "Consumer Discretionary": -0.35, "Industrials": -0.30, "Financials": -0.25,
            "Energy": -0.20, "default": -0.20,
        },
    },
    "inflation_spike": {
        "description": "Sharp increase in inflation reducing purchasing power",
        "impacts": {
            "Technology": -0.08, "Consumer Staples": -0.02, "Energy": 0.10,
            "Materials": 0.05, "default": -0.05,
        },
    },
    "black_swan": {
        "description": "Extreme unforeseen event affecting all asset classes",
        "impacts": {"default": -0.45},
    },
}

# Mock portfolio positions for demo
MOCK_PORTFOLIO = {
    "positions": [
        {"symbol": "AAPL", "sector": "Technology", "value": 35000, "weight": 0.28},
        {"symbol": "MSFT", "sector": "Technology", "value": 25000, "weight": 0.20},
        {"symbol": "GOOGL", "sector": "Technology", "value": 15000, "weight": 0.12},
        {"symbol": "JPM", "sector": "Financials", "value": 18000, "weight": 0.144},
        {"symbol": "JNJ", "sector": "Healthcare", "value": 12000, "weight": 0.096},
        {"symbol": "XOM", "sector": "Energy", "value": 8000, "weight": 0.064},
        {"symbol": "PG", "sector": "Consumer Staples", "value": 7000, "weight": 0.056},
        {"symbol": "AMZN", "sector": "Consumer Discretionary", "value": 5000, "weight": 0.04},
    ],
    "total_value": 125000,
}


def _generate_returns(days: int = 252, seed: int = 42) -> np.ndarray:
    """Generate simulated daily returns for analysis."""
    rng = np.random.default_rng(seed)
    return rng.normal(0.0004, 0.012, days)


class RiskEngine:
    """Core risk analysis engine."""

    def __init__(self):
        self.returns_cache: Dict[str, np.ndarray] = {}

    def _get_returns(self, portfolio_id: str) -> np.ndarray:
        """Get or generate returns for a portfolio."""
        if portfolio_id not in self.returns_cache:
            seed = int(hashlib.md5(portfolio_id.encode()).hexdigest()[:8], 16) % (2**31)
            self.returns_cache[portfolio_id] = _generate_returns(seed=seed)
        return self.returns_cache[portfolio_id]

    def calculate_var_historical(
        self, returns: np.ndarray, confidence: float, horizon: int
    ) -> Tuple[float, float]:
        """Historical VaR using percentile method."""
        scaled_returns = returns * np.sqrt(horizon)
        var_pct = np.percentile(scaled_returns, (1 - confidence) * 100)
        return var_pct, abs(var_pct)

    def calculate_var_parametric(
        self, returns: np.ndarray, confidence: float, horizon: int
    ) -> Tuple[float, float]:
        """Parametric VaR assuming normal distribution."""
        from scipy import stats as sp_stats
        mu = np.mean(returns) * horizon
        sigma = np.std(returns, ddof=1) * np.sqrt(horizon)
        z_score = sp_stats.norm.ppf(1 - confidence)
        var_pct = mu + z_score * sigma
        return var_pct, abs(var_pct)

    def calculate_var_monte_carlo(
        self, returns: np.ndarray, confidence: float, horizon: int,
        simulations: int = 10000
    ) -> Tuple[float, float]:
        """Monte Carlo VaR simulation."""
        rng = np.random.default_rng(42)
        mu = np.mean(returns)
        sigma = np.std(returns, ddof=1)

        sim_returns = rng.normal(mu * horizon, sigma * np.sqrt(horizon), simulations)
        var_pct = np.percentile(sim_returns, (1 - confidence) * 100)
        return var_pct, abs(var_pct)

    def calculate_cvar(
        self, returns: np.ndarray, confidence: float, horizon: int = 1
    ) -> Tuple[float, float]:
        """Conditional VaR (Expected Shortfall)."""
        scaled_returns = returns * np.sqrt(horizon)
        var_threshold = np.percentile(scaled_returns, (1 - confidence) * 100)
        tail_returns = scaled_returns[scaled_returns <= var_threshold]
        if len(tail_returns) == 0:
            tail_returns = np.array([var_threshold])
        cvar_pct = np.mean(tail_returns)
        return cvar_pct, abs(cvar_pct)

    def calculate_max_drawdown(self, returns: np.ndarray) -> Dict[str, Any]:
        """Calculate maximum drawdown statistics."""
        cumulative = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdowns = (cumulative - running_max) / running_max

        max_dd = abs(np.min(drawdowns)) * 100

        # Find duration of max drawdown
        max_dd_idx = np.argmin(drawdowns)
        peak_idx = np.argmax(cumulative[:max_dd_idx + 1])
        duration_days = int(max_dd_idx - peak_idx)

        # Current drawdown
        current_dd = abs(drawdowns[-1]) * 100

        # Recovery time estimate
        recovery_days = None
        if max_dd_idx < len(cumulative) - 1:
            post_dd = cumulative[max_dd_idx:]
            peak_val = running_max[max_dd_idx]
            recovery_points = np.where(post_dd >= peak_val)[0]
            if len(recovery_points) > 0:
                recovery_days = int(recovery_points[0])

        return {
            "max_drawdown": round(max_dd, 2),
            "max_drawdown_duration_days": duration_days,
            "current_drawdown": round(current_dd, 2),
            "recovery_time_days": recovery_days,
        }

    def calculate_sharpe_ratio(self, returns: np.ndarray, risk_free_rate: float = 0.05) -> float:
        """Calculate annualized Sharpe ratio."""
        excess_returns = returns - risk_free_rate / 252
        if np.std(excess_returns, ddof=1) == 0:
            return 0.0
        return float(np.mean(excess_returns) / np.std(excess_returns, ddof=1) * np.sqrt(252))

    def calculate_sortino_ratio(self, returns: np.ndarray, risk_free_rate: float = 0.05) -> float:
        """Calculate annualized Sortino ratio."""
        excess_returns = returns - risk_free_rate / 252
        downside_returns = excess_returns[excess_returns < 0]
        if len(downside_returns) == 0 or np.std(downside_returns, ddof=1) == 0:
            return 0.0
        return float(np.mean(excess_returns) / np.std(downside_returns, ddof=1) * np.sqrt(252))

    def run_stress_test(
        self, positions: List[Dict], scenario_name: str, total_value: float
    ) -> Dict[str, Any]:
        """Run a single stress test scenario on portfolio positions."""
        scenario = STRESS_SCENARIOS.get(scenario_name)
        if not scenario:
            return None

        impacts = scenario["impacts"]
        total_impact_pct = 0.0
        worst_position = ""
        worst_impact = 0.0

        for pos in positions:
            sector = pos.get("sector", "default")
            weight = pos.get("weight", 0)
            impact = impacts.get(sector, impacts.get("default", -0.10))
            weighted_impact = impact * weight
            total_impact_pct += weighted_impact

            if abs(impact) > abs(worst_impact):
                worst_impact = impact * 100
                worst_position = pos.get("symbol", "Unknown")

        return {
            "scenario": scenario_name,
            "description": scenario["description"],
            "portfolio_impact_percentage": round(total_impact_pct * 100, 2),
            "portfolio_impact_amount": round(abs(total_impact_pct * total_value), 2),
            "worst_position": worst_position,
            "worst_position_impact": round(worst_impact, 2),
        }

    def calculate_risk_score(self, portfolio_data: Dict) -> Dict[str, Any]:
        """Calculate composite risk score for a portfolio."""
        positions = portfolio_data.get("positions", [])

        # Volatility risk (based on portfolio concentration)
        weights = [p.get("weight", 0) for p in positions]
        hhi = sum(w ** 2 for w in weights) if weights else 1
        volatility_risk = min(100, hhi * 200 + 15)

        # Concentration risk
        max_weight = max(weights) if weights else 1
        concentration_risk = min(100, max_weight * 150 + 10)

        # Liquidity risk (mock based on market cap proxy)
        liquidity_risk = 20.0  # Assume large cap = low liquidity risk

        # Market risk (based on beta proxy)
        market_risk = 45.0  # Average market risk

        overall = (
            volatility_risk * 0.3
            + concentration_risk * 0.3
            + liquidity_risk * 0.15
            + market_risk * 0.25
        )

        if overall <= 25:
            rating = "Low"
        elif overall <= 50:
            rating = "Moderate"
        elif overall <= 75:
            rating = "High"
        else:
            rating = "Very High"

        return {
            "overall_score": round(overall, 1),
            "volatility_risk": round(volatility_risk, 1),
            "concentration_risk": round(concentration_risk, 1),
            "liquidity_risk": round(liquidity_risk, 1),
            "market_risk": round(market_risk, 1),
            "rating": rating,
        }

    async def analyze_portfolio(self, request) -> Dict[str, Any]:
        """Run full risk analysis on a portfolio."""
        portfolio = MOCK_PORTFOLIO
        returns = self._get_returns(request.portfolio_id)
        total_value = portfolio["total_value"]
        positions = portfolio["positions"]

        # VaR analysis
        confidence = request.confidence_level
        horizon = request.time_horizon_days

        if request.method == "parametric":
            var_pct, _ = self.calculate_var_parametric(returns, confidence, horizon)
        elif request.method == "monte_carlo":
            var_pct, _ = self.calculate_var_monte_carlo(returns, confidence, horizon)
        else:
            var_pct, _ = self.calculate_var_historical(returns, confidence, horizon)

        cvar_pct, _ = self.calculate_cvar(returns, confidence, horizon)

        var_analysis = {
            "method": request.method,
            "confidence_level": confidence,
            "time_horizon_days": horizon,
            "var_amount": round(abs(var_pct) * total_value, 2),
            "var_percentage": round(abs(var_pct) * 100, 4),
            "cvar_amount": round(abs(cvar_pct) * total_value, 2),
            "cvar_percentage": round(abs(cvar_pct) * 100, 4),
        }

        # Drawdown
        drawdown = self.calculate_max_drawdown(returns)

        # Risk score
        risk_score = self.calculate_risk_score(portfolio)

        # Stress tests
        stress_tests = []
        if request.include_stress_tests:
            for scenario_name in STRESS_SCENARIOS:
                result = self.run_stress_test(positions, scenario_name, total_value)
                if result:
                    stress_tests.append(result)

        # Risk factors
        sharpe = self.calculate_sharpe_ratio(returns)
        sortino = self.calculate_sortino_ratio(returns)
        risk_factors = {
            "sharpe_ratio": round(sharpe, 3),
            "sortino_ratio": round(sortino, 3),
            "annualized_volatility": round(float(np.std(returns, ddof=1) * np.sqrt(252) * 100), 2),
            "annualized_return": round(float(np.mean(returns) * 252 * 100), 2),
            "beta": round(1.0 + np.random.uniform(-0.3, 0.3), 3),
        }

        return {
            "portfolio_id": request.portfolio_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "var_analysis": var_analysis,
            "drawdown": drawdown,
            "risk_score": risk_score,
            "stress_tests": stress_tests,
            "risk_factors": risk_factors,
        }


risk_engine = RiskEngine()
