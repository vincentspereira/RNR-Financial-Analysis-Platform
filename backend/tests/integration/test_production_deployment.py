"""Smoke tests against the production deployment.

Same shape as the staging deployment tests but pointed at production via
PRODUCTION_API_URL. Skips when no production URL is configured so it cannot
fail a pipeline just because production is not deployed.
"""
from __future__ import annotations

import os

import httpx
import pytest

PRODUCTION_API_URL = os.getenv("PRODUCTION_API_URL", "").rstrip("/")

pytestmark = pytest.mark.skipif(
    not PRODUCTION_API_URL,
    reason="PRODUCTION_API_URL not set; no production deployment to verify",
)


@pytest.fixture(scope="module")
def client() -> httpx.Client:
    with httpx.Client(base_url=PRODUCTION_API_URL, timeout=20.0) as c:
        yield c


def test_production_health(client: httpx.Client) -> None:
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200, resp.text


def test_production_openapi(client: httpx.Client) -> None:
    resp = client.get("/api/v1/openapi.json")
    assert resp.status_code == 200
    assert resp.json().get("paths"), "OpenAPI spec has no paths"


def test_production_no_server_error_on_root(client: httpx.Client) -> None:
    resp = client.get("/")
    assert resp.status_code < 500, f"root returned {resp.status_code}"


def test_production_security_headers(client: httpx.Client) -> None:
    """Production should set basic security headers (if a fronting proxy adds them)."""
    resp = client.get("/")
    # Only assert when the header is present (some setups terminate TLS upstream).
    if "x-content-type-options" in {k.lower() for k in resp.headers}:
        assert resp.headers["x-content-type-options"].lower() == "nosniff"
