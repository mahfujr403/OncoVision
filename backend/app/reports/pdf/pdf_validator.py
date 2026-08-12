"""PDF Export Validator (Phase 6.4, ADR-040).

`PDFValidator` validates a PDF export request before `PDFExportService`
performs any repository or analytics access. It intentionally duplicates
none of the validation Prediction History and Prediction Analytics
already perform:

- Filter date-range and confidence-range consistency is already enforced
  at construction time by `PredictionHistoryFilter` (ADR-035) -- a
  filter value that exists at all has already passed that check.
- Ownership is already enforced by
  `PredictionHistoryRepository.list_by_user()` scoping every query to the
  supplied `user_id` (ADR-032/ADR-034) -- `PDFValidator` only checks that
  a `user_id` was actually supplied, never that it "owns" anything.

`PDFValidator` validates only what is genuinely this layer's own
responsibility: that an export request carries an authenticated user and
a supported `PDFPageSize`. An empty prediction history collection is a
valid, expected outcome rather than a validation failure -- `PDFBuilder`
renders a correct, complete PDF document for it, mirroring the same
"empty is not an error" convention already established by
`ReportBuilder`, `AnalyticsBuilder`, and `CSVExportBuilder`.
"""

from app.core.logging import get_logger
from app.history.prediction_history import PredictionHistory
from app.reports.pdf.enums import PDFPageSize
from app.reports.pdf.exceptions import InvalidPDFExportRequestError, PDFExportLimitExceededError

logger = get_logger(__name__)


class PDFValidator:
    """Validates PDF export requests before rendering proceeds.

    Stateless and side-effect free beyond logging, mirroring the
    convention already used by `app.reports.csv.csv_validator.CSVValidator`.
    """

    def validate(self, user_id: str, page_size: PDFPageSize = PDFPageSize.A4) -> None:
        """Validate a PDF export request.

        Args:
            user_id: Identifier of the authenticated user requesting the
                PDF export.
            page_size: Requested `PDFPageSize`. Only `PDFPageSize.A4` is
                supported in this phase.

        Raises:
            InvalidPDFExportRequestError: If `user_id` is missing or
                blank, or `page_size` is not a supported `PDFPageSize`
                value.
        """
        if not user_id or not user_id.strip():
            logger.warning("PDF export request rejected: missing authenticated user.")
            raise InvalidPDFExportRequestError(
                "PDF export requires an authenticated user."
            )

        if not isinstance(page_size, PDFPageSize) or page_size != PDFPageSize.A4:
            logger.warning("PDF export request rejected: unsupported page_size=%s", page_size)
            raise InvalidPDFExportRequestError(
                "Only A4 page size is supported for PDF export in this phase."
            )

    def note_if_empty(self, user_id: str, history: list[PredictionHistory]) -> None:
        """Log (without raising) when `history` is empty.

        An empty prediction history collection is a valid outcome --
        `PDFBuilder` still renders a correct, complete PDF document for
        it. This method exists purely for observability, matching the
        informational logging `CSVValidator.note_if_empty()` already
        performs.
        """
        if not history:
            logger.info("PDF export requested with an empty history collection: user_id=%s", user_id)

    def validate_export_limit(self, user_id: str, total_records: int, max_rows: int) -> None:
        """Reject a PDF export whose matching history collection is too large.

        Introduced by Phase 6.6 Reporting Hardening (ADR-042).
        `PDFExportService` calls this after determining `total_records`
        via `PredictionHistoryRepository.count_by_user()` and before
        retrieving any history rows, so an over-limit request never
        issues the larger `list_by_user()` query at all. Mirrors
        `app.reports.csv.csv_validator.CSVValidator.validate_export_limit()`.

        Args:
            user_id: Identifier of the authenticated user requesting the
                PDF export. Used only for logging.
            total_records: The total number of matching history records,
                as reported by `PredictionHistoryRepository.count_by_user()`.
            max_rows: The configured maximum
                (`Settings.REPORT_EXPORT_MAX_ROWS`).

        Raises:
            PDFExportLimitExceededError: If `total_records` exceeds `max_rows`.
        """
        if total_records > max_rows:
            logger.warning(
                "PDF export rejected: total_records=%d exceeds max_rows=%d user_id=%s",
                total_records,
                max_rows,
                user_id,
            )
            raise PDFExportLimitExceededError(
                f"The matching prediction history contains {total_records} records, "
                f"which exceeds the maximum of {max_rows} supported for a single PDF export."
            )

    def validate_export_size(self, user_id: str, content_size_bytes: int, max_size_bytes: int) -> None:
        """Reject an already-rendered PDF document that exceeds the configured size cap.

        Introduced by Phase 6.6 Reporting Hardening (ADR-042) as a
        last-line-of-defense safety net, checked by `PDFExportService`
        only after `PDFBuilder` has already rendered the document. Not
        expected to be reached under normal operation at the default
        `Settings.REPORT_EXPORT_MAX_ROWS`. Mirrors
        `app.reports.csv.csv_validator.CSVValidator.validate_export_size()`.

        Args:
            user_id: Identifier of the authenticated user requesting the
                PDF export. Used only for logging.
            content_size_bytes: The byte size of the already-rendered
                `PDFExportResult.content`.
            max_size_bytes: The configured maximum
                (`Settings.REPORT_EXPORT_MAX_SIZE_BYTES`).

        Raises:
            PDFExportLimitExceededError: If `content_size_bytes` exceeds
                `max_size_bytes`.
        """
        if content_size_bytes > max_size_bytes:
            logger.warning(
                "PDF export rejected: content_size_bytes=%d exceeds max_size_bytes=%d "
                "user_id=%s",
                content_size_bytes,
                max_size_bytes,
                user_id,
            )
            raise PDFExportLimitExceededError(
                "The generated PDF document exceeds the maximum supported export size."
            )
