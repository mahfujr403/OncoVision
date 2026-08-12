"""Prediction Analytics Service (Phase 6.2, ADR-038).

`PredictionAnalyticsService` is the single orchestration point for
Prediction Analytics, mirroring the role `ReportService` already plays
for Reporting (ADR-037) and `PredictionHistoryService` plays for
Prediction History (ADR-032).

Per ADR-038, `PredictionAnalyticsService` depends only on the existing
`PredictionHistoryRepository` contract, `AnalyticsValidator`, and
`AnalyticsBuilder` -- never on `AIRuntimeManager`, `PredictionEngine`,
`PredictionService`, or the database directly. No new repository is
introduced: Analytics reuses `PredictionHistoryRepository` exactly as it
already exists, so the repository's own ownership enforcement
(ADR-032/ADR-034) is reused rather than duplicated here.

The computation pipeline is:

    AnalyticsValidator.validate()
        |
        v
    PredictionHistoryRepository.count_by_user()
        |
        v
    AnalyticsValidator.validate_export_limit()
        |
        v
    PredictionHistoryRepository.list_by_user()
        |
        v
    AnalyticsBuilder.build()
        |
        v
    PredictionAnalyticsResult

Phase 6.6 Reporting Hardening (ADR-042) replaces the fixed, non-configurable
`ANALYTICS_HISTORY_LIMIT` bound previously enforced by silently truncating
`list_by_user()`'s results with a configurable
`Settings.REPORT_EXPORT_MAX_ROWS`, checked against an up-front
`count_by_user()` call before any history rows are retrieved -- a request
whose matching history exceeds the limit is now rejected with an explicit
`AnalyticsExportLimitExceededError` (`413`) instead of being silently cut
off. Phase 6.6 also adds `compute_analytics_from_history()`, for callers
(`CSVExportService`, `PDFExportService`) that have already retrieved the
exact same `user_id`/`filters`-scoped history collection themselves and
would otherwise trigger a second, redundant `list_by_user()` query for the
same data.
"""

from app.core.config import settings
from app.core.logging import get_logger
from app.history.filters import PredictionHistoryFilter
from app.history.prediction_history import PredictionHistory
from app.repositories.prediction_history_repository import PredictionHistoryRepository
from app.reports.analytics.analytics_builder import AnalyticsBuilder
from app.reports.analytics.analytics_result import PredictionAnalyticsResult
from app.reports.analytics.analytics_validator import AnalyticsValidator
from app.reports.analytics.exceptions import AnalyticsGenerationError

logger = get_logger(__name__)

# Default, non-configurable fallback bound on the number of
# `PredictionHistory` records a single analytics computation will
# aggregate over, used only when no `Settings.REPORT_EXPORT_MAX_ROWS`
# value is otherwise available (e.g. legacy direct construction).
# `Settings.REPORT_EXPORT_MAX_ROWS` (Phase 6.6, ADR-042) is the
# authoritative, configurable value applied at request time.
ANALYTICS_HISTORY_LIMIT: int = 1000


class PredictionAnalyticsService:
    """Orchestrates analytics computation from a user's prediction history.

    Depends only on a `PredictionHistoryRepository` implementation, an
    `AnalyticsValidator`, and an `AnalyticsBuilder` -- all supplied
    through dependency injection, matching the constructor-injection
    convention already used by `ReportService` and
    `PredictionHistoryService`.
    """

    def __init__(
        self,
        history_repository: PredictionHistoryRepository,
        validator: AnalyticsValidator | None = None,
        builder: AnalyticsBuilder | None = None,
    ) -> None:
        self._history_repository = history_repository
        self._validator = validator or AnalyticsValidator()
        self._builder = builder or AnalyticsBuilder()

    async def compute_analytics(
        self,
        user_id: str,
        filters: PredictionHistoryFilter | None = None,
    ) -> PredictionAnalyticsResult:
        """Compute a `PredictionAnalyticsResult` for `user_id` from their prediction history.

        Validates `user_id`, retrieves `user_id`'s prediction history
        through the existing `PredictionHistoryRepository` (ownership
        enforced by that repository query itself, exactly as it already
        is for `ReportService.generate_report()`), and delegates
        aggregation entirely to `AnalyticsBuilder`. Performs no
        aggregation, filtering, or business logic of its own beyond that
        delegation.

        Args:
            user_id: Identifier of the authenticated user requesting the
                analytics computation.
            filters: Optional `PredictionHistoryFilter` narrowing which
                prediction history records are included. `None` (the
                default) includes every record owned by `user_id`.

        Returns:
            An immutable `PredictionAnalyticsResult`.
            `PredictionAnalyticsResult.empty()` (via `AnalyticsBuilder`)
            when `user_id` has no matching prediction history records.

        Raises:
            InvalidAnalyticsRequestError: If `user_id` is missing or blank.
            AnalyticsExportLimitExceededError: If the matching prediction
                history exceeds `Settings.REPORT_EXPORT_MAX_ROWS`
                (Phase 6.6, ADR-042).
            AnalyticsGenerationError: If `AnalyticsBuilder.build()` raises
                an unexpected error while aggregating analytics (Phase
                6.6, ADR-042).
        """
        self._validator.validate(user_id=user_id)

        logger.info(
            "Analytics computation started: user_id=%s filtered=%s",
            user_id,
            filters is not None and not filters.is_empty,
        )

        max_rows = settings.REPORT_EXPORT_MAX_ROWS
        total_records = await self._history_repository.count_by_user(
            user_id=user_id, filters=filters
        )
        self._validator.validate_export_limit(
            user_id=user_id, total_records=total_records, max_rows=max_rows
        )

        history: list[PredictionHistory] = await self._history_repository.list_by_user(
            user_id=user_id,
            limit=max_rows,
            offset=0,
            filters=filters,
        )

        result = self._build_analytics_safely(user_id=user_id, history=history)

        logger.info(
            "Analytics computation completed: user_id=%s analytics_id=%s total_predictions=%d",
            user_id,
            result.analytics_id,
            result.total_predictions,
        )

        return result

    async def compute_analytics_from_history(
        self,
        user_id: str,
        history: list[PredictionHistory],
    ) -> PredictionAnalyticsResult:
        """Compute a `PredictionAnalyticsResult` for `user_id` from an already-retrieved history collection.

        Introduced by Phase 6.6 Reporting Hardening (ADR-042). Skips the
        `PredictionHistoryRepository.count_by_user()` /
        `list_by_user()` calls entirely and delegates straight to
        `AnalyticsBuilder.build()`, for callers (`CSVExportService`,
        `PDFExportService`) that have already retrieved the exact same
        `user_id`/`filters`-scoped history collection themselves and
        would otherwise issue a second, redundant database query for the
        same data. Produces output identical to what `compute_analytics()`
        would produce given that same history collection, since both
        delegate to the same stateless `AnalyticsBuilder` -- only the
        retrieval path differs.

        Args:
            user_id: Identifier of the authenticated user requesting the
                analytics computation.
            history: An already-retrieved, `user_id`-scoped
                `PredictionHistory` collection (typically the result of a
                prior `list_by_user()` call the caller already made).

        Returns:
            An immutable `PredictionAnalyticsResult`.
            `PredictionAnalyticsResult.empty()` (via `AnalyticsBuilder`)
            when `history` is empty.

        Raises:
            InvalidAnalyticsRequestError: If `user_id` is missing or blank.
            AnalyticsGenerationError: If `AnalyticsBuilder.build()` raises
                an unexpected error while aggregating analytics (Phase
                6.6, ADR-042).
        """
        self._validator.validate(user_id=user_id)

        result = self._build_analytics_safely(user_id=user_id, history=history)

        logger.info(
            "Analytics computation completed (from pre-fetched history): user_id=%s "
            "analytics_id=%s total_predictions=%d",
            user_id,
            result.analytics_id,
            result.total_predictions,
        )

        return result

    def _build_analytics_safely(
        self, user_id: str, history: list[PredictionHistory]
    ) -> PredictionAnalyticsResult:
        """Delegate to `AnalyticsBuilder.build()`, converting unexpected failures into `AnalyticsGenerationError`.

        Introduced by Phase 6.6 Reporting Hardening (ADR-042). Mirrors
        `app.services.report_service.ReportService._build_report_safely()`:
        `AnalyticsBuilder` performs no I/O and is not expected to raise
        under normal operation, but this boundary ensures that if it
        ever does, the failure is logged with its full context here, at
        the Analytics subsystem boundary, rather than surfacing only as
        a generic, unattributed `500` from
        `app.core.exceptions.unhandled_exception_handler`. The client
        response is unaffected either way: both paths return a `500`
        with no internal details exposed.
        """
        try:
            return self._builder.build(user_id=user_id, history=history)
        except Exception as exc:
            logger.error(
                "Analytics computation failed while aggregating results: user_id=%s "
                "record_count=%d",
                user_id,
                len(history),
                exc_info=exc,
            )
            raise AnalyticsGenerationError() from exc
