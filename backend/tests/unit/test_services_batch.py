"""
Batch tests for self-contained service modules:
- SentimentAnalyzer
- RiskEngine
- ScreenerService
- NotificationService
- TradingEngine (paper trading)

All modules use in-memory state or pure functions, so no DB or external API
mocking is required.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import numpy as np
import pytest

from app.services.sentiment.analyzer import SentimentAnalyzer
from app.services.risk.risk_engine import RiskEngine, STRESS_SCENARIOS, MOCK_PORTFOLIO
from app.services.screener.screener_service import ScreenerService
from app.services.notifications.notification_service import NotificationService
from app.services.paper_trading.trading_engine import TradingEngine
from app.schemas.notifications import AlertCondition, CreateAlertRequest
from app.schemas.screener import ScreenerFilter
from app.schemas.paper_trading import PlaceOrderRequest, OrderSide, OrderType


# ===========================================================================
# SentimentAnalyzer
# ===========================================================================


@pytest.fixture
def sa() -> SentimentAnalyzer:
    return SentimentAnalyzer()


@pytest.mark.unit
class TestSentimentAnalyzer:
    def test_positive_text_scores_positive(self, sa):
        r = sa.analyze_article("Strong buy rating. Earnings beat estimates and revenue growth surged.")
        assert r["score"] > 0
        assert r["label"] == "positive"
        assert 0 < r["confidence"] <= 1.0

    def test_negative_text_scores_negative(self, sa):
        r = sa.analyze_article("Bearish outlook. Massive losses, downgrade, plunge expected.")
        assert r["score"] < 0
        assert r["label"] == "negative"

    def test_empty_text_returns_neutral(self, sa):
        r = sa.analyze_article("")
        assert r["score"] == 0.0
        assert r["label"] == "neutral"
        assert r["confidence"] == 0.0

    def test_unrelated_text_returns_neutral(self, sa):
        r = sa.analyze_article("The weather is nice today and the sky is blue.")
        # No financial keywords — neutral
        assert r["label"] == "neutral"

    def test_negation_flips_sentiment(self, sa):
        without_negation = sa.analyze_article("Profits surged this quarter")
        with_negation = sa.analyze_article("No profits this quarter")
        # Negation should reduce or invert
        assert with_negation["score"] < without_negation["score"]

    def test_analyze_batch_preserves_fields(self, sa):
        articles = [
            {"title": "Bullish breakout", "summary": ""},
            {"title": "Bearish crash", "summary": ""},
        ]
        result = sa.analyze_batch(articles)
        assert len(result) == 2
        assert all("sentiment_score" in a and "sentiment_label" in a for a in result)
        # Original fields preserved
        assert result[0]["title"] == "Bullish breakout"

    def test_aggregate_sentiment_with_articles(self, sa):
        now = datetime.now(timezone.utc)
        articles = [
            {"sentiment_score": 0.5, "sentiment_label": "positive", "published_at": now.isoformat()},
            {"sentiment_score": -0.4, "sentiment_label": "negative", "published_at": (now - timedelta(days=3)).isoformat()},
            {"sentiment_score": 0.1, "sentiment_label": "neutral", "published_at": (now - timedelta(days=10)).isoformat()},
        ]
        agg = sa.compute_aggregate_sentiment(articles, "AAPL")
        assert agg["symbol"] == "AAPL"
        assert agg["article_count"] == 3
        assert agg["positive_count"] == 1
        assert agg["negative_count"] == 1
        assert agg["neutral_count"] == 1
        assert agg["sentiment_trend"] in ("stable", "improving", "declining")

    def test_aggregate_with_no_articles(self, sa):
        agg = sa.compute_aggregate_sentiment([], "AAPL")
        assert agg["article_count"] == 0
        assert agg["overall_label"] == "neutral"
        assert agg["overall_score"] == 0.0

    def test_get_financial_keywords(self, sa):
        kw = sa.get_financial_keywords()
        assert "positive" in kw and "negative" in kw
        assert isinstance(kw["positive"], list) and len(kw["positive"]) > 0
        assert isinstance(kw["negative"], list) and len(kw["negative"]) > 0


# ===========================================================================
# RiskEngine
# ===========================================================================


@pytest.fixture
def risk() -> RiskEngine:
    return RiskEngine()


@pytest.fixture
def returns_arr() -> np.ndarray:
    rng = np.random.default_rng(42)
    return rng.normal(0.0004, 0.012, 252)


@pytest.mark.unit
class TestRiskEngine:
    def test_var_historical(self, risk, returns_arr):
        var_pct, abs_var = risk.calculate_var_historical(returns_arr, 0.95, 1)
        assert var_pct < 0  # losses are negative
        assert abs_var > 0

    def test_var_parametric(self, risk, returns_arr):
        var_pct, abs_var = risk.calculate_var_parametric(returns_arr, 0.95, 1)
        assert abs_var > 0

    def test_var_monte_carlo(self, risk, returns_arr):
        var_pct, abs_var = risk.calculate_var_monte_carlo(returns_arr, 0.95, 1, simulations=1000)
        assert abs_var > 0

    def test_cvar_at_least_var(self, risk, returns_arr):
        _, abs_var = risk.calculate_var_historical(returns_arr, 0.95, 1)
        _, abs_cvar = risk.calculate_cvar(returns_arr, 0.95, 1)
        assert abs_cvar >= abs_var - 1e-9

    def test_max_drawdown(self, risk, returns_arr):
        dd = risk.calculate_max_drawdown(returns_arr)
        assert dd["max_drawdown"] >= 0
        assert dd["max_drawdown_duration_days"] >= 0

    def test_sharpe_ratio(self, risk, returns_arr):
        sharpe = risk.calculate_sharpe_ratio(returns_arr, risk_free_rate=0.05)
        assert isinstance(sharpe, float)

    def test_sortino_ratio(self, risk, returns_arr):
        sortino = risk.calculate_sortino_ratio(returns_arr, risk_free_rate=0.05)
        assert isinstance(sortino, float)

    def test_run_stress_test_all_scenarios(self, risk):
        for scenario_name in STRESS_SCENARIOS:
            result = risk.run_stress_test(
                MOCK_PORTFOLIO["positions"], scenario_name, MOCK_PORTFOLIO["total_value"]
            )
            assert result is not None
            assert result["scenario"] == scenario_name
            assert "portfolio_impact_percentage" in result

    def test_run_stress_test_unknown_scenario(self, risk):
        assert risk.run_stress_test([], "totally_made_up_scenario", 100) is None

    def test_calculate_risk_score(self, risk):
        result = risk.calculate_risk_score(MOCK_PORTFOLIO)
        assert "overall_score" in result
        assert "rating" in result
        assert result["rating"] in ("Low", "Moderate", "High", "Very High")

    def test_get_returns_is_cached(self, risk):
        a = risk._get_returns("portfolio-A")
        b = risk._get_returns("portfolio-A")
        # Same array returned (cached)
        assert a is b

    @pytest.mark.asyncio
    async def test_analyze_portfolio_runs(self, risk):
        request = SimpleNamespace(
            portfolio_id="p1",
            confidence_level=0.95,
            time_horizon_days=1,
            method="historical",
            include_stress_tests=True,
        )
        result = await risk.analyze_portfolio(request)
        assert isinstance(result, dict)
        assert "var_analysis" in result or "var_amount" in str(result)


# ===========================================================================
# ScreenerService
# ===========================================================================


@pytest.fixture
def screener() -> ScreenerService:
    return ScreenerService()


@pytest.mark.unit
class TestScreenerService:
    def test_run_screener_no_filters(self, screener):
        filters = ScreenerFilter()
        result = screener.run_screener(filters)
        assert "results" in result
        assert "total_results" in result
        assert result["total_results"] > 0

    def test_run_screener_with_pe_max(self, screener):
        filters = ScreenerFilter(pe_ratio_max=15)
        result = screener.run_screener(filters)
        for stock in result["results"]:
            if stock.pe_ratio is not None:
                assert stock.pe_ratio <= 15

    def test_run_screener_with_market_cap_filter(self, screener):
        filters = ScreenerFilter(market_cap_min=500_000_000_000)  # 500B+
        result = screener.run_screener(filters)
        for stock in result["results"]:
            assert stock.market_cap >= 500_000_000_000

    def test_run_screener_with_sector_filter(self, screener):
        filters = ScreenerFilter(sector=["Technology"])
        result = screener.run_screener(filters)
        for stock in result["results"]:
            assert stock.sector == "Technology"

    def test_run_screener_with_dividend_filter(self, screener):
        filters = ScreenerFilter(dividend_yield_min=3.0)
        result = screener.run_screener(filters)
        for stock in result["results"]:
            if stock.dividend_yield is not None:
                assert stock.dividend_yield >= 3.0

    def test_run_screener_sort_order(self, screener):
        filters = ScreenerFilter(sort_by="market_cap", sort_order="desc")
        result = screener.run_screener(filters)
        caps = [s.market_cap for s in result["results"]]
        assert caps == sorted(caps, reverse=True)

    def test_get_presets_returns_list(self, screener):
        presets = screener.get_presets()
        assert isinstance(presets, list)
        assert len(presets) >= 5

    def test_get_specific_preset(self, screener):
        preset = screener.get_preset("value")
        assert preset is not None
        assert preset.name == "Value Stocks"

    def test_get_unknown_preset(self, screener):
        assert screener.get_preset("does-not-exist") is None

    def test_save_and_retrieve_screener(self, screener):
        user_id = f"user-{uuid4()}"
        filters = ScreenerFilter(pe_ratio_max=20)
        save_result = screener.save_screener(user_id, "My Screener", filters)
        assert "id" in save_result
        screener_id = save_result["id"]
        retrieved = screener.get_user_screeners(user_id)
        assert any(s["id"] == screener_id for s in retrieved)

    def test_delete_screener(self, screener):
        user_id = f"user-{uuid4()}"
        save_result = screener.save_screener(
            user_id, "To Delete", ScreenerFilter()
        )
        deleted = screener.delete_screener(user_id, save_result["id"])
        assert deleted is True
        assert all(s["id"] != save_result["id"] for s in screener.get_user_screeners(user_id))


# ===========================================================================
# NotificationService
# ===========================================================================


@pytest.fixture
def notif() -> NotificationService:
    return NotificationService()


@pytest.mark.unit
class TestNotificationService:
    def _user(self):
        return f"user-{uuid4()}"

    def test_create_and_get_alert(self, notif):
        user_id = self._user()
        req = CreateAlertRequest(
            name="AAPL hit $200",
            condition=AlertCondition(type="price_above", symbol="AAPL", threshold=200.0),
        )
        alert = notif.create_alert(user_id, req)
        assert alert.name == "AAPL hit $200"
        assert alert.is_active is True
        alerts = notif.get_alerts(user_id)
        assert len(alerts) == 1

    def test_update_alert(self, notif):
        user_id = self._user()
        alert = notif.create_alert(
            user_id,
            CreateAlertRequest(
                name="x",
                condition=AlertCondition(type="price_above", threshold=100),
            ),
        )
        updated = notif.update_alert(user_id, alert.id, {"is_active": False, "name": "x2"})
        assert updated is not None
        assert updated.is_active is False
        assert updated.name == "x2"

    def test_update_unknown_alert(self, notif):
        assert notif.update_alert("nobody", "nope", {"is_active": False}) is None

    def test_delete_alert(self, notif):
        user_id = self._user()
        alert = notif.create_alert(
            user_id,
            CreateAlertRequest(
                name="x", condition=AlertCondition(type="price_above", threshold=100)
            ),
        )
        assert notif.delete_alert(user_id, alert.id) is True
        assert notif.get_alerts(user_id) == []

    def test_delete_unknown_alert(self, notif):
        assert notif.delete_alert("nobody", "nope") is False

    def test_create_notification(self, notif):
        user_id = self._user()
        n = notif.create_notification(user_id, "Title", "Body", severity="warning")
        assert n.title == "Title"
        assert n.severity == "warning"
        assert n.is_read is False

    def test_notification_pagination(self, notif):
        user_id = self._user()
        for i in range(5):
            notif.create_notification(user_id, f"Title {i}", "body")
        result = notif.get_notifications(user_id, limit=2, offset=0)
        assert result["total"] == 5
        assert len(result["notifications"]) == 2
        assert result["unread_count"] == 5

    def test_mark_as_read(self, notif):
        user_id = self._user()
        n = notif.create_notification(user_id, "T", "B")
        assert notif.mark_as_read(user_id, n.id) is True
        assert notif.get_unread_count(user_id) == 0

    def test_mark_all_read(self, notif):
        user_id = self._user()
        for i in range(3):
            notif.create_notification(user_id, f"T{i}", "B")
        marked = notif.mark_all_read(user_id)
        assert marked == 3
        assert notif.get_unread_count(user_id) == 0

    def test_delete_notification(self, notif):
        user_id = self._user()
        n = notif.create_notification(user_id, "T", "B")
        assert notif.delete_notification(user_id, n.id) is True
        result = notif.get_notifications(user_id)
        assert result["total"] == 0

    def test_delete_unknown_notification(self, notif):
        assert notif.delete_notification("nobody", "nope") is False


# ===========================================================================
# TradingEngine (paper trading)
# ===========================================================================


@pytest.fixture
def pt() -> TradingEngine:
    return TradingEngine()


@pytest.fixture
def pt_user_id():
    return f"user-{uuid4()}"


@pytest.mark.unit
class TestPaperTradingEngine:
    def test_create_portfolio(self, pt, pt_user_id):
        portfolio = pt.create_portfolio(pt_user_id, "My Port", initial_capital=50000.0)
        assert portfolio.initial_capital == 50000.0
        assert portfolio.cash_balance == 50000.0
        assert portfolio.total_trades == 0

    def test_get_portfolio_returns_none_before_create(self, pt):
        new_user = f"user-{uuid4()}"
        assert pt.get_portfolio(new_user) is None

    def test_place_buy_order_reduces_cash(self, pt, pt_user_id):
        pt.create_portfolio(pt_user_id, "X", initial_capital=100_000)
        order = PlaceOrderRequest(
            symbol="AAPL", side=OrderSide.BUY,
            order_type=OrderType.MARKET, quantity=10,
        )
        result = pt.place_order(pt_user_id, order)
        assert result.status.value == "filled"
        portfolio = pt.get_portfolio(pt_user_id)
        # Cash reduced; AAPL position added
        assert portfolio.cash_balance < 100_000

    def test_place_order_without_portfolio_rejected(self, pt):
        new_user = f"user-{uuid4()}"
        order = PlaceOrderRequest(
            symbol="AAPL", side=OrderSide.BUY,
            order_type=OrderType.MARKET, quantity=10,
        )
        result = pt.place_order(new_user, order)
        assert result.status.value == "rejected"

    def test_place_sell_without_position_rejected(self, pt, pt_user_id):
        pt.create_portfolio(pt_user_id, "X", initial_capital=100_000)
        order = PlaceOrderRequest(
            symbol="AAPL", side=OrderSide.SELL,
            order_type=OrderType.MARKET, quantity=10,
        )
        result = pt.place_order(pt_user_id, order)
        assert result.status.value == "rejected"
        assert "No position" in result.message

    def test_place_limit_order_with_no_price_rejected(self, pt, pt_user_id):
        pt.create_portfolio(pt_user_id, "X", initial_capital=100_000)
        order = PlaceOrderRequest(
            symbol="AAPL", side=OrderSide.BUY,
            order_type=OrderType.LIMIT, quantity=10, price=None,
        )
        result = pt.place_order(pt_user_id, order)
        assert result.status.value == "rejected"

    def test_insufficient_cash_rejected(self, pt, pt_user_id):
        pt.create_portfolio(pt_user_id, "X", initial_capital=100)
        order = PlaceOrderRequest(
            symbol="AAPL", side=OrderSide.BUY,
            order_type=OrderType.MARKET, quantity=1000,
        )
        result = pt.place_order(pt_user_id, order)
        assert result.status.value == "rejected"
        assert "Insufficient cash" in result.message

    def test_close_position(self, pt, pt_user_id):
        pt.create_portfolio(pt_user_id, "X", initial_capital=100_000)
        buy = PlaceOrderRequest(
            symbol="MSFT", side=OrderSide.BUY,
            order_type=OrderType.MARKET, quantity=5,
        )
        pt.place_order(pt_user_id, buy)
        close = pt.close_position(pt_user_id, "MSFT")
        assert close is not None
        assert close.status.value == "filled"
        # Position should be gone
        positions = pt.get_positions(pt_user_id)
        assert all(p.symbol != "MSFT" for p in positions)

    def test_close_position_unknown_symbol(self, pt, pt_user_id):
        pt.create_portfolio(pt_user_id, "X", initial_capital=100_000)
        assert pt.close_position(pt_user_id, "NOSUCH") is None

    def test_get_performance_no_portfolio(self, pt):
        new_user = f"user-{uuid4()}"
        perf = pt.get_performance(new_user)
        assert perf["total_trades"] == 0

    def test_get_performance_after_trade(self, pt, pt_user_id):
        pt.create_portfolio(pt_user_id, "X", initial_capital=100_000)
        order = PlaceOrderRequest(
            symbol="AAPL", side=OrderSide.BUY,
            order_type=OrderType.MARKET, quantity=10,
        )
        pt.place_order(pt_user_id, order)
        perf = pt.get_performance(pt_user_id)
        assert perf["total_trades"] >= 1

    def test_get_leaderboard(self, pt, pt_user_id):
        pt.create_portfolio(pt_user_id, "X", initial_capital=100_000)
        lb = pt.get_leaderboard()
        assert isinstance(lb, list)

    def test_get_trade_history(self, pt, pt_user_id):
        pt.create_portfolio(pt_user_id, "X", initial_capital=100_000)
        pt.place_order(
            pt_user_id,
            PlaceOrderRequest(
                symbol="GOOGL", side=OrderSide.BUY,
                order_type=OrderType.MARKET, quantity=5,
            ),
        )
        trades = pt.get_trade_history(pt_user_id)
        assert len(trades) >= 1
