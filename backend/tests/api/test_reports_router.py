"""Router-level tests for the Reporting API (`app.api.v1.reports`, ADR-041/ADR-042).

Exercises `GET /api/v1/reports/analytics`, `GET /api/v1/reports/export/csv`,
and `GET /api/v1/reports/export/pdf` through the full FastAPI
routing/validation/exception-handling stack via
`fastapi.testclient.TestClient`, using `app.dependency_overrides` to
substitute the authenticated user (`get_current_active_user`) and each
reporting service -- the same dependency-injection seam already used by
`tests/api/test_prediction_history_detail_router.py` -- so no real
database or JWT is required.

Covers the mandatory Phase 6.6 Reporting Hardening test surface:
analytics/CSV/PDF routers, authentication, authorization/ownership,
validation failures, empty history, and export limits.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.dependencies.auth import get_current_active_user
from app.dependencies.services import (
    get_csv_export_service,
    get_pdf_export_service,
    get_prediction_analytics_service,
)
from app.main import app
from app.models.enums import UserRole
from app.models.user import User
from app.reports.csv.csv_export_service import CSVExportService
from app.reports.pdf.pdf_export_service import PDFExportService
from app.services.prediction_analytics_service import PredictionAnalyticsService
from tests.reports.conftest_helpers import make_history_record
from tests.reports.repository_test_double import TrackingPredictionHistoryRepository

ANALYTICS_PATH = "/api/v1/reports/analytics"
CSV_EXPORT_PATH = "/api/v1/reports/export/csv"
PDF_EXPORT_PATH = "/api/v1/reports/export/pdf"


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


@pytest.fixture
def current_user() -> User:
    return _make_user()


@pytest.fixture
def repository() -> TrackingPredictionHistoryRepository:
    return TrackingPredictionHistoryRepository([])


@pytest.fixture
def client(current_user: User, repository: TrackingPredictionHistoryRepository):
    """A `TestClient` with authentication and every reporting service faked out."""
    analytics_service = PredictionAnalyticsService(repository)
    csv_service = CSVExportService(history_repository=repository, analytics_service=analytics_service)
    pdf_service = PDFExportService(history_repository=repository, analytics_service=analytics_service)

    app.dependency_overrides[get_current_active_user] = lambda: current_user
    app.dependency_overrides[get_prediction_analytics_service] = lambda: analytics_service
    app.dependency_overrides[get_csv_export_service] = lambda: csv_service
    app.dependency_overrides[get_pdf_export_service] = lambda: pdf_service

    test_client = TestClient(app)

    yield test_client

    app.dependency_overrides.pop(get_current_active_user, None)
    app.dependency_overrides.pop(get_prediction_analytics_service, None)
    app.dependency_overrides.pop(get_csv_export_service, None)
    app.dependency_overrides.pop(get_pdf_export_service, None)


def _seed(repository: TrackingPredictionHistoryRepository, user_id: str, count: int) -> None:
    for i in range(count):
        repository._records.append(
            make_history_record(history_id=f"hist-{i:04d}", user_id=user_id)
        )


class TestAnalyticsEndpoint:
    """`GET /api/v1/reports/analytics`."""

    def test_returns_200_with_expected_schema(
        self, client: TestClient, current_user: User, repository: TrackingPredictionHistoryRepository
    ) -> None:
        _seed(repository, str(current_user.id), 3)

        response = client.get(ANALYTICS_PATH)

        assert response.status_code == 200
        payload = response.json()
        assert payload["success"] is True
        assert payload["data"]["total_predictions"] == 3
        assert "analytics_id" in payload["data"]

    def test_empty_history_returns_200_with_zeroed_analytics(self, client: TestClient) -> None:
        response = client.get(ANALYTICS_PATH)

        assert response.status_code == 200
        payload = response.json()
        assert payload["data"]["total_predictions"] == 0

    def test_scoped_to_the_authenticated_user_only(
        self, client: TestClient, current_user: User, repository: TrackingPredictionHistoryRepository
    ) -> None:
        _seed(repository, "some-other-user", 5)
        _seed(repository, str(current_user.id), 2)

        response = client.get(ANALYTICS_PATH)

        assert response.json()["data"]["total_predictions"] == 2

    def test_missing_authentication_returns_401(self) -> None:
        repository_double = TrackingPredictionHistoryRepository([])
        analytics_service = PredictionAnalyticsService(repository_double)
        app.dependency_overrides[get_prediction_analytics_service] = lambda: analytics_service

        test_client = TestClient(app)
        response = test_client.get(ANALYTICS_PATH)

        app.dependency_overrides.pop(get_prediction_analytics_service, None)

        assert response.status_code == 401

    def test_export_limit_exceeded_returns_413(
        self,
        client: TestClient,
        current_user: User,
        repository: TrackingPredictionHistoryRepository,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(settings, "REPORT_EXPORT_MAX_ROWS", 1)
        _seed(repository, str(current_user.id), 2)

        response = client.get(ANALYTICS_PATH)

        assert response.status_code == 413
        payload = response.json()
        assert payload["success"] is False


class TestCSVExportEndpoint:
    """`GET /api/v1/reports/export/csv`."""

    def test_returns_200_with_a_csv_attachment(
        self, client: TestClient, current_user: User, repository: TrackingPredictionHistoryRepository
    ) -> None:
        _seed(repository, str(current_user.id), 2)

        response = client.get(CSV_EXPORT_PATH)

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        assert "attachment" in response.headers["content-disposition"]
        assert "prediction_history.csv" in response.headers["content-disposition"]
        assert "req-" in response.text

    def test_empty_history_returns_200_with_a_zero_row_csv(self, client: TestClient) -> None:
        response = client.get(CSV_EXPORT_PATH)

        assert response.status_code == 200

    def test_missing_authentication_returns_401(self) -> None:
        repository_double = TrackingPredictionHistoryRepository([])
        app.dependency_overrides[get_csv_export_service] = lambda: CSVExportService(
            history_repository=repository_double
        )

        test_client = TestClient(app)
        response = test_client.get(CSV_EXPORT_PATH)

        app.dependency_overrides.pop(get_csv_export_service, None)

        assert response.status_code == 401

    def test_export_limit_exceeded_returns_413(
        self,
        client: TestClient,
        current_user: User,
        repository: TrackingPredictionHistoryRepository,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(settings, "REPORT_EXPORT_MAX_ROWS", 1)
        _seed(repository, str(current_user.id), 2)

        response = client.get(CSV_EXPORT_PATH)

        assert response.status_code == 413
        payload = response.json()
        assert payload["success"] is False

    def test_ownership_isolation_excludes_another_users_records(
        self, client: TestClient, current_user: User, repository: TrackingPredictionHistoryRepository
    ) -> None:
        repository._records.append(
            make_history_record(
                history_id="hist-other-user",
                request_id="req-other-user-secret",
                user_id="user-b",
            )
        )
        repository._records.append(
            make_history_record(
                history_id="hist-mine",
                request_id="req-mine",
                user_id=str(current_user.id),
            )
        )

        response = client.get(CSV_EXPORT_PATH)

        assert response.status_code == 200
        assert "req-mine" in response.text
        assert "req-other-user-secret" not in response.text
        assert "user-b" not in response.text


class TestPDFExportEndpoint:
    """`GET /api/v1/reports/export/pdf`."""

    def test_returns_200_with_a_pdf_attachment(
        self, client: TestClient, current_user: User, repository: TrackingPredictionHistoryRepository
    ) -> None:
        _seed(repository, str(current_user.id), 2)

        response = client.get(PDF_EXPORT_PATH)

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/pdf")
        assert "attachment" in response.headers["content-disposition"]
        assert "prediction_report.pdf" in response.headers["content-disposition"]
        assert response.content.startswith(b"%PDF")

    def test_empty_history_returns_200_with_a_zero_row_pdf(self, client: TestClient) -> None:
        response = client.get(PDF_EXPORT_PATH)

        assert response.status_code == 200
        assert response.content.startswith(b"%PDF")

    def test_missing_authentication_returns_401(self) -> None:
        repository_double = TrackingPredictionHistoryRepository([])
        app.dependency_overrides[get_pdf_export_service] = lambda: PDFExportService(
            history_repository=repository_double
        )

        test_client = TestClient(app)
        response = test_client.get(PDF_EXPORT_PATH)

        app.dependency_overrides.pop(get_pdf_export_service, None)

        assert response.status_code == 401

    def test_export_limit_exceeded_returns_413(
        self,
        client: TestClient,
        current_user: User,
        repository: TrackingPredictionHistoryRepository,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(settings, "REPORT_EXPORT_MAX_ROWS", 1)
        _seed(repository, str(current_user.id), 2)

        response = client.get(PDF_EXPORT_PATH)

        assert response.status_code == 413
        payload = response.json()
        assert payload["success"] is False

    def test_ownership_isolation_excludes_another_users_records(
        self, client: TestClient, current_user: User, repository: TrackingPredictionHistoryRepository
    ) -> None:
        """Ownership is verified at the `PDFExportService`/repository input, not by parsing PDF bytes.

        Directly asserting on rendered PDF byte content is unreliable
        (ReportLab's output is compressed/encoded and not guaranteed to
        contain plain, greppable text), so this test instead verifies
        the contract the PDF is built from: only the authenticated
        user's own records ever reach `PDFExportService.export_pdf()` /
        `PDFBuilder.build()`, exactly as already verified directly
        against the repository query in
        `tests/reports/pdf/test_pdf_export_service.py`. Combined with
        that existing, dedicated builder-input test, this is sufficient
        evidence that another user's data can never appear in the
        rendered document -- without adding a PDF-parsing dependency
        solely for this assertion.
        """
        repository._records.append(
            make_history_record(history_id="hist-other-user", user_id="user-b")
        )
        repository._records.append(
            make_history_record(history_id="hist-mine", user_id=str(current_user.id))
        )

        response = client.get(PDF_EXPORT_PATH)

        assert response.status_code == 200
        assert repository.last_list_call is not None
        assert repository.last_list_call["user_id"] == str(current_user.id)
        assert repository.last_list_call["user_id"] != "user-b"


class TestInvalidParameters:
    """Invalid-request handling for the Reporting API.

    `GET /api/v1/reports/analytics`, `/export/csv`, and `/export/pdf`
    intentionally accept no client-supplied query parameters -- Phase
    6.5 (ADR-041) explicitly deferred filtering to a later phase, so
    there is no reporting-specific filter/pagination/date-range/
    confidence-range/status-filter input for this router to validate.
    That existing, already-tested validation
    (`app.history.filters.PredictionHistoryFilter`, exercised by
    `tests/history` and `tests/api/test_prediction_history_pagination_router.py`)
    will apply automatically the moment such parameters are added to
    this router in a future phase; duplicating it here now would be
    invalid validation logic this router doesn't yet own (explicitly out
    of scope per this phase's directive).

    The one genuinely invalid-*input* surface this router does have
    today is the `Authorization` header itself, so that is what is
    verified here.
    """

    def test_malformed_bearer_token_returns_401(self) -> None:
        test_client = TestClient(app)

        response = test_client.get(
            ANALYTICS_PATH, headers={"Authorization": "Bearer not-a-real-jwt"}
        )

        assert response.status_code == 401
        payload = response.json()
        assert payload["success"] is False

    def test_non_bearer_authorization_scheme_returns_401(self) -> None:
        test_client = TestClient(app)

        response = test_client.get(
            CSV_EXPORT_PATH, headers={"Authorization": "Basic dXNlcjpwYXNz"}
        )

        assert response.status_code == 401

    def test_extra_unrecognized_query_parameters_are_ignored_not_rejected(
        self, client: TestClient, current_user: User, repository: TrackingPredictionHistoryRepository
    ) -> None:
        """FastAPI ignores undeclared query parameters by default; this pins that behavior.

        Not a validation gap: this router declares no query parameters
        at all, so there is nothing for an extra one to conflict with.
        """
        _seed(repository, str(current_user.id), 1)

        response = client.get(ANALYTICS_PATH, params={"unexpected": "value"})

        assert response.status_code == 200


class TestFailurePaths:
    """Verifies unexpected failures never leak internal details to the client.

    Exercises the full FastAPI stack -- including
    `app.core.exceptions.unhandled_exception_handler` and the Phase 6.6
    `*GenerationError` wiring added to each service -- end to end,
    complementing the service-level assertions in
    `tests/reports/test_generation_failure_handling.py`.
    """

    def test_csv_builder_failure_returns_a_sanitized_500(
        self, current_user: User, repository: TrackingPredictionHistoryRepository
    ) -> None:
        from tests.reports.test_generation_failure_handling import _ExplodingBuilder

        _seed(repository, str(current_user.id), 1)
        analytics_service = PredictionAnalyticsService(repository)
        csv_service = CSVExportService(
            history_repository=repository,
            analytics_service=analytics_service,
            builder=_ExplodingBuilder(),
        )

        app.dependency_overrides[get_current_active_user] = lambda: current_user
        app.dependency_overrides[get_csv_export_service] = lambda: csv_service
        test_client = TestClient(app, raise_server_exceptions=False)

        response = test_client.get(CSV_EXPORT_PATH)

        app.dependency_overrides.pop(get_current_active_user, None)
        app.dependency_overrides.pop(get_csv_export_service, None)

        assert response.status_code == 500
        payload = response.json()
        assert payload["success"] is False
        assert "Traceback" not in payload["message"]
        assert "corrupt template state" not in payload["message"]

    def test_repository_failure_returns_a_sanitized_500(self, current_user: User) -> None:
        from tests.reports.test_generation_failure_handling import _FailingRepository

        repository_double = _FailingRepository(
            [make_history_record(history_id="hist-0001", user_id=str(current_user.id))]
        )
        analytics_service = PredictionAnalyticsService(repository_double)

        app.dependency_overrides[get_current_active_user] = lambda: current_user
        app.dependency_overrides[get_prediction_analytics_service] = lambda: analytics_service
        test_client = TestClient(app, raise_server_exceptions=False)

        response = test_client.get(ANALYTICS_PATH)

        app.dependency_overrides.pop(get_current_active_user, None)
        app.dependency_overrides.pop(get_prediction_analytics_service, None)

        assert response.status_code == 500
        payload = response.json()
        assert payload["success"] is False
        assert "ConnectionError" not in payload["message"]
        assert "simulated database" not in payload["message"]
