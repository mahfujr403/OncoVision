"""Shared in-memory `PredictionHistoryRepository` test double (Phase 6.6, ADR-042).

Extends the minimal in-memory stand-ins already duplicated across
`tests/reports/test_report_service.py`, `tests/reports/csv/test_csv_export_service.py`,
`tests/reports/pdf/test_pdf_export_service.py`, and
`tests/reports/analytics/test_analytics_service.py` with call-count
tracking (`list_by_user_calls`, `count_by_user_calls`) and an optional
`count_override`, so Phase 6.6 Reporting Hardening tests can assert on:

- Export-limit enforcement short-circuiting before `list_by_user()` is
  ever called (`count_override` lets a test simulate a history collection
  far larger than the in-memory fixture actually holds).
- The elimination of the CSV/PDF export duplicate-query regression
  (`list_by_user_calls` should be exactly `1` per export run).

Existing per-package test doubles are untouched; this module is
exclusively for Phase 6.6's own test files.
"""

from app.history.filters import PredictionHistoryFilter
from app.history.prediction_history import PredictionHistory
from app.repositories.prediction_history_repository import PredictionHistoryRepository


class TrackingPredictionHistoryRepository(PredictionHistoryRepository):
    """Minimal in-memory `PredictionHistoryRepository` with call-count tracking (test-only)."""

    def __init__(
        self,
        records: list[PredictionHistory] | None = None,
        count_override: int | None = None,
    ) -> None:
        self._records = list(records or [])
        self._count_override = count_override
        self.list_by_user_calls = 0
        self.count_by_user_calls = 0
        self.last_list_call: dict | None = None
        self.last_count_call: dict | None = None

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
        self.list_by_user_calls += 1
        self.last_list_call = {
            "user_id": user_id,
            "limit": limit,
            "offset": offset,
            "filters": filters,
        }
        matching = [record for record in self._records if record.user_id == user_id]
        return matching[offset : offset + limit]

    async def count_by_user(
        self,
        user_id: str,
        filters: PredictionHistoryFilter | None = None,
    ) -> int:
        self.count_by_user_calls += 1
        self.last_count_call = {"user_id": user_id, "filters": filters}
        if self._count_override is not None:
            return self._count_override
        return len([record for record in self._records if record.user_id == user_id])
