"""Phase 6.6 Reporting Hardening tests for `ReportService` (ADR-042).

Covers only what Phase 6.6 adds on top of the Phase 6.1 behavior already
verified by `tests/reports/test_report_service.py`: the configurable
`Settings.REPORT_EXPORT_MAX_ROWS` export-limit safeguard, enforced via an
up-front `count_by_user()` check before any history rows are retrieved.
"""

import asyncio

import pytest

from app.core.config import settings
from app.reports.exceptions import ReportExportLimitExceededError
from app.schemas.report import ReportRequest
from app.services.report_service import ReportService
from tests.reports.conftest_helpers import make_history_record
from tests.reports.repository_test_double import TrackingPredictionHistoryRepository


class TestReportServiceExportLimit:
    """Verifies `ReportService.generate_report()` enforces `Settings.REPORT_EXPORT_MAX_ROWS`."""

    def test_raises_when_matching_history_exceeds_the_configured_limit(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "REPORT_EXPORT_MAX_ROWS", 1)
        records = [
            make_history_record(history_id="hist-0001", user_id="user-0001"),
            make_history_record(history_id="hist-0002", user_id="user-0001"),
        ]
        repository = TrackingPredictionHistoryRepository(records)
        service = ReportService(history_repository=repository)

        with pytest.raises(ReportExportLimitExceededError):
            asyncio.run(service.generate_report(user_id="user-0001", request=ReportRequest()))

    def test_limit_check_short_circuits_before_listing_history(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "REPORT_EXPORT_MAX_ROWS", 1)
        records = [
            make_history_record(history_id="hist-0001", user_id="user-0001"),
            make_history_record(history_id="hist-0002", user_id="user-0001"),
        ]
        repository = TrackingPredictionHistoryRepository(records)
        service = ReportService(history_repository=repository)

        with pytest.raises(ReportExportLimitExceededError):
            asyncio.run(service.generate_report(user_id="user-0001", request=ReportRequest()))

        assert repository.list_by_user_calls == 0
        assert repository.count_by_user_calls == 1

    def test_uses_an_artificially_large_count_override_without_real_records(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A `count_by_user()` result alone is enough to trigger the limit, regardless of fixture size."""
        monkeypatch.setattr(settings, "REPORT_EXPORT_MAX_ROWS", 1000)
        repository = TrackingPredictionHistoryRepository(records=[], count_override=1450)
        service = ReportService(history_repository=repository)

        with pytest.raises(ReportExportLimitExceededError):
            asyncio.run(service.generate_report(user_id="user-0001", request=ReportRequest()))

    def test_succeeds_when_matching_history_is_within_the_configured_limit(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "REPORT_EXPORT_MAX_ROWS", 10)
        records = [
            make_history_record(history_id="hist-0001", user_id="user-0001"),
            make_history_record(history_id="hist-0002", user_id="user-0001"),
        ]
        repository = TrackingPredictionHistoryRepository(records)
        service = ReportService(history_repository=repository)

        report = asyncio.run(service.generate_report(user_id="user-0001", request=ReportRequest()))

        assert len(report.history) == 2

    def test_default_configured_limit_matches_the_previous_phase_65_bound(self) -> None:
        """The Phase 6.6 default (`1000`) preserves Phase 6.1-6.5 behavior for typical users."""
        assert settings.REPORT_EXPORT_MAX_ROWS == 1000
