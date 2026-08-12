"""CSV Export Service (Phase 6.3, ADR-039).

`CSVExportService` is the single orchestration point for CSV Export,
mirroring the role `ReportService` already plays for Reporting (ADR-037)
and `PredictionAnalyticsService` plays for Prediction Analytics
(ADR-038).

Per ADR-039, `CSVExportService` depends only on the existing
`PredictionHistoryRepository` contract, `PredictionAnalyticsService`,
`CSVValidator`, and `CSVExportBuilder` -- never on `AIRuntimeManager`,
`PredictionEngine`, or the database directly. No new repository is
introduced: CSV Export reuses `PredictionHistoryRepository` exactly as
it already exists, so the repository's own ownership enforcement
(ADR-032/ADR-034) is reused rather than duplicated here, and reuses
`PredictionAnalyticsService` exactly as it already exists (Phase 6.2) so
analytics figures are never recomputed independently.

The generation pipeline is:

    CSVValidator.validate()
        |
        v
    PredictionHistoryRepository.count_by_user()
        |
        v
    CSVValidator.validate_export_limit()
        |
        v
    PredictionHistoryRepository.list_by_user()
        |
        v
    PredictionAnalyticsService.compute_analytics_from_history()
        |
        v
    CSVExportBuilder.build()
        |
        v
    CSVValidator.validate_export_size()
        |
        v
    CSVExportResult

Phase 6.6 Reporting Hardening (ADR-042) makes two changes to this
pipeline versus Phase 6.5:

- The fixed, non-configurable `CSV_EXPORT_HISTORY_LIMIT` bound
  previously enforced by silently truncating `list_by_user()`'s results
  is replaced with a configurable `Settings.REPORT_EXPORT_MAX_ROWS`,
  checked against an up-front `count_by_user()` call before any history
  rows are retrieved -- a request whose matching history exceeds the
  limit is now rejected with an explicit `CSVExportLimitExceededError`
  (`413`) instead of being silently cut off. A second safety check,
  `validate_export_size()`, runs after `CSVExportBuilder` has serialized
  the document, guarding against `Settings.REPORT_EXPORT_MAX_SIZE_BYTES`
  even when the row count itself was within bounds.
- `_retrieve()` no longer calls `PredictionAnalyticsService.compute_analytics()`
  (which would issue its own, independent `list_by_user()` query for the
  exact same `user_id`/`filters` pair `_retrieve()` already queried
  itself) and instead calls
  `PredictionAnalyticsService.compute_analytics_from_history()` with the
  history collection already retrieved -- eliminating a duplicate
  database query per export with no change to the resulting analytics
  figures.
"""

from app.core.config import settings
from app.core.logging import get_logger
from app.history.filters import PredictionHistoryFilter
from app.history.prediction_history import PredictionHistory
from app.repositories.prediction_history_repository import PredictionHistoryRepository
from app.reports.analytics.analytics_result import PredictionAnalyticsResult
from app.reports.csv.csv_builder import CSVExportBuilder
from app.reports.csv.csv_result import CSVExportResult
from app.reports.csv.csv_validator import CSVValidator
from app.reports.csv.exceptions import CSVExportGenerationError
from app.services.prediction_analytics_service import PredictionAnalyticsService

logger = get_logger(__name__)

# Default, non-configurable fallback bound on the number of
# `PredictionHistory` records a single CSV export run will serialize,
# used only when no `Settings.REPORT_EXPORT_MAX_ROWS` value is otherwise
# available. `Settings.REPORT_EXPORT_MAX_ROWS` (Phase 6.6, ADR-042) is
# the authoritative, configurable value applied at request time.
CSV_EXPORT_HISTORY_LIMIT: int = 1000


class CSVExportService:
    """Orchestrates CSV export generation from a user's prediction history and analytics.

    Depends on a `PredictionHistoryRepository` implementation and a
    `PredictionAnalyticsService`, plus a `CSVValidator` and a
    `CSVExportBuilder` -- all supplied through dependency injection,
    matching the constructor-injection convention already used by
    `ReportService` and `PredictionAnalyticsService`.
    """

    def __init__(
        self,
        history_repository: PredictionHistoryRepository,
        analytics_service: PredictionAnalyticsService | None = None,
        validator: CSVValidator | None = None,
        builder: CSVExportBuilder | None = None,
    ) -> None:
        self._history_repository = history_repository
        self._analytics_service = analytics_service or PredictionAnalyticsService(history_repository)
        self._validator = validator or CSVValidator()
        self._builder = builder or CSVExportBuilder()

    async def export_csv(
        self,
        user_id: str,
        filters: PredictionHistoryFilter | None = None,
    ) -> CSVExportResult:
        """Generate a `CSVExportResult` for `user_id` from their prediction history and analytics.

        Validates `user_id`, checks the matching history collection
        against the configured export row limit, retrieves `user_id`'s
        prediction history through the existing
        `PredictionHistoryRepository` and their aggregated analytics
        from that same, already-retrieved collection (ownership enforced
        by the repository query itself, exactly as it already is for
        `ReportService.generate_report()`), and delegates serialization
        entirely to `CSVExportBuilder`. Performs no aggregation,
        filtering, or serialization of its own beyond that delegation.

        Args:
            user_id: Identifier of the authenticated user requesting the
                CSV export.
            filters: Optional `PredictionHistoryFilter` narrowing which
                prediction history records are included, applied
                identically to both the history and analytics retrieval
                so the two sections of the resulting CSV always describe
                the same underlying record set. `None` includes every
                record owned by `user_id`.

        Returns:
            An immutable `CSVExportResult` carrying the complete CSV
            document. `CSVExportResult.empty()`-derived content (via
            `CSVExportBuilder`) when `user_id` has no matching prediction
            history records.

        Raises:
            InvalidCSVExportRequestError: If `user_id` is missing or blank.
            CSVExportLimitExceededError: If the matching prediction
                history exceeds `Settings.REPORT_EXPORT_MAX_ROWS`, or the
                generated document exceeds
                `Settings.REPORT_EXPORT_MAX_SIZE_BYTES` (Phase 6.6,
                ADR-042).
            CSVExportGenerationError: If `CSVExportBuilder.build()`
                raises an unexpected error while serializing the
                document (Phase 6.6, ADR-042).
        """
        self._validator.validate(user_id=user_id)

        logger.info(
            "CSV export started: user_id=%s filtered=%s",
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

        history, analytics = await self._retrieve(
            user_id=user_id, filters=filters, max_rows=max_rows
        )

        self._validator.note_if_empty(user_id=user_id, history=history)

        result = self._build_csv_safely(user_id=user_id, history=history, analytics=analytics)

        self._validator.validate_export_size(
            user_id=user_id,
            content_size_bytes=len(result.content.encode("utf-8")),
            max_size_bytes=settings.REPORT_EXPORT_MAX_SIZE_BYTES,
        )

        logger.info(
            "CSV export completed: user_id=%s export_id=%s record_count=%d",
            user_id,
            result.export_id,
            result.history_row_count,
        )

        return result

    async def _retrieve(
        self,
        user_id: str,
        filters: PredictionHistoryFilter | None,
        max_rows: int,
    ) -> tuple[list[PredictionHistory], PredictionAnalyticsResult]:
        """Retrieve prediction history once and derive analytics from it, for `user_id`.

        Issues a single `list_by_user()` query and computes analytics via
        `PredictionAnalyticsService.compute_analytics_from_history()`
        against that same result, rather than a second, independent
        `compute_analytics()` call that would otherwise re-query
        `list_by_user()` for identical data (Phase 6.6, ADR-042's
        "no duplicate database queries" hardening rule).
        """
        history = await self._history_repository.list_by_user(
            user_id=user_id,
            limit=max_rows,
            offset=0,
            filters=filters,
        )
        analytics = await self._analytics_service.compute_analytics_from_history(
            user_id=user_id, history=history
        )
        return history, analytics

    def _build_csv_safely(
        self,
        user_id: str,
        history: list[PredictionHistory],
        analytics: PredictionAnalyticsResult,
    ) -> CSVExportResult:
        """Delegate to `CSVExportBuilder.build()`, converting unexpected failures into `CSVExportGenerationError`.

        Introduced by Phase 6.6 Reporting Hardening (ADR-042). Mirrors
        `app.services.report_service.ReportService._build_report_safely()`:
        `CSVExportBuilder` performs no I/O beyond in-memory string
        serialization and is not expected to raise under normal
        operation, but this boundary ensures that if it ever does, the
        failure is logged with its full context here, at the CSV Export
        subsystem boundary, rather than surfacing only as a generic,
        unattributed `500` from
        `app.core.exceptions.unhandled_exception_handler`. The client
        response is unaffected either way: both paths return a `500`
        with no internal details exposed.
        """
        try:
            return self._builder.build(user_id=user_id, history=history, analytics=analytics)
        except Exception as exc:
            logger.error(
                "CSV export failed while building the document: user_id=%s record_count=%d",
                user_id,
                len(history),
                exc_info=exc,
            )
            raise CSVExportGenerationError() from exc
