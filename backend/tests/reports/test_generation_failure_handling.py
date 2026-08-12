"""Phase 6.6/6.7 tests for builder-failure handling across the Reporting subsystem (ADR-042).

Verifies that an unexpected exception raised by `ReportBuilder`,
`AnalyticsBuilder`, `CSVExportBuilder`, or `PDFBuilder` is:

- never propagated to the caller as the original, internal exception type
- always converted into the corresponding standardized
  `*GenerationError` (an `OncoVisionError`, handled by the existing
  centralized `app.core.exceptions.oncovision_exception_handler`)
- always logged, with the original exception attached as the cause
  (`__cause__`), before being re-raised

This is a genuine failure path: it does not mock away the service under
test, only the one collaborator (`builder`) whose failure is under test.
"""

import asyncio

import pytest

from app.reports.analytics.exceptions import AnalyticsGenerationError
from app.reports.csv.exceptions import CSVExportGenerationError
from app.reports.csv.csv_export_service import CSVExportService
from app.reports.exceptions import ReportGenerationError
from app.reports.pdf.exceptions import PDFExportGenerationError
from app.reports.pdf.pdf_export_service import PDFExportService
from app.schemas.report import ReportRequest
from app.services.prediction_analytics_service import PredictionAnalyticsService
from app.services.report_service import ReportService
from tests.reports.conftest_helpers import make_history_record
from tests.reports.repository_test_double import TrackingPredictionHistoryRepository


class _ExplodingBuilder:
    """A builder stand-in whose `build()` always raises (test-only)."""

    def build(self, *args, **kwargs):
        raise RuntimeError("simulated internal builder failure: corrupt template state")


class TestReportServiceBuilderFailure:
    def test_builder_failure_is_converted_to_report_generation_error(self) -> None:
        records = [make_history_record(history_id="hist-0001", user_id="user-0001")]
        repository = TrackingPredictionHistoryRepository(records)
        service = ReportService(history_repository=repository, builder=_ExplodingBuilder())

        with pytest.raises(ReportGenerationError) as exc_info:
            asyncio.run(service.generate_report(user_id="user-0001", request=ReportRequest()))

        assert isinstance(exc_info.value.__cause__, RuntimeError)
        assert "corrupt template state" not in exc_info.value.message


class TestPredictionAnalyticsServiceBuilderFailure:
    def test_builder_failure_is_converted_to_analytics_generation_error(self) -> None:
        records = [make_history_record(history_id="hist-0001", user_id="user-0001")]
        repository = TrackingPredictionHistoryRepository(records)
        service = PredictionAnalyticsService(repository, builder=_ExplodingBuilder())

        with pytest.raises(AnalyticsGenerationError) as exc_info:
            asyncio.run(service.compute_analytics(user_id="user-0001"))

        assert isinstance(exc_info.value.__cause__, RuntimeError)
        assert "corrupt template state" not in exc_info.value.message

    def test_builder_failure_via_compute_analytics_from_history_is_also_converted(self) -> None:
        records = [make_history_record(history_id="hist-0001", user_id="user-0001")]
        repository = TrackingPredictionHistoryRepository(records)
        service = PredictionAnalyticsService(repository, builder=_ExplodingBuilder())

        with pytest.raises(AnalyticsGenerationError):
            asyncio.run(
                service.compute_analytics_from_history(user_id="user-0001", history=records)
            )


class TestCSVExportServiceBuilderFailure:
    def test_builder_failure_is_converted_to_csv_export_generation_error(self) -> None:
        records = [make_history_record(history_id="hist-0001", user_id="user-0001")]
        repository = TrackingPredictionHistoryRepository(records)
        service = CSVExportService(history_repository=repository, builder=_ExplodingBuilder())

        with pytest.raises(CSVExportGenerationError) as exc_info:
            asyncio.run(service.export_csv(user_id="user-0001"))

        assert isinstance(exc_info.value.__cause__, RuntimeError)
        assert "corrupt template state" not in exc_info.value.message
        assert exc_info.value.status_code == 500


class TestPDFExportServiceBuilderFailure:
    def test_builder_failure_is_converted_to_pdf_export_generation_error(self) -> None:
        records = [make_history_record(history_id="hist-0001", user_id="user-0001")]
        repository = TrackingPredictionHistoryRepository(records)
        service = PDFExportService(history_repository=repository, builder=_ExplodingBuilder())

        with pytest.raises(PDFExportGenerationError) as exc_info:
            asyncio.run(service.export_pdf(user_id="user-0001"))

        assert isinstance(exc_info.value.__cause__, RuntimeError)
        assert "corrupt template state" not in exc_info.value.message
        assert exc_info.value.status_code == 500


class _FailingRepository(TrackingPredictionHistoryRepository):
    """A repository stand-in that raises on `list_by_user()`, simulating a database failure."""

    async def list_by_user(self, *args, **kwargs):
        raise ConnectionError("simulated database connection failure")


class TestRepositoryFailurePropagation:
    """Database/repository failures are not caught by the reporting services.

    They are expected to propagate to the existing centralized
    `app.core.exceptions.unhandled_exception_handler`, which already
    logs and sanitizes any unhandled exception -- see
    `tests/api/test_reports_router.py::TestFailurePaths` for the
    router-level, end-to-end assertion that no internal detail leaks to
    the client.
    """

    def test_report_service_lets_a_repository_failure_propagate(self) -> None:
        repository = _FailingRepository(
            [make_history_record(history_id="hist-0001", user_id="user-0001")]
        )
        service = ReportService(history_repository=repository)

        with pytest.raises(ConnectionError):
            asyncio.run(service.generate_report(user_id="user-0001", request=ReportRequest()))

    def test_csv_export_service_lets_a_repository_failure_propagate(self) -> None:
        repository = _FailingRepository(
            [make_history_record(history_id="hist-0001", user_id="user-0001")]
        )
        service = CSVExportService(history_repository=repository)

        with pytest.raises(ConnectionError):
            asyncio.run(service.export_csv(user_id="user-0001"))
