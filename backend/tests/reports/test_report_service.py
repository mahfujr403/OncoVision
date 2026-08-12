"""Tests for `ReportService` (Phase 6.1, ADR-037).

Uses an in-memory `PredictionHistoryRepository` implementation so these
tests exercise only `ReportService`'s own orchestration -- validation,
delegation to the repository, and delegation to `ReportBuilder` -- never
a real database.
"""

import asyncio

import pytest

from app.history.filters import PredictionHistoryFilter
from app.history.prediction_history import PredictionHistory
from app.repositories.prediction_history_repository import PredictionHistoryRepository
from app.reports.enums import ReportStatus
from app.reports.exceptions import InvalidReportRequestError
from app.schemas.report import ReportRequest
from app.services.report_service import ReportService
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


class TestReportServiceGeneration:
    """Verifies `ReportService.generate_report()` orchestration."""

    def test_generates_report_scoped_to_the_requesting_user(
        self, history_records: list[PredictionHistory]
    ) -> None:
        repository = InMemoryPredictionHistoryRepository(history_records)
        service = ReportService(history_repository=repository)

        report = asyncio.run(service.generate_report(user_id="user-0001", request=ReportRequest()))

        assert report.status == ReportStatus.GENERATED
        assert report.user_id == "user-0001"
        assert len(report.history) == 2
        assert all(record.user_id == "user-0001" for record in report.history)

    def test_user_with_no_history_receives_an_empty_report(
        self, history_records: list[PredictionHistory]
    ) -> None:
        repository = InMemoryPredictionHistoryRepository(history_records)
        service = ReportService(history_repository=repository)

        report = asyncio.run(
            service.generate_report(user_id="user-nobody", request=ReportRequest())
        )

        assert report.status == ReportStatus.EMPTY
        assert report.history == []

    def test_invalid_request_raises_before_touching_the_repository(self) -> None:
        class TrackingRepository(InMemoryPredictionHistoryRepository):
            def __init__(self) -> None:
                super().__init__()
                self.list_called = False

            async def list_by_user(self, *args, **kwargs):
                self.list_called = True
                return await super().list_by_user(*args, **kwargs)

        repository = TrackingRepository()
        service = ReportService(history_repository=repository)

        with pytest.raises(InvalidReportRequestError):
            asyncio.run(service.generate_report(user_id="", request=ReportRequest()))

        assert repository.list_called is False

    def test_filters_are_passed_through_to_the_repository_unchanged(
        self, history_records: list[PredictionHistory]
    ) -> None:
        repository = InMemoryPredictionHistoryRepository(history_records)
        service = ReportService(history_repository=repository)
        filters = PredictionHistoryFilter()

        asyncio.run(
            service.generate_report(
                user_id="user-0001", request=ReportRequest(filters=filters)
            )
        )

        assert repository.last_list_call is not None
        assert repository.last_list_call["filters"] is filters
        assert repository.last_list_call["user_id"] == "user-0001"

    def test_never_updates_or_deletes_existing_history_records(
        self, history_records: list[PredictionHistory]
    ) -> None:
        repository = InMemoryPredictionHistoryRepository(history_records)
        original_snapshot = [record.model_copy(deep=True) for record in history_records]
        service = ReportService(history_repository=repository)

        asyncio.run(service.generate_report(user_id="user-0001", request=ReportRequest()))

        assert repository._records == original_snapshot
