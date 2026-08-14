"""Unit tests for `MonitoringService` (Phase 8.1, ADR-036).

Uses lightweight fakes for `SystemService`/`AIRuntimeManager` and
monkeypatches `check_database_connection` -- no real database, TensorFlow
runtime, or model files required, mirroring
`tests/admin/test_admin_system_service.py`.
"""

import asyncio

import pytest

from app.core.request_metrics import RequestMetricsCollector, RequestMetricsSnapshot
from app.monitoring.enums import ComponentStatus
from app.schemas.common import ApplicationInfo
from app.services.monitoring_service import MonitoringService


class _FakeHealthService:
    def __init__(self, runtime_status: dict) -> None:
        self._runtime_status = runtime_status

    async def runtime_status(self) -> dict:
        return self._runtime_status


class _FakeRuntimeManager:
    def __init__(self, runtime_status: dict, model_statuses: list[dict]) -> None:
        self.health_service = _FakeHealthService(runtime_status)
        self._model_statuses = model_statuses

    async def get_all_model_status(self) -> list[dict]:
        return self._model_statuses


class _FakeSystemService:
    def get_application_info(self) -> ApplicationInfo:
        return ApplicationInfo(
            name="OncoVision AI",
            version="0.1.0",
            environment="test",
            health_endpoint="/api/v1/health",
        )


def _operational_runtime_status(*, failed_model_count: int = 0) -> dict:
    return {
        "is_operational": True,
        "total_model_count": 3,
        "loaded_model_count": 3 - failed_model_count,
        "failed_model_count": failed_model_count,
        "pending_model_count": 0,
        "disabled_model_count": 0,
    }


def _non_operational_runtime_status() -> dict:
    return {
        "is_operational": False,
        "total_model_count": 3,
        "loaded_model_count": 0,
        "failed_model_count": 3,
        "pending_model_count": 0,
        "disabled_model_count": 0,
    }


def _model_status(
    model_id: str = "mobilenet_v2", state: str = "ready", error_message: str | None = None
) -> dict:
    return {
        "model_id": model_id,
        "display_name": model_id,
        "priority": 1,
        "loading_strategy": "startup",
        "state": state,
        "error_message": error_message,
        "load_duration_ms": 120.5,
        "memory_estimate_mb": 45.0,
        "loaded_at": "2026-01-01T00:00:00Z",
        "attempts": 1,
    }


def _patch_database_connection(monkeypatch: pytest.MonkeyPatch, *, healthy: bool) -> None:
    if healthy:

        async def fake_check_connection() -> None:
            return None

    else:

        async def fake_check_connection() -> None:
            raise RuntimeError("connection refused: password=super-secret")

    monkeypatch.setattr(
        "app.services.monitoring_service.check_database_connection", fake_check_connection
    )


class TestApplicationHealth:
    def test_application_is_always_reported_healthy(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_database_connection(monkeypatch, healthy=True)
        service = MonitoringService(
            runtime_manager=_FakeRuntimeManager(_operational_runtime_status(), [_model_status()]),
            system_service=_FakeSystemService(),
        )

        result = asyncio.run(service.get_monitoring_status())

        assert result.application.status == ComponentStatus.HEALTHY
        assert result.application.name == "OncoVision AI"
        assert result.application.version == "0.1.0"
        assert result.application.environment == "test"


class TestDatabaseHealth:
    def test_healthy_database_is_reported_connected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_database_connection(monkeypatch, healthy=True)
        service = MonitoringService(
            runtime_manager=_FakeRuntimeManager(_operational_runtime_status(), [_model_status()]),
            system_service=_FakeSystemService(),
        )

        result = asyncio.run(service.get_monitoring_status())

        assert result.database.status == ComponentStatus.HEALTHY
        assert result.database.connected is True

    def test_unreachable_database_is_reported_unhealthy_without_leaking_the_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_database_connection(monkeypatch, healthy=False)
        service = MonitoringService(
            runtime_manager=_FakeRuntimeManager(_operational_runtime_status(), [_model_status()]),
            system_service=_FakeSystemService(),
        )

        result = asyncio.run(service.get_monitoring_status())

        assert result.database.status == ComponentStatus.UNHEALTHY
        assert result.database.connected is False
        assert "super-secret" not in result.model_dump_json()


class TestRuntimeHealthAndModelAvailability:
    def test_operational_runtime_with_no_failures_is_healthy(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_database_connection(monkeypatch, healthy=True)
        service = MonitoringService(
            runtime_manager=_FakeRuntimeManager(
                _operational_runtime_status(),
                [_model_status("mobilenet_v2"), _model_status("densenet121")],
            ),
            system_service=_FakeSystemService(),
        )

        result = asyncio.run(service.get_monitoring_status())

        assert result.runtime.status == ComponentStatus.HEALTHY
        assert result.runtime.is_operational is True
        assert result.runtime.loaded_model_count == 3
        assert len(result.runtime.models) == 2
        assert all(model.is_available for model in result.runtime.models)

    def test_operational_runtime_with_a_failed_model_is_degraded(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_database_connection(monkeypatch, healthy=True)
        service = MonitoringService(
            runtime_manager=_FakeRuntimeManager(
                _operational_runtime_status(failed_model_count=1),
                [
                    _model_status("mobilenet_v2", state="ready"),
                    _model_status("fusion_model", state="failed", error_message="out of memory"),
                ],
            ),
            system_service=_FakeSystemService(),
        )

        result = asyncio.run(service.get_monitoring_status())

        assert result.runtime.status == ComponentStatus.DEGRADED
        assert result.runtime.failed_model_count == 1
        failed_entry = next(m for m in result.runtime.models if m.model_id == "fusion_model")
        assert failed_entry.is_available is False
        assert failed_entry.error_message == "out of memory"

    def test_non_operational_runtime_with_no_loaded_models_is_unhealthy(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_database_connection(monkeypatch, healthy=True)
        service = MonitoringService(
            runtime_manager=_FakeRuntimeManager(
                _non_operational_runtime_status(),
                [_model_status("mobilenet_v2", state="failed", error_message="download failed")],
            ),
            system_service=_FakeSystemService(),
        )

        result = asyncio.run(service.get_monitoring_status())

        assert result.runtime.status == ComponentStatus.UNHEALTHY
        assert result.runtime.is_operational is False


class TestOverallStatus:
    def test_overall_status_is_healthy_when_database_and_runtime_are_healthy(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_database_connection(monkeypatch, healthy=True)
        service = MonitoringService(
            runtime_manager=_FakeRuntimeManager(_operational_runtime_status(), [_model_status()]),
            system_service=_FakeSystemService(),
        )

        result = asyncio.run(service.get_monitoring_status())

        assert result.status == ComponentStatus.HEALTHY

    def test_overall_status_is_degraded_when_runtime_has_a_failed_model(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_database_connection(monkeypatch, healthy=True)
        service = MonitoringService(
            runtime_manager=_FakeRuntimeManager(
                _operational_runtime_status(failed_model_count=1),
                [_model_status("mobilenet_v2"), _model_status("fusion_model", state="failed")],
            ),
            system_service=_FakeSystemService(),
        )

        result = asyncio.run(service.get_monitoring_status())

        assert result.status == ComponentStatus.DEGRADED

    def test_overall_status_is_unhealthy_when_database_is_unreachable_even_if_runtime_is_healthy(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_database_connection(monkeypatch, healthy=False)
        service = MonitoringService(
            runtime_manager=_FakeRuntimeManager(_operational_runtime_status(), [_model_status()]),
            system_service=_FakeSystemService(),
        )

        result = asyncio.run(service.get_monitoring_status())

        assert result.status == ComponentStatus.UNHEALTHY

    def test_overall_status_is_unhealthy_when_runtime_has_no_loaded_models(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_database_connection(monkeypatch, healthy=True)
        service = MonitoringService(
            runtime_manager=_FakeRuntimeManager(
                _non_operational_runtime_status(), [_model_status(state="failed")]
            ),
            system_service=_FakeSystemService(),
        )

        result = asyncio.run(service.get_monitoring_status())

        assert result.status == ComponentStatus.UNHEALTHY

    def test_result_includes_a_generated_at_timestamp(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_database_connection(monkeypatch, healthy=True)
        service = MonitoringService(
            runtime_manager=_FakeRuntimeManager(_operational_runtime_status(), [_model_status()]),
            system_service=_FakeSystemService(),
        )

        result = asyncio.run(service.get_monitoring_status())

        assert result.generated_at


class _FailingRequestMetricsCollector(RequestMetricsCollector):
    """A collector whose `snapshot()` always raises, for failure-isolation tests."""

    def snapshot(self) -> RequestMetricsSnapshot:
        raise RuntimeError("metrics store unavailable")


class TestRequestMetrics:
    """Phase 8.2 (ADR-036): `MonitoringService` request/prediction metrics projection."""

    def test_defaults_to_the_process_wide_collector_when_none_is_supplied(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Phase 8.1 callers that construct `MonitoringService` without a collector still work."""
        _patch_database_connection(monkeypatch, healthy=True)
        service = MonitoringService(
            runtime_manager=_FakeRuntimeManager(_operational_runtime_status(), [_model_status()]),
            system_service=_FakeSystemService(),
        )

        result = asyncio.run(service.get_monitoring_status())

        assert result.request_metrics.total_requests >= 0
        assert result.prediction_metrics.total_requests >= 0

    def test_collector_snapshot_is_copied_onto_the_result_without_recalculation(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_database_connection(monkeypatch, healthy=True)
        collector = RequestMetricsCollector()
        collector.record_request(method="GET", path="/api/v1/health", status_code=200, duration_ms=4.0)
        collector.record_request(
            method="POST", path="/api/v1/predictions", status_code=200, duration_ms=100.0
        )
        collector.record_request(
            method="POST", path="/api/v1/predictions", status_code=503, duration_ms=2.0
        )
        service = MonitoringService(
            runtime_manager=_FakeRuntimeManager(_operational_runtime_status(), [_model_status()]),
            system_service=_FakeSystemService(),
            request_metrics_collector=collector,
        )

        result = asyncio.run(service.get_monitoring_status())

        assert result.request_metrics.total_requests == 3
        assert result.request_metrics.status_2xx == 2
        assert result.request_metrics.status_5xx == 1
        assert result.prediction_metrics.total_requests == 2
        assert result.prediction_metrics.successful_requests == 1
        assert result.prediction_metrics.failed_requests == 1

    def test_a_broken_collector_never_raises_and_yields_zeroed_metrics(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Failure isolation (Phase 8.2): a metrics-store failure must never break `/monitoring`."""
        _patch_database_connection(monkeypatch, healthy=True)
        service = MonitoringService(
            runtime_manager=_FakeRuntimeManager(_operational_runtime_status(), [_model_status()]),
            system_service=_FakeSystemService(),
            request_metrics_collector=_FailingRequestMetricsCollector(),
        )

        result = asyncio.run(service.get_monitoring_status())

        assert result.request_metrics.total_requests == 0
        assert result.prediction_metrics.total_requests == 0
        # The rest of the snapshot must remain unaffected by the metrics failure.
        assert result.status == ComponentStatus.HEALTHY
        assert result.database.connected is True
