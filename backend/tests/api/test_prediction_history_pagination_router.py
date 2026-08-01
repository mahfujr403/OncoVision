"""Router-level tests for Phase 5.4 Prediction History Pagination & Filtering (ADR-035).

Exercises `GET /api/v1/predictions/history` through the full FastAPI
routing/validation/exception-handling stack via `fastapi.testclient.TestClient`,
using `app.dependency_overrides` to substitute the authenticated user
(`get_current_active_user`) and the Prediction History Service
(`get_prediction_history_service`) -- the same dependency-injection seams
already used throughout `app.dependencies` -- so no real database or JWT
is required.

Covers only what Phase 5.4 adds to the Phase 5.3 endpoint: the new
`page`/`page_size`/filter query parameters, the `pagination` block now
present on every response, and the `422` validation behavior for
inconsistent filter/pagination combinations. Phase 4/5.1-5.3 endpoint
behavior is unaffected and is not re-verified here.
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


def _make_history(user_id: str, history_id: str, created_at: str) -> PredictionHistory:
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
        status=PredictionHistoryStatus.SUCCESS,
        created_at=created_at,
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

    # Deliberately NOT used as a context manager: entering `TestClient` as a
    # context manager triggers `app`'s lifespan (`run_startup()`), which
    # attempts real database connectivity and AI Runtime/model downloads --
    # none of which this router-level test needs or has available. A plain
    # `TestClient(app)` instance still routes requests through the full
    # middleware/validation/exception-handling stack without running
    # startup/shutdown events.
    test_client = TestClient(app)
    test_client.oncovision_repository = repository  # type: ignore[attr-defined]

    yield test_client

    app.dependency_overrides.pop(get_current_active_user, None)
    app.dependency_overrides.pop(get_prediction_history_service, None)


class TestPredictionHistoryPaginationDefaults:
    """`GET /api/v1/predictions/history` with no query params (Phase 5.4, ADR-035)."""

    def test_no_query_params_returns_200_with_default_pagination(
        self, client: TestClient, current_user: User
    ) -> None:
        response = client.get(HISTORY_PATH)

        assert response.status_code == 200
        payload = response.json()
        assert payload["success"] is True
        pagination = payload["data"]["pagination"]
        assert pagination["current_page"] == 1
        assert pagination["page_size"] == 20
        assert pagination["total_records"] == 0
        assert pagination["total_pages"] == 0
        assert pagination["has_next"] is False
        assert pagination["has_previous"] is False


class TestPredictionHistoryPaginationQueryParams:
    """`GET /api/v1/predictions/history?page=...&page_size=...` (Phase 5.4, ADR-035)."""

    def test_page_and_page_size_are_passed_through_to_the_service(
        self, client: TestClient, current_user: User
    ) -> None:
        user_id = str(current_user.id)
        repository: InMemoryPredictionHistoryRepository = client.oncovision_repository  # type: ignore[attr-defined]

        import asyncio

        async def seed() -> None:
            for index in range(12):
                await repository.save(
                    _make_history(
                        user_id,
                        f"hist-{index}",
                        f"2026-07-27T{10 + index:02d}:00:00+00:00",
                    )
                )

        asyncio.run(seed())

        response = client.get(HISTORY_PATH, params={"page": 2, "page_size": 5})

        assert response.status_code == 200
        payload = response.json()["data"]
        pagination = payload["pagination"]
        assert pagination["current_page"] == 2
        assert pagination["page_size"] == 5
        assert pagination["total_records"] == 12
        assert pagination["total_pages"] == 3
        assert pagination["has_next"] is True
        assert pagination["has_previous"] is True
        assert len(payload["items"]) == 5


class TestPredictionHistoryPaginationValidation:
    """`422` behavior for invalid pagination/filter combinations (Phase 5.4, ADR-035)."""

    def test_min_confidence_greater_than_max_confidence_returns_422(
        self, client: TestClient
    ) -> None:
        response = client.get(
            HISTORY_PATH, params={"min_confidence": 90, "max_confidence": 10}
        )

        assert response.status_code == 422
        payload = response.json()
        assert payload["success"] is False
        assert payload["errors"] is not None

    def test_page_size_101_returns_422(self, client: TestClient) -> None:
        response = client.get(HISTORY_PATH, params={"page_size": 101})

        assert response.status_code == 422

    def test_page_zero_returns_422(self, client: TestClient) -> None:
        response = client.get(HISTORY_PATH, params={"page": 0})

        assert response.status_code == 422

    def test_start_date_after_end_date_returns_422(self, client: TestClient) -> None:
        response = client.get(
            HISTORY_PATH,
            params={
                "start_date": "2026-02-01T00:00:00+00:00",
                "end_date": "2026-01-01T00:00:00+00:00",
            },
        )

        assert response.status_code == 422
