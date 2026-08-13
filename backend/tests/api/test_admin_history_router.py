"""Router-level tests for `app.api.v1.admin.history` (Phase 7.4/7.6, ADR-036).

Exercises the Admin History endpoints through the full FastAPI
routing/validation/exception-handling stack via
`fastapi.testclient.TestClient`, using `app.dependency_overrides` to
substitute the authenticated user (`get_current_active_user`) and the
Admin History Service (`get_admin_history_service`) -- no real database.
"""

import pytest
from fastapi.testclient import TestClient

from app.dependencies.auth import get_current_active_user
from app.dependencies.services import get_admin_history_service
from app.history.enums import PredictionHistoryStatus
from app.history.metadata import PredictionHistoryMetadata
from app.history.prediction_history import PredictionHistory
from app.history.summary import PredictionHistorySummary
from app.main import app
from app.models.enums import UserRole
from app.services.admin_history_service import AdminHistoryService
from app.services.prediction_history_service import PredictionHistoryService
from tests.admin.doubles import AdminAwarePredictionHistoryRepository, make_user
from tests.history.conftest_helpers import make_context

HISTORY_PATH = "/api/v1/admin/history"


def _make_history(
    user_id: str,
    history_id: str,
    status: PredictionHistoryStatus = PredictionHistoryStatus.SUCCESS,
) -> PredictionHistory:
    context = make_context(user_id=user_id)
    metadata = PredictionHistoryMetadata(
        request_id=context.request_id,
        requested_at=context.requested_at,
        user_id=user_id,
        user_email=context.user_email,
        image_filename=context.image_filename,
        image_content_type=context.image_content_type,
        image_size_bytes=context.image_size_bytes,
        image_width=context.image_width,
        image_height=context.image_height,
    )
    summary = PredictionHistorySummary(
        predicted_class="lung_aca",
        confidence=91.2,
        agreement_ratio=1.0,
        successful_models=["mobilenetv2"],
        failed_models=[],
        participating_models=1,
        individual_predictions=[],
    )
    return PredictionHistory(
        history_id=history_id,
        request_id=context.request_id,
        user_id=user_id,
        status=status,
        created_at="2026-07-27T10:00:00+00:00",
        metadata=metadata,
        summary=summary,
    )


@pytest.fixture
def admin_user():
    return make_user(role=UserRole.ADMIN, email="admin@example.com")


@pytest.fixture
def standard_user():
    return make_user(role=UserRole.USER, email="standard@example.com")


def _client_as(current_user, records: list[PredictionHistory] | None = None) -> TestClient:
    repository = AdminAwarePredictionHistoryRepository(records or [])
    history_service = PredictionHistoryService(repository)
    admin_history_service = AdminHistoryService(history_service)

    app.dependency_overrides[get_current_active_user] = lambda: current_user
    app.dependency_overrides[get_admin_history_service] = lambda: admin_history_service

    return TestClient(app)


def _clear_overrides() -> None:
    app.dependency_overrides.pop(get_current_active_user, None)
    app.dependency_overrides.pop(get_admin_history_service, None)


class TestAdminHistoryAuthorization:
    def test_unauthenticated_request_returns_401(self) -> None:
        test_client = TestClient(app)

        response = test_client.get(HISTORY_PATH)

        assert response.status_code == 401

    def test_non_admin_returns_403(self, standard_user) -> None:
        client = _client_as(standard_user)

        response = client.get(HISTORY_PATH)
        _clear_overrides()

        assert response.status_code == 403


class TestListHistory:
    def test_lists_records_across_every_user(self, admin_user) -> None:
        records = [
            _make_history("user-a", "hist-1"),
            _make_history("user-b", "hist-2"),
        ]
        client = _client_as(admin_user, records)

        response = client.get(HISTORY_PATH)
        _clear_overrides()

        assert response.status_code == 200
        payload = response.json()["data"]
        assert payload["count"] == 2
        assert {item["user_id"] for item in payload["items"]} == {"user-a", "user-b"}

    def test_filters_by_status(self, admin_user) -> None:
        records = [
            _make_history("user-a", "hist-1", status=PredictionHistoryStatus.SUCCESS),
            _make_history("user-b", "hist-2", status=PredictionHistoryStatus.FAILED),
        ]
        client = _client_as(admin_user, records)

        response = client.get(HISTORY_PATH, params={"status": "failed"})
        _clear_overrides()

        assert response.status_code == 200
        payload = response.json()["data"]
        assert payload["count"] == 1
        assert payload["items"][0]["history_id"] == "hist-2"

    def test_filters_by_user_id(self, admin_user) -> None:
        records = [
            _make_history("user-a", "hist-1"),
            _make_history("user-b", "hist-2"),
        ]
        client = _client_as(admin_user, records)

        response = client.get(HISTORY_PATH, params={"user_id": "user-a"})
        _clear_overrides()

        assert response.status_code == 200
        payload = response.json()["data"]
        assert payload["count"] == 1
        assert payload["items"][0]["user_id"] == "user-a"

    def test_pagination_response_shape(self, admin_user) -> None:
        records = [_make_history("user-a", f"hist-{i}") for i in range(5)]
        client = _client_as(admin_user, records)

        response = client.get(HISTORY_PATH, params={"page": 1, "page_size": 2})
        _clear_overrides()

        pagination = response.json()["data"]["pagination"]
        assert pagination["current_page"] == 1
        assert pagination["page_size"] == 2
        assert pagination["total_records"] == 5
        assert pagination["total_pages"] == 3
        assert pagination["has_next"] is True
        assert pagination["has_previous"] is False


class TestGetHistoryDetail:
    def test_returns_record_regardless_of_owner(self, admin_user) -> None:
        records = [_make_history("user-a", "hist-1")]
        client = _client_as(admin_user, records)

        response = client.get(f"{HISTORY_PATH}/hist-1")
        _clear_overrides()

        assert response.status_code == 200
        assert response.json()["data"]["user_id"] == "user-a"

    def test_nonexistent_history_returns_404(self, admin_user) -> None:
        client = _client_as(admin_user, [])

        response = client.get(f"{HISTORY_PATH}/does-not-exist")
        _clear_overrides()

        assert response.status_code == 404

    def test_response_never_exposes_a_mutation_endpoint(self, admin_user) -> None:
        # Immutability check (ADR-041): the Admin History router exposes
        # no PUT/PATCH/DELETE for this resource -- only the two GET routes
        # registered above.
        route_methods = {
            (route.path, method)
            for route in app.routes
            if hasattr(route, "path") and route.path.startswith("/api/v1/admin/history")
            for method in getattr(route, "methods", set())
        }

        assert route_methods == {
            ("/api/v1/admin/history", "GET"),
            ("/api/v1/admin/history/{history_id}", "GET"),
        }
