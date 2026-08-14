"""Router-level tests for `app.api.v1.monitoring` (Phase 8.1, ADR-036).

Exercises the Monitoring endpoint through the full FastAPI
routing/validation/exception-handling stack via
`fastapi.testclient.TestClient`, using `app.dependency_overrides` to
substitute the authenticated user (`get_current_active_user`) and the
Monitoring Service (`get_monitoring_service`) with a mocked runtime --
no real database, TensorFlow runtime, or model files required, mirroring
`tests/api/test_admin_system_router.py`.
"""

import pytest
from fastapi.testclient import TestClient

from app.core.request_metrics import RequestMetricsCollector
from app.dependencies.auth import get_current_active_user
from app.dependencies.services import get_monitoring_service
from app.main import app
from app.models.enums import UserRole
from app.services.monitoring_service import MonitoringService
from tests.admin.doubles import make_user
from tests.monitoring.test_monitoring_service import (
    _FakeRuntimeManager,
    _FakeSystemService,
    _model_status,
    _operational_runtime_status,
)

MONITORING_PATH = "/api/v1/monitoring"


@pytest.fixture
def admin_user():
    return make_user(role=UserRole.ADMIN, email="admin@example.com")


@pytest.fixture
def standard_user():
    return make_user(role=UserRole.USER, email="standard@example.com")


def _client_as(current_user, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    async def fake_check_connection() -> None:
        return None

    monkeypatch.setattr(
        "app.services.monitoring_service.check_database_connection", fake_check_connection
    )

    service = MonitoringService(
        runtime_manager=_FakeRuntimeManager(
            _operational_runtime_status(), [_model_status("mobilenet_v2")]
        ),
        system_service=_FakeSystemService(),
    )

    app.dependency_overrides[get_current_active_user] = lambda: current_user
    app.dependency_overrides[get_monitoring_service] = lambda: service

    return TestClient(app)

def _clear_overrides() -> None:
    app.dependency_overrides.pop(get_current_active_user, None)
    app.dependency_overrides.pop(get_monitoring_service, None)


class TestMonitoringAuthorization:
    def test_unauthenticated_request_returns_401(self) -> None:
        test_client = TestClient(app)

        response = test_client.get(MONITORING_PATH)

        assert response.status_code == 401

    def test_non_admin_returns_403(self, standard_user, monkeypatch: pytest.MonkeyPatch) -> None:
        client = _client_as(standard_user, monkeypatch)

        response = client.get(MONITORING_PATH)
        _clear_overrides()

        assert response.status_code == 403


class TestGetMonitoringStatus:
    def test_administrator_receives_monitoring_snapshot(
        self, admin_user, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        client = _client_as(admin_user, monkeypatch)

        response = client.get(MONITORING_PATH)
        _clear_overrides()

        assert response.status_code == 200
        payload = response.json()["data"]
        assert payload["status"] == "healthy"
        assert payload["application"]["status"] == "healthy"
        assert payload["database"]["connected"] is True
        assert payload["runtime"]["is_operational"] is True
        assert payload["runtime"]["models"][0]["model_id"] == "mobilenet_v2"
        assert "generated_at" in payload

    def test_response_matches_the_documented_schema(
        self, admin_user, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        client = _client_as(admin_user, monkeypatch)

        response = client.get(MONITORING_PATH)
        _clear_overrides()

        payload = response.json()["data"]
        assert set(payload.keys()) == {
            "status",
            "application",
            "database",
            "runtime",
            "request_metrics",
            "prediction_metrics",
            "generated_at",
        }
        assert set(payload["runtime"].keys()) == {
            "status",
            "is_operational",
            "total_model_count",
            "loaded_model_count",
            "failed_model_count",
            "pending_model_count",
            "disabled_model_count",
            "models",
        }
        assert set(payload["request_metrics"].keys()) == {
            "total_requests",
            "status_2xx",
            "status_3xx",
            "status_4xx",
            "status_5xx",
            "average_duration_ms",
        }
        assert set(payload["prediction_metrics"].keys()) == {
            "total_requests",
            "successful_requests",
            "failed_requests",
        }

    def test_response_never_includes_secret_looking_keys(
        self, admin_user, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        client = _client_as(admin_user, monkeypatch)

        response = client.get(MONITORING_PATH)
        _clear_overrides()

        body_text = response.text.lower()
        for forbidden in ("password", "secret", "database_url", "jwt_secret", "api_key"):
            assert forbidden not in body_text

    def test_database_failure_is_reported_as_unhealthy_with_200_status(
        self, admin_user, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def failing_check_connection() -> None:
            raise RuntimeError("connection refused")

        monkeypatch.setattr(
            "app.services.monitoring_service.check_database_connection",
            failing_check_connection,
        )
        service = MonitoringService(
            runtime_manager=_FakeRuntimeManager(
                _operational_runtime_status(), [_model_status("mobilenet_v2")]
            ),
            system_service=_FakeSystemService(),
        )
        app.dependency_overrides[get_current_active_user] = lambda: admin_user
        app.dependency_overrides[get_monitoring_service] = lambda: service

        response = TestClient(app).get(MONITORING_PATH)
        _clear_overrides()

        assert response.status_code == 200
        payload = response.json()["data"]
        assert payload["status"] == "unhealthy"
        assert payload["database"]["connected"] is False


class TestMonitoringRequestAndPredictionMetrics:
    """Phase 8.2 (ADR-036): `request_metrics`/`prediction_metrics` on `GET /api/v1/monitoring`."""

    def test_response_includes_populated_request_and_prediction_metrics(
        self, admin_user, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def fake_check_connection() -> None:
            return None

        monkeypatch.setattr(
            "app.services.monitoring_service.check_database_connection", fake_check_connection
        )
        collector = RequestMetricsCollector()
        collector.record_request(
            method="POST", path="/api/v1/predictions", status_code=200, duration_ms=42.0
        )
        collector.record_request(
            method="POST", path="/api/v1/predictions", status_code=503, duration_ms=3.0
        )
        service = MonitoringService(
            runtime_manager=_FakeRuntimeManager(
                _operational_runtime_status(), [_model_status("mobilenet_v2")]
            ),
            system_service=_FakeSystemService(),
            request_metrics_collector=collector,
        )
        app.dependency_overrides[get_current_active_user] = lambda: admin_user
        app.dependency_overrides[get_monitoring_service] = lambda: service

        response = TestClient(app).get(MONITORING_PATH)
        _clear_overrides()

        assert response.status_code == 200
        payload = response.json()["data"]
        assert payload["request_metrics"]["total_requests"] == 2
        assert payload["request_metrics"]["status_2xx"] == 1
        assert payload["request_metrics"]["status_5xx"] == 1
        assert payload["prediction_metrics"]["total_requests"] == 2
        assert payload["prediction_metrics"]["successful_requests"] == 1
        assert payload["prediction_metrics"]["failed_requests"] == 1
