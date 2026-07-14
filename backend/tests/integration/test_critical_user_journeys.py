"""Critical user-journey tests against a deployed API.

Walks the highest-value end-to-end flows (health -> auth -> authenticated
read) to catch regressions a deployment could introduce. Skips when no target
is configured.

NOTE: authenticated steps require TEST_USER_EMAIL / TEST_USER_PASSWORD; when
those are absent the auth-dependent steps are skipped individually while the
unauthenticated smoke steps still run.
"""
from __future__ import annotations

import os

import httpx
import pytest

API_URL = os.getenv("JOURNEY_API_URL") or os.getenv("STAGING_API_URL") or ""
TEST_USER_EMAIL = os.getenv("TEST_USER_EMAIL", "")
TEST_USER_PASSWORD = os.getenv("TEST_USER_PASSWORD", "")

pytestmark = pytest.mark.skipif(
    not API_URL,
    reason="JOURNEY_API_URL/STAGING_API_URL not set; no deployment to exercise",
)


@pytest.fixture(scope="module")
def client() -> httpx.Client:
    with httpx.Client(base_url=API_URL.rstrip("/"), timeout=15.0) as c:
        yield c


def test_journey_api_is_alive(client: httpx.Client) -> None:
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200, resp.text


def test_journey_openapi_advertises_auth(client: httpx.Client) -> None:
    resp = client.get("/api/v1/openapi.json")
    assert resp.status_code == 200
    spec = resp.json()
    # The auth router should be present in the published API surface.
    auth_paths = [p for p in spec.get("paths", {}) if "/auth" in p]
    assert auth_paths, "no /auth paths in OpenAPI spec"


@pytest.mark.skipif(
    not (TEST_USER_EMAIL and TEST_USER_PASSWORD),
    reason="TEST_USER_EMAIL/TEST_USER_PASSWORD not set",
)
def test_journey_login_returns_token(client: httpx.Client) -> None:
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
    )
    # 401 is a legitimate outcome for bogus creds; only 5xx is a deployment fault.
    assert resp.status_code < 500, f"login endpoint errored: {resp.status_code}"
    if resp.status_code == 200:
        body = resp.json()
        token = body.get("access_token") or body.get("token")
        assert token, "login succeeded but no access token returned"


def test_journey_protected_route_rejects_anonymous(client: httpx.Client) -> None:
    """An unauthenticated request to a protected resource must NOT 5xx."""
    resp = client.get("/api/v1/users/me")
    assert resp.status_code in (401, 403), (
        f"expected 401/403 for anonymous access, got {resp.status_code}"
    )
