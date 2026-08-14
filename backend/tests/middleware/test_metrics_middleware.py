"""Tests for `RequestMetricsMiddleware` (Phase 8.2, ADR-036).

Exercises the middleware through the full FastAPI stack via
`fastapi.testclient.TestClient`, using the already-registered
`GET /api/v1/health` endpoint (Phase 1) as a stable, unauthenticated
target -- no database, TensorFlow runtime, or model files required.

The critical property under test is Phase 8.2's Reliability
requirement: a monitoring/metrics failure must never break a request.
"""

import pytest
from fastapi.testclient import TestClient

from app.core.request_metrics import default_request_metrics_collector
from app.main import app

HEALTH_PATH = "/api/v1/health"


class TestRequestMetricsMiddlewareRecording:
    def test_a_successful_request_is_recorded(self) -> None:
        default_request_metrics_collector.reset()
        client = TestClient(app)

        response = client.get(HEALTH_PATH)

        assert response.status_code == 200
        snapshot = default_request_metrics_collector.snapshot()
        assert snapshot.total_requests == 1
        assert snapshot.status_2xx == 1


class TestRequestMetricsMiddlewareFailureIsolation:
    def test_a_broken_collector_never_breaks_the_response(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A `record_request()` failure must be swallowed, never surfaced as a 500."""
        default_request_metrics_collector.reset()

        def _raise(*args, **kwargs):
            raise RuntimeError("metrics store unavailable")

        monkeypatch.setattr(default_request_metrics_collector, "record_request", _raise)
        client = TestClient(app)

        response = client.get(HEALTH_PATH)

        assert response.status_code == 200
        assert response.json()["data"]["status"] == "healthy"
