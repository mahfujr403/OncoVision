"""PDF Export Service (Phase 6.4, ADR-040).

`PDFExportService` is the single orchestration point for PDF Export,
mirroring the role `CSVExportService` already plays for CSV Export
(ADR-039), `ReportService` plays for Reporting (ADR-037), and
`PredictionAnalyticsService` plays for Prediction Analytics (ADR-038).

Per ADR-040, `PDFExportService` depends only on the existing
`PredictionHistoryRepository` contract, `PredictionAnalyticsService`,
`PDFValidator`, and `PDFBuilder` -- never on `AIRuntimeManager`,
`PredictionEngine`, or the database directly. No new repository is
introduced: PDF Export reuses `PredictionHistoryRepository` exactly as
it already exists, so the repository's own ownership enforcement
(ADR-032/ADR-034) is reused rather than duplicated here, and reuses
`PredictionAnalyticsService` exactly as it already exists (Phase 6.2) so
analytics figures are never recomputed independently.

The generation pipeline is:

    PDFValidator.validate()
        |
        v
    PredictionHistoryRepository.count_by_user()
        |
        v
    PDFValidator.validate_export_limit()
        |
        v
    PredictionHistoryRepository.list_by_user()
        |
        v
    PredictionAnalyticsService.compute_analytics_from_history()
        |
        v
    PDFBuilder.build()
        |
        v
    PDFValidator.validate_export_size()
        |
        v
    PDFExportResult

Phase 6.6 Reporting Hardening (ADR-042) makes two changes to this
pipeline versus Phase 6.5, mirroring
`app.reports.csv.csv_export_service.CSVExportService` exactly:

- The fixed, non-configurable `PDF_EXPORT_HISTORY_LIMIT` bound
  previously enforced by silently truncating `list_by_user()`'s results
  is replaced with a configurable `Settings.REPORT_EXPORT_MAX_ROWS`,
  checked against an up-front `count_by_user()` call before any history
  rows are retrieved -- a request whose matching history exceeds the
  limit is now rejected with an explicit `PDFExportLimitExceededError`
  (`413`) instead of being silently cut off. A second safety check,
  `validate_export_size()`, runs after `PDFBuilder` has rendered the
  document, guarding against `Settings.REPORT_EXPORT_MAX_SIZE_BYTES`
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
from app.reports.pdf.enums import PDFPageSize
from app.reports.pdf.exceptions import PDFExportGenerationError
from app.reports.pdf.pdf_builder import PDFBuilder
from app.reports.pdf.pdf_result import PDFExportResult
from app.reports.pdf.pdf_validator import PDFValidator
from app.services.prediction_analytics_service import PredictionAnalyticsService

logger = get_logger(__name__)

# Default, non-configurable fallback bound on the number of
# `PredictionHistory` records a single PDF export run will render, used
# only when no `Settings.REPORT_EXPORT_MAX_ROWS` value is otherwise
# available. `Settings.REPORT_EXPORT_MAX_ROWS` (Phase 6.6, ADR-042) is
# the authoritative, configurable value applied at request time.
PDF_EXPORT_HISTORY_LIMIT: int = 1000


class PDFExportService:
    """Orchestrates PDF export generation from a user's prediction history and analytics.

    Depends on a `PredictionHistoryRepository` implementation and a
    `PredictionAnalyticsService`, plus a `PDFValidator` and a
    `PDFBuilder` -- all supplied through dependency injection, matching
    the constructor-injection convention already used by
    `CSVExportService` and `ReportService`.
    """

    def __init__(
        self,
        history_repository: PredictionHistoryRepository,
        analytics_service: PredictionAnalyticsService | None = None,
        validator: PDFValidator | None = None,
        builder: PDFBuilder | None = None,
    ) -> None:
        self._history_repository = history_repository
        self._analytics_service = analytics_service or PredictionAnalyticsService(history_repository)
        self._validator = validator or PDFValidator()
        self._builder = builder or PDFBuilder()

    async def export_pdf(
        self,
        user_id: str,
        filters: PredictionHistoryFilter | None = None,
        page_size: PDFPageSize = PDFPageSize.A4,
    ) -> PDFExportResult:
        """Generate a `PDFExportResult` for `user_id` from their prediction history and analytics.

        Validates the request, checks the matching history collection
        against the configured export row limit, retrieves `user_id`'s
        prediction history through the existing
        `PredictionHistoryRepository` and their aggregated analytics
        from that same, already-retrieved collection (ownership enforced
        by the repository query itself, exactly as it already is for
        `CSVExportService.export_csv()`), and delegates rendering
        entirely to `PDFBuilder`. Performs no aggregation, filtering, or
        rendering of its own beyond that delegation.

        Args:
            user_id: Identifier of the authenticated user requesting the
                PDF export.
            filters: Optional `PredictionHistoryFilter` narrowing which
                prediction history records are included, applied
                identically to both the history and analytics retrieval
                so the report's Analytics Summary and Prediction History
                sections always describe the same underlying record set.
                `None` includes every record owned by `user_id`.
            page_size: The `PDFPageSize` to render with. Only
                `PDFPageSize.A4` is supported in this phase.

        Returns:
            An immutable `PDFExportResult` carrying the complete,
            rendered PDF document. `PDFExportResult.empty()`-derived
            content (via `PDFBuilder`) when `user_id` has no matching
            prediction history records.

        Raises:
            InvalidPDFExportRequestError: If `user_id` is missing/blank,
                or `page_size` is not a supported `PDFPageSize` value.
            PDFExportLimitExceededError: If the matching prediction
                history exceeds `Settings.REPORT_EXPORT_MAX_ROWS`, or the
                rendered document exceeds
                `Settings.REPORT_EXPORT_MAX_SIZE_BYTES` (Phase 6.6,
                ADR-042).
            PDFExportGenerationError: If `PDFBuilder.build()` raises an
                unexpected error while rendering the document (Phase
                6.6, ADR-042).
        """
        self._validator.validate(user_id=user_id, page_size=page_size)

        logger.info(
            "PDF export started: user_id=%s filtered=%s page_size=%s",
            user_id,
            filters is not None and not filters.is_empty,
            page_size.value,
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

        result = self._build_pdf_safely(
            user_id=user_id, history=history, analytics=analytics, page_size=page_size
        )

        self._validator.validate_export_size(
            user_id=user_id,
            content_size_bytes=len(result.content),
            max_size_bytes=settings.REPORT_EXPORT_MAX_SIZE_BYTES,
        )

        logger.info(
            "PDF export completed: user_id=%s export_id=%s record_count=%d",
            user_id,
            result.export_id,
            result.history_row_count,
        )

        return result

    def _build_pdf_safely(
        self,
        user_id: str,
        history: list[PredictionHistory],
        analytics: PredictionAnalyticsResult,
        page_size: PDFPageSize,
    ) -> PDFExportResult:
        """Delegate to `PDFBuilder.build()`, converting unexpected failures into `PDFExportGenerationError`.

        Introduced by Phase 6.6 Reporting Hardening (ADR-042). Mirrors
        `app.reports.csv.csv_export_service.CSVExportService._build_csv_safely()`:
        `PDFBuilder` -- including the underlying ReportLab rendering
        calls -- is the one builder in this subsystem with meaningfully
        higher failure surface than a pure in-memory transform, so this
        boundary ensures a render failure is logged with its full
        context here, at the PDF Export subsystem boundary, rather than
        surfacing only as a generic, unattributed `500` from
        `app.core.exceptions.unhandled_exception_handler`. The client
        response is unaffected either way: both paths return a `500`
        with no internal details exposed.
        """
        try:
            return self._builder.build(
                user_id=user_id, history=history, analytics=analytics, page_size=page_size
            )
        except Exception as exc:
            logger.error(
                "PDF export failed while rendering the document: user_id=%s record_count=%d",
                user_id,
                len(history),
                exc_info=exc,
            )
            raise PDFExportGenerationError() from exc

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
        "no duplicate database queries" hardening rule). Mirrors
        `CSVExportService._retrieve()`.
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
