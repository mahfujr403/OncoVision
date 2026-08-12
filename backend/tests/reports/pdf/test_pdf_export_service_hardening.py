"""Phase 6.6 Reporting Hardening tests for `PDFExportService` (ADR-042).

Mirrors `tests/reports/csv/test_csv_export_service_hardening.py` exactly,
covering only what Phase 6.6 adds on top of the Phase 6.4 behavior
already verified by `tests/reports/pdf/test_pdf_export_service.py`.
"""

import asyncio

import pytest

from app.core.config import settings
from app.reports.pdf.exceptions import PDFExportLimitExceededError
from app.reports.pdf.pdf_export_service import PDFExportService
from tests.reports.conftest_helpers import make_history_record
from tests.reports.repository_test_double import TrackingPredictionHistoryRepository


class TestPDFExportServiceExportLimit:
    """Verifies `PDFExportService.export_pdf()` enforces `Settings.REPORT_EXPORT_MAX_ROWS`."""

    def test_raises_when_matching_history_exceeds_the_configured_limit(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "REPORT_EXPORT_MAX_ROWS", 1)
        records = [
            make_history_record(history_id="hist-0001", user_id="user-0001"),
            make_history_record(history_id="hist-0002", user_id="user-0001"),
        ]
        repository = TrackingPredictionHistoryRepository(records)
        service = PDFExportService(history_repository=repository)

        with pytest.raises(PDFExportLimitExceededError):
            asyncio.run(service.export_pdf(user_id="user-0001"))

    def test_limit_check_short_circuits_before_listing_history(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "REPORT_EXPORT_MAX_ROWS", 1)
        records = [
            make_history_record(history_id="hist-0001", user_id="user-0001"),
            make_history_record(history_id="hist-0002", user_id="user-0001"),
        ]
        repository = TrackingPredictionHistoryRepository(records)
        service = PDFExportService(history_repository=repository)

        with pytest.raises(PDFExportLimitExceededError):
            asyncio.run(service.export_pdf(user_id="user-0001"))

        assert repository.list_by_user_calls == 0
        assert repository.count_by_user_calls == 1

    def test_succeeds_when_matching_history_is_within_the_configured_limit(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "REPORT_EXPORT_MAX_ROWS", 10)
        records = [
            make_history_record(history_id="hist-0001", user_id="user-0001"),
            make_history_record(history_id="hist-0002", user_id="user-0001"),
        ]
        repository = TrackingPredictionHistoryRepository(records)
        service = PDFExportService(history_repository=repository)

        result = asyncio.run(service.export_pdf(user_id="user-0001"))

        assert result.history_row_count == 2


class TestPDFExportServiceExportSize:
    """Verifies `PDFExportService.export_pdf()` enforces `Settings.REPORT_EXPORT_MAX_SIZE_BYTES`."""

    def test_raises_when_the_generated_document_exceeds_the_configured_size(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "REPORT_EXPORT_MAX_SIZE_BYTES", 1)
        records = [make_history_record(history_id="hist-0001", user_id="user-0001")]
        repository = TrackingPredictionHistoryRepository(records)
        service = PDFExportService(history_repository=repository)

        with pytest.raises(PDFExportLimitExceededError):
            asyncio.run(service.export_pdf(user_id="user-0001"))

    def test_succeeds_when_the_generated_document_is_within_the_configured_size(
        self,
    ) -> None:
        records = [make_history_record(history_id="hist-0001", user_id="user-0001")]
        repository = TrackingPredictionHistoryRepository(records)
        service = PDFExportService(history_repository=repository)

        result = asyncio.run(service.export_pdf(user_id="user-0001"))

        assert result.history_row_count == 1


class TestPDFExportServiceDuplicateQueryElimination:
    """Verifies `PDFExportService` no longer issues a duplicate `list_by_user()` query."""

    def test_history_is_retrieved_exactly_once_per_export(self) -> None:
        records = [
            make_history_record(history_id="hist-0001", user_id="user-0001"),
            make_history_record(history_id="hist-0002", user_id="user-0001"),
        ]
        repository = TrackingPredictionHistoryRepository(records)
        service = PDFExportService(history_repository=repository)

        asyncio.run(service.export_pdf(user_id="user-0001"))

        assert repository.list_by_user_calls == 1
