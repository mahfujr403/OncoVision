"""Unit tests for `AdminSystemService` (Phase 7.5, ADR-036).

Uses lightweight fakes/mocks for `SystemService`/`AIRuntimeManager` and
monkeypatches `check_database_connection` -- no real database, TensorFlow
runtime, or model files required, mirroring how
`tests/api/test_system_router.py` already tests the self-service system
endpoints.
"""

import asyncio

import pytest

from app.schemas.common import ApplicationInfo
from app.services.admin_system_service import AdminSystemService


class _FakeHealthService:
    async def runtime_status(self) -> dict:
        return {"status": "healthy", "loaded_models": 2}


class _FakeRuntimeManager:
    def __init__(self) -> None:
        self.health_service = _FakeHealthService()

    async def get_all_model_status(self) -> list[dict]:
        return [{"model_name": "MobileNetV2", "status": "loaded"}]


class _FakeSystemService:
    def get_application_info(self) -> ApplicationInfo:
        return ApplicationInfo(
            name="OncoVision AI",
            version="0.1.0",
            environment="test",
            health_endpoint="/api/v1/health",
        )


class TestGetSystemStatus:
    def test_aggregates_application_database_runtime_and_model_status(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def fake_check_connection() -> None:
            return None

        monkeypatch.setattr(
            "app.services.admin_system_service.check_database_connection",
            fake_check_connection,
        )

        service = AdminSystemService(
            runtime_manager=_FakeRuntimeManager(), system_service=_FakeSystemService()
        )

        status_snapshot = asyncio.run(service.get_system_status())

        assert status_snapshot["application"]["name"] == "OncoVision AI"
        assert status_snapshot["database"]["connected"] is True
        assert status_snapshot["runtime"]["status"] == "healthy"
        assert status_snapshot["models"]["models"][0]["model_name"] == "MobileNetV2"
        assert "generated_at" in status_snapshot

    def test_reports_unhealthy_database_without_leaking_the_underlying_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def failing_check_connection() -> None:
            raise RuntimeError("connection refused: password=super-secret")

        monkeypatch.setattr(
            "app.services.admin_system_service.check_database_connection",
            failing_check_connection,
        )

        service = AdminSystemService(
            runtime_manager=_FakeRuntimeManager(), system_service=_FakeSystemService()
        )

        status_snapshot = asyncio.run(service.get_system_status())

        assert status_snapshot["database"]["connected"] is False
        assert "super-secret" not in str(status_snapshot)
