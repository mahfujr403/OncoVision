"""Admin Prediction/History Oversight Service (Phase 7.4, ADR-036).

`AdminHistoryService` is a thin orchestration layer over the existing
`PredictionHistoryService` -- per ADR-036/the Phase 7.4 scope, this is
explicitly NOT a second Prediction History implementation. It exists only
so the Admin History Router depends on an Admin-named service (matching
the Router -> Service -> Repository/Existing Service architecture laid
out in ADR-036) without importing `PredictionHistoryService` directly
into `app.api.v1.admin`, keeping the same one-service-per-router-module
convention already used elsewhere (`ReportService`, `PredictionAnalyticsService`).

Every method here delegates directly to `PredictionHistoryService`'s own
Phase 7.4 admin methods (`list_history_admin()` / `get_history_admin()`)
-- no filtering, pagination, or lookup logic is duplicated. Prediction
History remains immutable and append-only: no method on this service (or
on `PredictionHistoryService`) ever modifies a record.
"""

from app.core.logging import get_logger
from app.history.filters import PredictionHistoryFilter
from app.history.pagination import PredictionHistoryPage, PredictionHistoryPageRequest
from app.history.prediction_history import PredictionHistory
from app.services.prediction_history_service import PredictionHistoryService

logger = get_logger(__name__)


class AdminHistoryService:
    """Orchestrates administrative prediction history oversight."""

    def __init__(self, history_service: PredictionHistoryService) -> None:
        self._history_service = history_service

    async def list_history(
        self,
        page_request: PredictionHistoryPageRequest,
        filters: PredictionHistoryFilter | None = None,
        user_id: str | None = None,
    ) -> PredictionHistoryPage:
        """Return one page of prediction history across every user (or one, via `user_id`).

        Delegates entirely to `PredictionHistoryService.list_history_admin()`.
        """
        return await self._history_service.list_history_admin(
            page_request=page_request, filters=filters, user_id=user_id
        )

    async def get_history(self, history_id: str) -> PredictionHistory | None:
        """Return a single prediction history record by ID, regardless of owner.

        Delegates entirely to `PredictionHistoryService.get_history_admin()`.
        """
        return await self._history_service.get_history_admin(history_id=history_id)
