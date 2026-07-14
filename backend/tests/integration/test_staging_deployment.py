"""Smoke tests against the staging deployment.

These run from CI after a staging deploy. They hit the live staging API and
verify the deployment is healthy. They SKIP when no staging URL is configured
(e.g. running locally, or no staging environment deployed yet), so they never
fail a pipeline merely because the environment is absent.
"""
from __future__ import annotations

import os

import httpx
import pytest

STAGING_API_URL = os.getenv("STAGING_API_URL", "").rstrip("/")

# Skip the whole module if there is no staging target to test against.
pytestmark = pytest.mark.skipif(
    not STAGING_API_URL,
    reason="STAGING_API_URL not set; no staging deployment to verify",
)


@pytest.fixture(scope="module")
def client() -> httpx.Client:
    with httpx.Client(base_url=STAGING_API_URL, timeout=15.0) as c:
        yield c


def test_health_endpoint_ok(client: httpx.Client) -> None:
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200, resp.text


def test_openapi_published(client: httpx.Client) -> None:
    resp = client.get("/api/v1/openapi.json")
    assert resp.status_code == 200
    spec = resp.json()
    assert "paths" in spec and spec["paths"], "OpenAPI spec has no paths"


def test_monitoring_metrics_exposed(client: httpx.Client) -> None:
    resp = client.get("/api/v1/monitoring/metrics")
    # 200 in normal operation; 401/403 if metrics require auth. 5xx is a failure.
    assert resp.status_code < 500, f"metrics endpoint errored: {resp.status_code}"


def test_root_welcome(client: httpx.Client) -> None:
    resp = client.get("/")
    assert resp.status_code == 200
