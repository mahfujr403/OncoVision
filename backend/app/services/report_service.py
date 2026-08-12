"""Report Service (Phase 6.1, ADR-037).

`ReportService` is the single orchestration point for Reporting,
mirroring the role `PredictionHistoryService` already plays for
Prediction History (ADR-032) and `PredictionService` plays for the
prediction pipeline (ADR-013).

Per ADR-037, `ReportService` depends only on the existing
`PredictionHistoryRepository` contract, `ReportValidator`, and
`ReportBuilder` -- never on `AIRuntimeManager`, `PredictionEngine`, or
the database directly. No new repository is introduced: Reporting reuses
`PredictionHistoryRepository` exactly as it already exists (Phase 5.2
onward), so a repository's own ownership enforcement (ADR-032/ADR-034)
is reused rather than duplicated here.

The generation pipeline is:

    ReportValidator.validate()
        |
        v
    PredictionHistoryRepository.count_by_user()
        |
        v
    ReportValidator.validate_export_limit()
        |
        v
    PredictionHistoryRepository.list_by_user()
        |
        v
    ReportBuilder.build()
        |
        v
    Report

Phase 6.6 Reporting Hardening (ADR-042) replaces the fixed,
non-configurable `REPORT_HISTORY_LIMIT` bound previously enforced by
silently truncating `list_by_user()`'s results with a configurable
`Settings.REPORT_EXPORT_MAX_ROWS`, checked against an up-front
`count_by_user()` call before any history rows are retrieved -- a
request whose matching history exceeds the limit is now rejected with
an explicit `ReportExportLimitExceededError` (`413`) instead of being
silently cut off.
"""

from app.core.config import settings
from app.core.logging import get_logger
from app.history.prediction_history import PredictionHistory
from app.repositories.prediction_history_repository import PredictionHistoryRepository
from app.reports.builder import ReportBuilder
from app.reports.exceptions import ReportGenerationError
from app.reports.report import Report
from app.reports.validator import ReportValidator
from app.schemas.report import ReportRequest

logger = get_logger(__name__)

# Default, non-configurable fallback bound on the number of
# `PredictionHistory` records a single report generation run will
# aggregate over, used only when no `Settings.REPORT_EXPORT_MAX_ROWS`
# value is otherwise available. `Settings.REPORT_EXPORT_MAX_ROWS`
# (Phase 6.6, ADR-042) is the authoritative, configurable value applied
# at request time.
REPORT_HISTORY_LIMIT: int = 1000


class ReportService:
    """Orchestrates report generation from a user's prediction history.

    Depends only on a `PredictionHistoryRepository` implementation, a
    `ReportValidator`, and a `ReportBuilder` -- all supplied through
    dependency injection, matching the constructor-injection convention
    already used by `PredictionHistoryService` and `PredictionService`.
    """

    def __init__(
        self,
        history_repository: PredictionHistoryRepository,
        validator: ReportValidator | None = None,
        builder: ReportBuilder | None = None,
    ) -> None:
        self._history_repository = history_repository
        self._validator = validator or ReportValidator()
        self._builder = builder or ReportBuilder()

    async def generate_report(self, user_id: str, request: ReportRequest) -> Report:
        """Generate a `Report` for `user_id` from their prediction history.

        Validates `request`, retrieves `user_id`'s prediction history
        through the existing `PredictionHistoryRepository` (ownership
        enforced by that repository query itself, exactly as it already
        is for `PredictionHistoryService.list_history()`), and delegates
        aggregation entirely to `ReportBuilder`. Performs no aggregation,
        filtering, or business logic of its own beyond that delegation.

        Args:
            user_id: Identifier of the authenticated user requesting the
                report.
            request: An already-constructed `ReportRequest` (format and
                optional `PredictionHistoryFilter`).

        Returns:
            An immutable `Report`. `Report.empty()` (via `ReportBuilder`)
            when `user_id` has no matching prediction history records.

        Raises:
            InvalidReportRequestError: If `request` fails
                `ReportValidator` validation.
            ReportExportLimitExceededError: If the matching prediction
                history exceeds `Settings.REPORT_EXPORT_MAX_ROWS`
                (Phase 6.6, ADR-042).
            ReportGenerationError: If `ReportBuilder.build()` raises an
                unexpected error while assembling the report (Phase 6.6,
                ADR-042). The underlying exception is always logged with
                its full traceback before being re-raised as this
                standardized, client-safe error.
        """
        self._validator.validate(user_id=user_id, request=request)

        logger.info(
            "Report generation started: user_id=%s format=%s filtered=%s",
            user_id,
            request.format.value,
            request.filters is not None and not request.filters.is_empty,
        )

        max_rows = settings.REPORT_EXPORT_MAX_ROWS
        total_records = await self._history_repository.count_by_user(
            user_id=user_id, filters=request.filters
        )
        self._validator.validate_export_limit(
            user_id=user_id, total_records=total_records, max_rows=max_rows
        )

        history: list[PredictionHistory] = await self._history_repository.list_by_user(
            user_id=user_id,
            limit=max_rows,
            offset=0,
            filters=request.filters,
        )

        report = self._build_report_safely(user_id=user_id, history=history)

        logger.info(
            "Report generation completed: user_id=%s report_id=%s status=%s record_count=%d",
            user_id,
            report.report_id,
            report.status.value,
            len(report.history),
        )

        return report

    def _build_report_safely(self, user_id: str, history: list[PredictionHistory]) -> Report:
        """Delegate to `ReportBuilder.build()`, converting unexpected failures into `ReportGenerationError`.

        Introduced by Phase 6.6 Reporting Hardening (ADR-042).
        `ReportBuilder` performs no I/O and is not expected to raise
        under normal operation, but this boundary ensures that if it
        ever does -- a programming error, a malformed history record,
        etc. -- the failure is logged with its full context here, at the
        Reporting subsystem boundary, rather than surfacing only as a
        generic, unattributed `500` from
        `app.core.exceptions.unhandled_exception_handler`. The client
        response is unaffected either way: both paths return a `500`
        with no internal details exposed.
        """
        try:
            return self._builder.build(user_id=user_id, history=history)
        except Exception as exc:
            logger.error(
                "Report generation failed while building the report: user_id=%s "
                "record_count=%d",
                user_id,
                len(history),
                exc_info=exc,
            )
            raise ReportGenerationError() from exc
