"""Router-level tests for `app.api.v1.admin.system` (Phase 7.5/7.6, ADR-036).

Exercises the Admin System endpoint through the full FastAPI
routing/validation/exception-handling stack via
`fastapi.testclient.TestClient`, using `app.dependency_overrides` to
substitute the authenticated user (`get_current_active_user`) and the
Admin System Service (`get_admin_system_service`) with a mocked runtime
-- no real database, TensorFlow runtime, or model files required.
"""

import pytest
from fastapi.testclient import TestClient

from app.dependencies.auth import get_current_active_user
from app.dependencies.services import get_admin_system_service
from app.main import app
from app.models.enums import UserRole
from tests.admin.doubles import make_user
from tests.admin.test_admin_system_service import _FakeRuntimeManager, _FakeSystemService
from app.services.admin_system_service import AdminSystemService

SYSTEM_PATH = "/api/v1/admin/system"


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
        "app.services.admin_system_service.check_database_connection", fake_check_connection
    )

    service = AdminSystemService(
        runtime_manager=_FakeRuntimeManager(), system_service=_FakeSystemService()
    )

    app.dependency_overrides[get_current_active_user] = lambda: current_user
    app.dependency_overrides[get_admin_system_service] = lambda: service

    return TestClient(app)


def _clear_overrides() -> None:
    app.dependency_overrides.pop(get_current_active_user, None)
    app.dependency_overrides.pop(get_admin_system_service, None)


class TestAdminSystemAuthorization:
    def test_unauthenticated_request_returns_401(self) -> None:
        test_client = TestClient(app)

        response = test_client.get(SYSTEM_PATH)

        assert response.status_code == 401

    def test_non_admin_returns_403(self, standard_user, monkeypatch: pytest.MonkeyPatch) -> None:
        client = _client_as(standard_user, monkeypatch)

        response = client.get(SYSTEM_PATH)
        _clear_overrides()

        assert response.status_code == 403


class TestGetAdminSystemStatus:
    def test_administrator_receives_status_snapshot(
        self, admin_user, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        client = _client_as(admin_user, monkeypatch)

        response = client.get(SYSTEM_PATH)
        _clear_overrides()

        assert response.status_code == 200
        payload = response.json()["data"]
        assert payload["database"]["connected"] is True
        assert payload["runtime"]["status"] == "healthy"
        assert payload["models"]["models"][0]["model_name"] == "MobileNetV2"
        assert "generated_at" in payload

    def test_response_never_includes_secret_looking_keys(
        self, admin_user, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        client = _client_as(admin_user, monkeypatch)

        response = client.get(SYSTEM_PATH)
        _clear_overrides()

        body_text = response.text.lower()
        for forbidden in ("password", "secret", "database_url", "jwt_secret", "api_key"):
            assert forbidden not in body_text
