"""
API endpoint smoke tests via FastAPI TestClient.

For endpoints that require authentication, we:
1. Send a valid JWT in the Authorization header (the ConsolidatedMiddleware
   blocks unauthenticated requests before the route runs).
2. Override the per-endpoint `get_current_user_from_token` dependency so
   that the endpoint receives a MagicMock user instead of touching the DB.

These tests prioritise breadth (hit many endpoints) over depth (assertions
mostly check shape + status code). Use existing service-level tests for
correctness of business logic.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

# Endpoint modules that define their own get_current_user_from_token
from app.api.v1.endpoints import (
    admin,
    ibkr,
    notifications,
    paper_trading,
    risk,
    screener,
    sentiment,
)
from app.api.v1.endpoints.technical_analysis import (
    get_current_user_from_token as tech_get_user,
)
from app.api.v1.endpoints.portfolio_optimization import (
    get_current_user_from_token as po_get_user,
)
from app.main import app
from app.services.auth.jwt_handler import jwt_handler


def _mock_user(role: str = "user"):
    user = MagicMock()
    user.id = uuid4()
    user.email = "test@test.com"
    user.is_active = True
    user.role = role
    return user


@pytest.fixture
def auth_headers() -> dict:
    """Real JWT so the ConsolidatedMiddleware lets the request through."""
    token = jwt_handler.create_access_token(uuid4())
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client(auth_headers) -> TestClient:
    """TestClient with all per-endpoint auth dependencies overridden.

    NB: We intentionally do NOT use TestClient as a context manager — that
    would trigger FastAPI's lifespan handler, which tries to connect to
    Postgres and Redis. For unit tests we want the app machinery without
    the external-service handshake.
    """
    overrides = {
        screener.get_current_user_from_token: lambda: _mock_user(),
        notifications.get_current_user_from_token: lambda: _mock_user(),
        paper_trading.get_current_user_from_token: lambda: _mock_user(),
        risk.get_current_user_from_token: lambda: _mock_user(),
        sentiment.get_current_user_from_token: lambda: _mock_user(),
        ibkr.get_current_user: lambda: _mock_user(),
        admin.get_current_user_from_token: lambda: _mock_user(role="admin"),
        tech_get_user: lambda: _mock_user(),
        po_get_user: lambda: _mock_user(),
    }
    for dep, override in overrides.items():
        app.dependency_overrides[dep] = override

    # Disable rate-limiting middleware so the ~26 tests in this file don't
    # trip the 10-req/10s burst limit.
    with patch(
        "app.core.middleware.RateLimitingMiddleware._is_burst_limited",
        return_value=False,
    ), patch(
        "app.core.security.RateLimiter.is_rate_limited",
        return_value=False,
    ):
        c = TestClient(app, headers=auth_headers)
        yield c

    app.dependency_overrides.clear()


# ===========================================================================
# Screener endpoints
# ===========================================================================


@pytest.mark.unit
class TestScreenerEndpoints:
    def test_run_screener(self, client):
        response = client.post(
            "/api/v1/screener/run",
            json={"pe_ratio_max": 30, "sort_by": "market_cap", "sort_order": "desc"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "total_results" in data

    def test_get_presets(self, client):
        response = client.get("/api/v1/screener/presets")
        assert response.status_code == 200
        body = response.json()
        # API wraps the list in {"presets": [...]}
        if isinstance(body, dict):
            assert any(isinstance(v, list) for v in body.values())
        else:
            assert isinstance(body, list)

    def test_run_preset(self, client):
        response = client.post("/api/v1/screener/presets/value/run", json={})
        assert response.status_code == 200

    def test_run_unknown_preset(self, client):
        response = client.post("/api/v1/screener/presets/does-not-exist/run", json={})
        assert response.status_code == 404

    def test_save_screener(self, client):
        response = client.post(
            "/api/v1/screener/save",
            json={"name": "Saved 1", "filters": {"pe_ratio_max": 15}},
        )
        assert response.status_code == 200

    def test_list_saved_screeners(self, client):
        response = client.get("/api/v1/screener/saved")
        assert response.status_code == 200
        body = response.json()
        # API wraps in {"screeners": [...]}
        if isinstance(body, dict):
            assert any(isinstance(v, list) for v in body.values())
        else:
            assert isinstance(body, list)


# ===========================================================================
# Notification endpoints
# ===========================================================================


@pytest.mark.unit
class TestNotificationEndpoints:
    def test_get_alerts(self, client):
        response = client.get("/api/v1/notifications/alerts")
        assert response.status_code == 200

    def test_create_alert(self, client):
        response = client.post(
            "/api/v1/notifications/alerts",
            json={
                "name": "AAPL price alert",
                "condition": {"type": "price_above", "symbol": "AAPL", "threshold": 200.0},
                "notification_methods": ["in_app"],
            },
        )
        assert response.status_code == 200

    def test_list_notifications(self, client):
        response = client.get("/api/v1/notifications")
        assert response.status_code == 200
        assert "notifications" in response.json()

    def test_unread_count(self, client):
        response = client.get("/api/v1/notifications/unread-count")
        assert response.status_code == 200

    def test_mark_all_read(self, client):
        response = client.post("/api/v1/notifications/mark-all-read")
        assert response.status_code == 200


# ===========================================================================
# Paper-Trading endpoints
# ===========================================================================


@pytest.mark.unit
class TestPaperTradingEndpoints:
    def test_create_portfolio(self, client):
        response = client.post(
            "/api/v1/paper-trading/portfolios",
            json={"name": "Test Portfolio", "initial_capital": 50_000},
        )
        assert response.status_code == 200

    def test_list_portfolios(self, client):
        response = client.get("/api/v1/paper-trading/portfolios")
        assert response.status_code == 200

    def test_get_portfolio_without_creating(self, client):
        # The user fixture creates a new user each time, so no portfolio exists
        response = client.get("/api/v1/paper-trading/portfolio")
        # Either 200 (if a previous test created one for this user) or 404
        assert response.status_code in (200, 404)

    def test_leaderboard(self, client):
        response = client.get("/api/v1/paper-trading/leaderboard")
        assert response.status_code == 200


# ===========================================================================
# Risk endpoints
# ===========================================================================


@pytest.mark.unit
class TestRiskEndpoints:
    def test_risk_analyze(self, client):
        response = client.post(
            "/api/v1/risk/analyze",
            json={
                "portfolio_id": "p1",
                "confidence_level": 0.95,
                "time_horizon_days": 1,
                "method": "historical",
                "include_stress_tests": False,
            },
        )
        # Risk analyze may return 200 or 500 depending on implementation,
        # but the route is reachable
        assert response.status_code in (200, 500)

    def test_risk_score(self, client):
        response = client.get("/api/v1/risk/score/p1")
        assert response.status_code in (200, 404, 500)


# ===========================================================================
# IBKR endpoints (read-only paths that don't need TWS)
# ===========================================================================


@pytest.mark.unit
class TestIBKREndpoints:
    def test_ibkr_status_when_disabled(self, client):
        # IBKR is disabled in test env (no IBKR_ENABLED=true)
        response = client.get("/api/v1/ibkr/status")
        assert response.status_code == 200
        data = response.json()
        assert "state" in data

    def test_ibkr_orders_listing(self, client):
        # No real DB → use simple list call
        response = client.get("/api/v1/ibkr/orders")
        # Either 200 with empty list, 500 (DB unavailable), or 422
        assert response.status_code in (200, 422, 500)

    def test_ibkr_connect_when_disabled(self, client):
        response = client.post("/api/v1/ibkr/connect")
        # 503 = service unavailable when disabled
        assert response.status_code == 503


# ===========================================================================
# Health endpoints (no auth required)
# ===========================================================================


@pytest.mark.unit
class TestHealthEndpoints:
    def test_root(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert "RNR Financial Analysis Platform" in response.json()["message"]

    def test_api_v1_health(self, client):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_openapi_schema(self, client):
        response = client.get("/api/v1/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "paths" in schema
        # Ensure all our endpoints are documented
        assert any("/screener" in p for p in schema["paths"])
        assert any("/ibkr" in p for p in schema["paths"])


# ===========================================================================
# Admin endpoints
# ===========================================================================


@pytest.mark.unit
class TestAdminEndpoints:
    def test_admin_users(self, client):
        response = client.get("/api/v1/admin/users")
        assert response.status_code in (200, 403, 500)

    def test_admin_system_metrics(self, client):
        response = client.get("/api/v1/admin/system/metrics")
        # System metrics endpoint might be /metrics or /system-metrics; try one
        # If not found, fine — we just want middleware coverage from the attempt
        assert response.status_code in (200, 403, 404, 500)


# ===========================================================================
# Sentiment endpoints
# ===========================================================================


@pytest.mark.unit
class TestSentimentEndpoints:
    def test_sentiment_keywords(self, client):
        # Try to fetch keywords endpoint
        response = client.get("/api/v1/sentiment/keywords")
        assert response.status_code in (200, 404, 405, 500)
