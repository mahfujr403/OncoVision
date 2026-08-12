"""Phase 6.6 Reporting Hardening tests for `PredictionAnalyticsService` (ADR-042).

Covers only what Phase 6.6 adds on top of the Phase 6.2 behavior already
verified by `tests/reports/analytics/test_analytics_service.py`:

- The configurable `Settings.REPORT_EXPORT_MAX_ROWS` limit safeguard,
  enforced via an up-front `count_by_user()` check before any history
  rows are retrieved.
- `compute_analytics_from_history()`, the new entry point used by
  `CSVExportService`/`PDFExportService` to avoid a duplicate
  `list_by_user()` query.
"""

import asyncio

import pytest

from app.core.config import settings
from app.reports.analytics.exceptions import (
    AnalyticsExportLimitExceededError,
    InvalidAnalyticsRequestError,
)
from app.services.prediction_analytics_service import PredictionAnalyticsService
from tests.reports.conftest_helpers import make_history_record
from tests.reports.repository_test_double import TrackingPredictionHistoryRepository


class TestPredictionAnalyticsServiceExportLimit:
    """Verifies `PredictionAnalyticsService.compute_analytics()` enforces `Settings.REPORT_EXPORT_MAX_ROWS`."""

    def test_raises_when_matching_history_exceeds_the_configured_limit(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "REPORT_EXPORT_MAX_ROWS", 1)
        records = [
            make_history_record(history_id="hist-0001", user_id="user-0001"),
            make_history_record(history_id="hist-0002", user_id="user-0001"),
        ]
        repository = TrackingPredictionHistoryRepository(records)
        service = PredictionAnalyticsService(repository)

        with pytest.raises(AnalyticsExportLimitExceededError):
            asyncio.run(service.compute_analytics(user_id="user-0001"))

    def test_limit_check_short_circuits_before_listing_history(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "REPORT_EXPORT_MAX_ROWS", 1)
        records = [
            make_history_record(history_id="hist-0001", user_id="user-0001"),
            make_history_record(history_id="hist-0002", user_id="user-0001"),
        ]
        repository = TrackingPredictionHistoryRepository(records)
        service = PredictionAnalyticsService(repository)

        with pytest.raises(AnalyticsExportLimitExceededError):
            asyncio.run(service.compute_analytics(user_id="user-0001"))

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
        service = PredictionAnalyticsService(repository)

        result = asyncio.run(service.compute_analytics(user_id="user-0001"))

        assert result.total_predictions == 2


class TestComputeAnalyticsFromHistory:
    """Verifies `PredictionAnalyticsService.compute_analytics_from_history()`."""

    def test_never_touches_the_repository(self) -> None:
        records = [
            make_history_record(history_id="hist-0001", user_id="user-0001"),
            make_history_record(history_id="hist-0002", user_id="user-0001"),
        ]
        repository = TrackingPredictionHistoryRepository(records)
        service = PredictionAnalyticsService(repository)

        asyncio.run(service.compute_analytics_from_history(user_id="user-0001", history=records))

        assert repository.list_by_user_calls == 0
        assert repository.count_by_user_calls == 0

    def test_still_validates_the_authenticated_user(self) -> None:
        repository = TrackingPredictionHistoryRepository([])
        service = PredictionAnalyticsService(repository)

        with pytest.raises(InvalidAnalyticsRequestError):
            asyncio.run(service.compute_analytics_from_history(user_id="", history=[]))

    def test_produces_the_same_result_as_compute_analytics_given_the_same_history(self) -> None:
        records = [
            make_history_record(history_id="hist-0001", user_id="user-0001"),
            make_history_record(history_id="hist-0002", user_id="user-0001"),
        ]
        repository = TrackingPredictionHistoryRepository(records)
        service = PredictionAnalyticsService(repository)

        direct = asyncio.run(service.compute_analytics(user_id="user-0001"))
        from_history = asyncio.run(
            service.compute_analytics_from_history(user_id="user-0001", history=records)
        )

        assert from_history.total_predictions == direct.total_predictions
        assert from_history.successful_predictions == direct.successful_predictions
        assert from_history.failed_predictions == direct.failed_predictions
        assert from_history.success_rate == direct.success_rate
        assert from_history.average_confidence == direct.average_confidence
        assert from_history.class_distribution == direct.class_distribution

    def test_empty_history_produces_empty_analytics(self) -> None:
        repository = TrackingPredictionHistoryRepository([])
        service = PredictionAnalyticsService(repository)

        result = asyncio.run(
            service.compute_analytics_from_history(user_id="user-0001", history=[])
        )

        assert result.total_predictions == 0
