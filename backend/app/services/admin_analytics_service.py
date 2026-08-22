"""Admin Prediction Analytics Oversight Service (Phase 7.7, ADR-036 extension).

`AdminAnalyticsService` is a thin orchestration layer over the existing
`PredictionAnalyticsService` -- mirroring exactly how `AdminHistoryService`
(Phase 7.4) wraps `PredictionHistoryService` rather than introducing a
second analytics implementation. It exists only so the Admin Analytics
Router depends on an Admin-named service (matching the Router -> Service
-> Existing Service architecture ADR-036 already established) without
importing `PredictionAnalyticsService` directly into `app.api.v1.admin`.

Delegates directly to `PredictionAnalyticsService.compute_admin_analytics()`
-- no aggregation logic is duplicated here.
"""

from app.core.logging import get_logger
from app.history.filters import PredictionHistoryFilter
from app.reports.analytics.analytics_result import PredictionAnalyticsResult
from app.services.prediction_analytics_service import PredictionAnalyticsService

logger = get_logger(__name__)


class AdminAnalyticsService:
    """Orchestrates administrative prediction analytics oversight."""

    def __init__(self, analytics_service: PredictionAnalyticsService) -> None:
        self._analytics_service = analytics_service

    async def compute_analytics(
        self,
        user_id: str | None = None,
        filters: PredictionHistoryFilter | None = None,
    ) -> PredictionAnalyticsResult:
        """Return aggregated analytics across every user, or one user via `user_id`.

        Delegates entirely to
        `PredictionAnalyticsService.compute_admin_analytics()`.
        """
        return await self._analytics_service.compute_admin_analytics(
            user_id=user_id, filters=filters
        )
