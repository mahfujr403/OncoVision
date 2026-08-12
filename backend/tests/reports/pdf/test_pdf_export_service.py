"""Tests for `PDFExportService` (Phase 6.4, ADR-040).

Uses an in-memory `PredictionHistoryRepository` implementation so these
tests exercise only `PDFExportService`'s own orchestration -- validation,
delegation to the repository, delegation to `PredictionAnalyticsService`,
and delegation to `PDFBuilder` -- never a real database. Mirrors
`tests.reports.csv.test_csv_export_service`.
"""

import asyncio

import pytest

from app.history.filters import PredictionHistoryFilter
from app.history.prediction_history import PredictionHistory
from app.repositories.prediction_history_repository import PredictionHistoryRepository
from app.reports.pdf.enums import PDFPageSize
from app.reports.pdf.exceptions import InvalidPDFExportRequestError
from app.reports.pdf.pdf_export_service import PDFExportService
from app.services.prediction_analytics_service import PredictionAnalyticsService
from tests.reports.conftest_helpers import make_history_record


class InMemoryPredictionHistoryRepository(PredictionHistoryRepository):
    """Minimal in-memory stand-in for `PredictionHistoryRepository` (test-only)."""

    def __init__(self, records: list[PredictionHistory] | None = None) -> None:
        self._records = list(records or [])
        self.last_list_call: dict | None = None

    async def save(self, history: PredictionHistory) -> PredictionHistory:
        self._records.append(history)
        return history

    async def get_by_id(self, history_id: str, user_id: str) -> PredictionHistory | None:
        for record in self._records:
            if record.history_id == history_id and record.user_id == user_id:
                return record
        return None

    async def list_by_user(
        self,
        user_id: str,
        limit: int,
        offset: int,
        filters: PredictionHistoryFilter | None = None,
    ) -> list[PredictionHistory]:
        self.last_list_call = {
            "user_id": user_id,
            "limit": limit,
            "offset": offset,
            "filters": filters,
        }
        return [record for record in self._records if record.user_id == user_id][offset : offset + limit]

    async def count_by_user(
        self, user_id: str, filters: PredictionHistoryFilter | None = None
    ) -> int:
        return len([record for record in self._records if record.user_id == user_id])


@pytest.fixture
def history_records() -> list[PredictionHistory]:
    return [
        make_history_record(history_id="hist-0001", user_id="user-0001"),
        make_history_record(history_id="hist-0002", user_id="user-0001"),
        make_history_record(history_id="hist-0003", user_id="user-0002"),
    ]


class TestPDFExportServiceExport:
    """Verifies `PDFExportService.export_pdf()` orchestration."""

    def test_exports_pdf_scoped_to_the_requesting_user(
        self, history_records: list[PredictionHistory]
    ) -> None:
        repository = InMemoryPredictionHistoryRepository(history_records)
        service = PDFExportService(history_repository=repository)

        result = asyncio.run(service.export_pdf(user_id="user-0001"))

        assert result.user_id == "user-0001"
        assert result.history_row_count == 2
        assert result.content.startswith(b"%PDF")

    def test_user_with_no_history_receives_a_zero_row_result(
        self, history_records: list[PredictionHistory]
    ) -> None:
        repository = InMemoryPredictionHistoryRepository(history_records)
        service = PDFExportService(history_repository=repository)

        result = asyncio.run(service.export_pdf(user_id="user-nobody"))

        assert result.history_row_count == 0
        assert result.content.startswith(b"%PDF")

    def test_invalid_user_id_raises_before_touching_the_repository(self) -> None:
        class TrackingRepository(InMemoryPredictionHistoryRepository):
            def __init__(self) -> None:
                super().__init__()
                self.list_called = False

            async def list_by_user(self, *args, **kwargs):
                self.list_called = True
                return await super().list_by_user(*args, **kwargs)

        repository = TrackingRepository()
        service = PDFExportService(history_repository=repository)

        with pytest.raises(InvalidPDFExportRequestError):
            asyncio.run(service.export_pdf(user_id=""))

        assert repository.list_called is False

    def test_unsupported_page_size_raises_before_touching_the_repository(
        self, history_records: list[PredictionHistory]
    ) -> None:
        class TrackingRepository(InMemoryPredictionHistoryRepository):
            def __init__(self, records) -> None:
                super().__init__(records)
                self.list_called = False

            async def list_by_user(self, *args, **kwargs):
                self.list_called = True
                return await super().list_by_user(*args, **kwargs)

        repository = TrackingRepository(history_records)
        service = PDFExportService(history_repository=repository)

        with pytest.raises(InvalidPDFExportRequestError):
            asyncio.run(service.export_pdf(user_id="user-0001", page_size="letter"))  # type: ignore[arg-type]

        assert repository.list_called is False

    def test_filters_are_passed_through_to_the_repository_unchanged(
        self, history_records: list[PredictionHistory]
    ) -> None:
        repository = InMemoryPredictionHistoryRepository(history_records)
        service = PDFExportService(history_repository=repository)
        filters = PredictionHistoryFilter()

        asyncio.run(service.export_pdf(user_id="user-0001", filters=filters))

        assert repository.last_list_call is not None
        assert repository.last_list_call["filters"] is filters
        assert repository.last_list_call["user_id"] == "user-0001"

    def test_uses_a4_page_size_by_default(self, history_records: list[PredictionHistory]) -> None:
        repository = InMemoryPredictionHistoryRepository(history_records)
        service = PDFExportService(history_repository=repository)

        result = asyncio.run(service.export_pdf(user_id="user-0001"))

        assert result.content.startswith(b"%PDF")

    def test_uses_a_default_prediction_analytics_service_when_none_supplied(
        self, history_records: list[PredictionHistory]
    ) -> None:
        repository = InMemoryPredictionHistoryRepository(history_records)
        service = PDFExportService(history_repository=repository)

        assert isinstance(service._analytics_service, PredictionAnalyticsService)

    def test_never_updates_or_deletes_existing_history_records(
        self, history_records: list[PredictionHistory]
    ) -> None:
        repository = InMemoryPredictionHistoryRepository(history_records)
        original_snapshot = [record.model_copy(deep=True) for record in history_records]
        service = PDFExportService(history_repository=repository)

        asyncio.run(service.export_pdf(user_id="user-0001"))

        assert repository._records == original_snapshot

    def test_explicit_a4_page_size_is_accepted(
        self, history_records: list[PredictionHistory]
    ) -> None:
        repository = InMemoryPredictionHistoryRepository(history_records)
        service = PDFExportService(history_repository=repository)

        result = asyncio.run(service.export_pdf(user_id="user-0001", page_size=PDFPageSize.A4))

        assert result.content.startswith(b"%PDF")
