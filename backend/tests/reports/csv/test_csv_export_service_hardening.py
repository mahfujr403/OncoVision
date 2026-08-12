"""Phase 6.6 Reporting Hardening tests for `CSVExportService` (ADR-042).

Covers only what Phase 6.6 adds on top of the Phase 6.3 behavior already
verified by `tests/reports/csv/test_csv_export_service.py`:

- The configurable `Settings.REPORT_EXPORT_MAX_ROWS` export-limit
  safeguard, enforced via an up-front `count_by_user()` check before any
  history rows are retrieved.
- The configurable `Settings.REPORT_EXPORT_MAX_SIZE_BYTES` document-size
  safeguard, enforced after `CSVExportBuilder` has serialized the
  document.
- Elimination of the Phase 6.3-6.5 duplicate-query regression, where
  `PredictionAnalyticsService.compute_analytics()` issued its own,
  independent `list_by_user()` query for the same `user_id`/`filters`
  pair `CSVExportService._retrieve()` already queried itself.
"""

import asyncio

import pytest

from app.core.config import settings
from app.reports.csv.csv_export_service import CSVExportService
from app.reports.csv.exceptions import CSVExportLimitExceededError
from tests.reports.conftest_helpers import make_history_record
from tests.reports.repository_test_double import TrackingPredictionHistoryRepository


class TestCSVExportServiceExportLimit:
    """Verifies `CSVExportService.export_csv()` enforces `Settings.REPORT_EXPORT_MAX_ROWS`."""

    def test_raises_when_matching_history_exceeds_the_configured_limit(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "REPORT_EXPORT_MAX_ROWS", 1)
        records = [
            make_history_record(history_id="hist-0001", user_id="user-0001"),
            make_history_record(history_id="hist-0002", user_id="user-0001"),
        ]
        repository = TrackingPredictionHistoryRepository(records)
        service = CSVExportService(history_repository=repository)

        with pytest.raises(CSVExportLimitExceededError):
            asyncio.run(service.export_csv(user_id="user-0001"))

    def test_limit_check_short_circuits_before_listing_history(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "REPORT_EXPORT_MAX_ROWS", 1)
        records = [
            make_history_record(history_id="hist-0001", user_id="user-0001"),
            make_history_record(history_id="hist-0002", user_id="user-0001"),
        ]
        repository = TrackingPredictionHistoryRepository(records)
        service = CSVExportService(history_repository=repository)

        with pytest.raises(CSVExportLimitExceededError):
            asyncio.run(service.export_csv(user_id="user-0001"))

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
        service = CSVExportService(history_repository=repository)

        result = asyncio.run(service.export_csv(user_id="user-0001"))

        assert result.history_row_count == 2


class TestCSVExportServiceExportSize:
    """Verifies `CSVExportService.export_csv()` enforces `Settings.REPORT_EXPORT_MAX_SIZE_BYTES`."""

    def test_raises_when_the_generated_document_exceeds_the_configured_size(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "REPORT_EXPORT_MAX_SIZE_BYTES", 1)
        records = [make_history_record(history_id="hist-0001", user_id="user-0001")]
        repository = TrackingPredictionHistoryRepository(records)
        service = CSVExportService(history_repository=repository)

        with pytest.raises(CSVExportLimitExceededError):
            asyncio.run(service.export_csv(user_id="user-0001"))

    def test_succeeds_when_the_generated_document_is_within_the_configured_size(
        self,
    ) -> None:
        records = [make_history_record(history_id="hist-0001", user_id="user-0001")]
        repository = TrackingPredictionHistoryRepository(records)
        service = CSVExportService(history_repository=repository)

        result = asyncio.run(service.export_csv(user_id="user-0001"))

        assert result.history_row_count == 1


class TestCSVExportServiceDuplicateQueryElimination:
    """Verifies `CSVExportService` no longer issues a duplicate `list_by_user()` query."""

    def test_history_is_retrieved_exactly_once_per_export(self) -> None:
        records = [
            make_history_record(history_id="hist-0001", user_id="user-0001"),
            make_history_record(history_id="hist-0002", user_id="user-0001"),
        ]
        repository = TrackingPredictionHistoryRepository(records)
        service = CSVExportService(history_repository=repository)

        asyncio.run(service.export_csv(user_id="user-0001"))

        assert repository.list_by_user_calls == 1

    def test_analytics_derived_from_pre_fetched_history_match_a_direct_computation(self) -> None:
        """`compute_analytics_from_history()` must be output-equivalent to `compute_analytics()`."""
        from app.services.prediction_analytics_service import PredictionAnalyticsService

        records = [
            make_history_record(history_id="hist-0001", user_id="user-0001"),
            make_history_record(history_id="hist-0002", user_id="user-0001"),
        ]
        repository = TrackingPredictionHistoryRepository(records)
        analytics_service = PredictionAnalyticsService(repository)

        direct = asyncio.run(analytics_service.compute_analytics(user_id="user-0001"))
        from_history = asyncio.run(
            analytics_service.compute_analytics_from_history(user_id="user-0001", history=records)
        )

        assert from_history.total_predictions == direct.total_predictions
        assert from_history.success_rate == direct.success_rate
        assert from_history.class_distribution == direct.class_distribution
