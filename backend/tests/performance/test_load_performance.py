"""Lightweight load / latency checks for a deployed API.

Repeatedly hits the health + status endpoints and asserts that the p95 response
time stays under a configurable threshold. Skips when no target is configured
(local runs / no deployment).
"""
from __future__ import annotations

import os
import time

import httpx
import pytest

API_URL = os.getenv("LOAD_TEST_API_URL") or os.getenv("STAGING_API_URL") or ""
P95_THRESHOLD_MS = float(os.getenv("LOAD_TEST_P95_MS", "500"))
REQUESTS_PER_ENDPOINT = int(os.getenv("LOAD_TEST_REQUESTS", "40"))

pytestmark = pytest.mark.skipif(
    not API_URL,
    reason="LOAD_TEST_API_URL/STAGING_API_URL not set; nothing to load-test",
)


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    k = max(0, min(len(values) - 1, int(round((pct / 100.0) * (len(values) - 1)))))
    return values[k]


@pytest.mark.parametrize("path", ["/api/v1/health", "/api/v1/status"])
def test_endpoint_p95_under_threshold(path: str) -> None:
    timings_ms: list[float] = []
    with httpx.Client(base_url=API_URL.rstrip("/"), timeout=15.0) as client:
        # Warm up (cold start / cache miss) before measuring.
        client.get(path)
        for _ in range(REQUESTS_PER_ENDPOINT):
            start = time.perf_counter()
            resp = client.get(path)
            timings_ms.append((time.perf_counter() - start) * 1000.0)
            assert resp.status_code < 500, f"{path} errored: {resp.status_code}"

    p95 = _percentile(timings_ms, 95)
    assert p95 <= P95_THRESHOLD_MS, (
        f"{path} p95={p95:.1f}ms exceeds threshold {P95_THRESHOLD_MS}ms"
    )
