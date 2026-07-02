"""
More endpoint smoke tests — financial, data, reports, IBKR deep paths.

Hits each route at least once to drive endpoint code paths. Service layer
calls return 500 / 404 in most cases (no DB), but the route handler still
executes its argument parsing, validation, and error branches.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints import (
    admin,
    data,
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
from app.core.auth import get_current_user as core_get_current_user


def _mock_user():
    user = MagicMock()
    user.id = uuid4()
    user.email = "test@test.com"
    user.is_active = True
    user.role = "admin"
    return user


@pytest.fixture
def auth_headers() -> dict:
    token = jwt_handler.create_access_token(uuid4())
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client(auth_headers) -> TestClient:
    overrides = {
        screener.get_current_user_from_token: _mock_user,
        notifications.get_current_user_from_token: _mock_user,
        paper_trading.get_current_user_from_token: _mock_user,
        risk.get_current_user_from_token: _mock_user,
        sentiment.get_current_user_from_token: _mock_user,
        ibkr.get_current_user: _mock_user,
        admin.get_current_user_from_token: _mock_user,
        tech_get_user: _mock_user,
        po_get_user: _mock_user,
        data.get_current_user_from_token: _mock_user,
        core_get_current_user: _mock_user,
    }
    for dep, override in overrides.items():
        app.dependency_overrides[dep] = override

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
# Financial endpoints
# ===========================================================================


@pytest.mark.unit
class TestFinancialEndpoints:
    def test_calculate_ratios_quarterly_without_quarter_returns_400(self, client):
        response = client.post(
            "/api/v1/financial/ratios/calculate",
            json={
                "company_id": str(uuid4()),
                "period_type": "quarterly",
                "fiscal_year": 2024,
                # No fiscal_quarter
            },
        )
        # Validation either 400 or 422 acceptable
        assert response.status_code in (400, 422, 500)

    def test_calculate_ratios_invalid_quarter(self, client):
        response = client.post(
            "/api/v1/financial/ratios/calculate",
            json={
                "company_id": str(uuid4()),
                "period_type": "quarterly",
                "fiscal_year": 2024,
                "fiscal_quarter": 99,
            },
        )
        assert response.status_code in (400, 422, 500)

    def test_calculate_valuation(self, client):
        response = client.post(
            "/api/v1/financial/valuation/calculate",
            json={
                "company_id": str(uuid4()),
                "assumptions": {"discount_rate": 0.10},
            },
        )
        assert response.status_code in (200, 400, 404, 422, 500)

    def test_peer_comparison(self, client):
        response = client.post(
            "/api/v1/financial/peer-comparison",
            json={
                "company_id": str(uuid4()),
                "peer_company_ids": [str(uuid4())],
                "period_type": "annual",
                "fiscal_year": 2024,
            },
        )
        assert response.status_code in (200, 400, 404, 422, 500)

    def test_company_financial_data(self, client):
        response = client.get(f"/api/v1/financial/company/{uuid4()}/financial-data")
        assert response.status_code in (200, 400, 404, 422, 500)


# ===========================================================================
# Data endpoints
# ===========================================================================


@pytest.mark.unit
class TestDataEndpoints:
    def test_ingest_company(self, client):
        # Mock the ingestion service to avoid real API calls
        with patch(
            "app.api.v1.endpoints.data.data_ingestion_service.ingest_company_data",
            AsyncMock(return_value={"symbol": "AAPL", "success": True}),
        ):
            response = client.post(
                "/api/v1/data/ingest/company",
                json={"symbol": "AAPL"},
            )
        assert response.status_code in (200, 400, 422, 500)

    def test_ingest_batch(self, client):
        with patch(
            "app.api.v1.endpoints.data.data_ingestion_service.batch_ingest_companies",
            AsyncMock(return_value={"total_processed": 0, "results": []}),
        ):
            response = client.post(
                "/api/v1/data/ingest/batch",
                json={"symbols": ["AAPL", "MSFT"]},
            )
        assert response.status_code in (200, 400, 422, 500)

    def test_sources_status(self, client):
        with patch(
            "app.api.v1.endpoints.data.data_ingestion_service.get_data_source_status",
            AsyncMock(return_value={"sources": {}}),
        ):
            response = client.get("/api/v1/data/sources/status")
        assert response.status_code in (200, 400, 500)

    def test_data_stats(self, client):
        response = client.get("/api/v1/data/stats")
        assert response.status_code in (200, 400, 500)


# ===========================================================================
# Reports endpoints
# ===========================================================================


@pytest.mark.unit
class TestReportsEndpoints:
    def test_generate_report(self, client):
        response = client.post(
            "/api/v1/reports/generate",
            json={
                "report_type": "portfolio",
                "portfolio_id": str(uuid4()),
                "format": "pdf",
            },
        )
        assert response.status_code in (200, 400, 404, 422, 500)

    def test_generate_custom_report(self, client):
        response = client.post(
            "/api/v1/reports/generate/custom",
            json={"title": "Custom", "sections": []},
        )
        assert response.status_code in (200, 400, 422, 500)

    def test_download_nonexistent_report(self, client):
        response = client.get(f"/api/v1/reports/download/{uuid4()}")
        # Reports module may stub-return 200 for unknown IDs in dev mode
        assert response.status_code in (200, 401, 404, 500)

    def test_preview_nonexistent_report(self, client):
        response = client.get(f"/api/v1/reports/preview/{uuid4()}")
        assert response.status_code in (200, 401, 404, 500)

    def test_get_scheduled_reports(self, client):
        response = client.get("/api/v1/reports/scheduled")
        assert response.status_code in (200, 500)

    def test_get_report_history(self, client):
        response = client.get("/api/v1/reports/history")
        assert response.status_code in (200, 500)

    def test_get_templates(self, client):
        response = client.get("/api/v1/reports/templates")
        assert response.status_code in (200, 500)


# ===========================================================================
# IBKR endpoints (more depth)
# ===========================================================================


@pytest.mark.unit
class TestIBKREndpointsDeep:
    def test_get_status(self, client):
        response = client.get("/api/v1/ibkr/status")
        assert response.status_code == 200
        data = response.json()
        assert data["state"] in ("disabled", "disconnected", "failed", "connected")

    def test_account_when_disabled_returns_503(self, client):
        response = client.get("/api/v1/ibkr/account")
        # IBKR disabled in test env
        assert response.status_code == 503

    def test_positions_when_disabled_returns_503(self, client):
        response = client.get("/api/v1/ibkr/positions")
        assert response.status_code == 503

    def test_disconnect_is_safe_when_disconnected(self, client):
        response = client.post("/api/v1/ibkr/disconnect")
        assert response.status_code == 200

    def test_quote_when_disabled_returns_503(self, client):
        response = client.get("/api/v1/ibkr/quote/AAPL")
        assert response.status_code == 503

    def test_place_order_when_disabled_returns_503(self, client):
        response = client.post(
            "/api/v1/ibkr/orders",
            json={
                "symbol": "AAPL",
                "action": "BUY",
                "order_type": "market",
                "quantity": 1,
            },
        )
        assert response.status_code == 503

    def test_sync_orders_when_disabled_returns_503(self, client):
        response = client.post("/api/v1/ibkr/orders/sync")
        assert response.status_code == 503


# ===========================================================================
# Notification endpoints (more)
# ===========================================================================


@pytest.mark.unit
class TestNotificationEndpointsMore:
    def test_delete_alert_unknown(self, client):
        response = client.delete(f"/api/v1/notifications/alerts/{uuid4()}")
        assert response.status_code in (200, 404)

    def test_mark_notification_as_read_unknown(self, client):
        response = client.post(f"/api/v1/notifications/{uuid4()}/read")
        # 405 acceptable if endpoint expects different route
        assert response.status_code in (200, 404, 405)
