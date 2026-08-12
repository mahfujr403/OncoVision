"""Router-level tests for Phase 5.5 Prediction History Detail Retrieval (ADR-035 update).

Exercises `GET /api/v1/predictions/history/{history_id}` through the full
FastAPI routing/validation/exception-handling stack via
`fastapi.testclient.TestClient`, using `app.dependency_overrides` to
substitute the authenticated user (`get_current_active_user`) and the
Prediction History Service (`get_prediction_history_service`) -- the same
dependency-injection seams already used by
`tests/api/test_prediction_history_pagination_router.py` -- so no real
database or JWT is required.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.dependencies.auth import get_current_active_user
from app.dependencies.services import get_prediction_history_service
from app.history.enums import PredictionHistoryStatus
from app.history.metadata import PredictionHistoryMetadata
from app.history.prediction_history import PredictionHistory
from app.history.summary import PredictionHistorySummary
from app.main import app
from app.models.enums import UserRole
from app.models.user import User
from app.services.prediction_history_service import PredictionHistoryService
from tests.history.conftest_helpers import make_context
from tests.history.test_prediction_history_repository import InMemoryPredictionHistoryRepository

HISTORY_PATH = "/api/v1/predictions/history"


def _make_user() -> User:
    return User(
        id=uuid.uuid4(),
        full_name="Test Pathologist",
        email="pathologist@example.com",
        password_hash="not-a-real-hash",
        role=UserRole.USER,
        is_active=True,
        is_verified=True,
    )


def _make_history(user_id: str, history_id: str) -> PredictionHistory:
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
        model_manifest_version="2026.07.1",
        processing_time_ms=154.8,
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
        status=PredictionHistoryStatus.SUCCESS,
        created_at="2026-07-27T10:00:00+00:00",
        metadata=metadata,
        summary=summary,
    )


@pytest.fixture
def current_user() -> User:
    return _make_user()


@pytest.fixture
def client(current_user: User):
    """A `TestClient` with authentication and the history repository faked out."""
    repository = InMemoryPredictionHistoryRepository()
    service = PredictionHistoryService(repository=repository)

    app.dependency_overrides[get_current_active_user] = lambda: current_user
    app.dependency_overrides[get_prediction_history_service] = lambda: service

    # Deliberately NOT used as a context manager -- see
    # `tests/api/test_prediction_history_pagination_router.py` for why.
    test_client = TestClient(app)
    test_client.oncovision_repository = repository  # type: ignore[attr-defined]

    yield test_client

    app.dependency_overrides.pop(get_current_active_user, None)
    app.dependency_overrides.pop(get_prediction_history_service, None)


class TestPredictionHistoryDetailFound:
    """`GET /api/v1/predictions/history/{history_id}` for an owned record (Phase 5.5, ADR-035 update)."""

    def test_existing_owned_record_returns_200_with_full_detail(
        self, client: TestClient, current_user: User
    ) -> None:
        user_id = str(current_user.id)
        repository: InMemoryPredictionHistoryRepository = client.oncovision_repository  # type: ignore[attr-defined]

        import asyncio

        history = _make_history(user_id, "hist-0001")
        asyncio.run(repository.save(history))

        response = client.get(f"{HISTORY_PATH}/hist-0001")

        assert response.status_code == 200
        payload = response.json()
        assert payload["success"] is True
        data = payload["data"]
        assert data["history_id"] == "hist-0001"
        assert data["predicted_class"] == "lung_aca"
        assert data["confidence"] == 91.2
        assert data["image_metadata"]["filename"] == history.metadata.image_filename
        assert data["image_metadata"]["width"] == history.metadata.image_width
        assert data["runtime_info"]["model_manifest_version"] == "2026.07.1"
        assert data["runtime_info"]["processing_time_ms"] == 154.8


class TestPredictionHistoryDetailNotFound:
    """`GET /api/v1/predictions/history/{history_id}` returns `404` per ADR-035's detail policy."""

    def test_nonexistent_history_id_returns_404(self, client: TestClient) -> None:
        response = client.get(f"{HISTORY_PATH}/does-not-exist")

        assert response.status_code == 404
        payload = response.json()
        assert payload["success"] is False

    def test_record_owned_by_a_different_user_returns_404(
        self, client: TestClient, current_user: User
    ) -> None:
        repository: InMemoryPredictionHistoryRepository = client.oncovision_repository  # type: ignore[attr-defined]

        import asyncio

        other_user_history = _make_history("someone-else", "hist-0002")
        asyncio.run(repository.save(other_user_history))

        response = client.get(f"{HISTORY_PATH}/hist-0002")

        assert response.status_code == 404
        payload = response.json()
        assert payload["success"] is False


class TestPredictionHistoryDetailAuthentication:
    """`GET /api/v1/predictions/history/{history_id}` requires authentication."""

    def test_missing_authentication_returns_401(self) -> None:
        repository = InMemoryPredictionHistoryRepository()
        service = PredictionHistoryService(repository=repository)
        app.dependency_overrides[get_prediction_history_service] = lambda: service

        test_client = TestClient(app)
        response = test_client.get(f"{HISTORY_PATH}/hist-0001")

        app.dependency_overrides.pop(get_prediction_history_service, None)

        assert response.status_code == 401
