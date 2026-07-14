"""
Basic tests for the main FastAPI application.

These tests use the FastAPI TestClient and exercise endpoints that do NOT
require an external database or Redis to respond meaningfully.
"""
from unittest.mock import patch, AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


def test_root_endpoint(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data
    assert "environment" in data
    assert "RNR Financial Analysis Platform" in data["message"]


def test_health_check_returns_payload(client: TestClient) -> None:
    """/health may report degraded/unhealthy in unit-test environment (no real
    DB). Assert only that the response is 200 and contains the expected
    envelope, NOT the specific health state."""
    # Mock the DB health checker so /health always reports a known state.
    fake_health = {"status": "healthy", "checks": {}, "timestamp": "2026-01-01T00:00:00Z"}
    with patch(
        "app.core.database_performance.db_health_checker.check_database_health",
        AsyncMock(return_value=fake_health),
    ):
        response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "environment" in data
    assert "services" in data
    assert data["services"]["api"] == "operational"


def test_api_v1_health(client: TestClient) -> None:
    """/api/v1/health is the API-version-scoped health endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert isinstance(data.get("features", []), list)
    assert len(data["features"]) > 0


def test_openapi_docs(client: TestClient) -> None:
    response = client.get("/api/v1/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "openapi" in data
    assert "info" in data
    assert data["info"]["title"] == "RNR Financial Analysis Platform"