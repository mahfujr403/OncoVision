"""Report Validator (Phase 6.1, ADR-037).

`ReportValidator` validates a report generation request before
`ReportService` performs any repository access. It intentionally
duplicates none of the validation Prediction History already performs:

- Filter date-range and confidence-range consistency is already enforced
  at construction time by `PredictionHistoryFilter` (ADR-035) -- a
  `ReportRequest.filters` value that exists at all has already passed
  that check.
- Ownership is already enforced by
  `PredictionHistoryRepository.list_by_user()` scoping every query to the
  supplied `user_id` (ADR-032/ADR-034) -- `ReportValidator` only checks
  that a `user_id` was actually supplied, never that it "owns" anything.

`ReportValidator` validates only what is genuinely this layer's own
responsibility: that a report request carries an authenticated user and
a supported `ReportFormat`.
"""

from app.core.logging import get_logger
from app.reports.enums import ReportFormat
from app.reports.exceptions import InvalidReportRequestError, ReportExportLimitExceededError
from app.schemas.report import ReportRequest

logger = get_logger(__name__)


class ReportValidator:
    """Validates `ReportRequest` instances before report generation proceeds.

    Stateless and side-effect free beyond logging, mirroring the
    convention already used by `app.core.upload.UploadValidator`.
    """

    def validate(self, user_id: str, request: ReportRequest) -> None:
        """Validate a report generation request.

        Args:
            user_id: Identifier of the authenticated user requesting the
                report.
            request: The `ReportRequest` to validate.

        Raises:
            InvalidReportRequestError: If `user_id` is missing/blank, or
                `request.format` is not a supported `ReportFormat` value.
        """
        if not user_id or not user_id.strip():
            logger.warning("Report request rejected: missing authenticated user.")
            raise InvalidReportRequestError(
                "Report generation requires an authenticated user."
            )

        if not isinstance(request.format, ReportFormat):
            logger.warning(
                "Report request rejected: unsupported format=%s", request.format
            )
            raise InvalidReportRequestError(
                "Report format must be a supported ReportFormat value."
            )

    def validate_export_limit(self, user_id: str, total_records: int, max_rows: int) -> None:
        """Reject report generation over a matching history collection that is too large.

        Introduced by Phase 6.6 Reporting Hardening (ADR-042).
        `ReportService` calls this after determining `total_records` via
        `PredictionHistoryRepository.count_by_user()` and before
        retrieving any history rows, so an over-limit request never
        issues the larger `list_by_user()` query at all. Mirrors
        `app.reports.analytics.analytics_validator.AnalyticsValidator.validate_export_limit()`.

        Args:
            user_id: Identifier of the authenticated user requesting the
                report. Used only for logging.
            total_records: The total number of matching history records,
                as reported by `PredictionHistoryRepository.count_by_user()`.
            max_rows: The configured maximum
                (`Settings.REPORT_EXPORT_MAX_ROWS`).

        Raises:
            ReportExportLimitExceededError: If `total_records` exceeds
                `max_rows`.
        """
        if total_records > max_rows:
            logger.warning(
                "Report request rejected: total_records=%d exceeds max_rows=%d user_id=%s",
                total_records,
                max_rows,
                user_id,
            )
            raise ReportExportLimitExceededError(
                f"The matching prediction history contains {total_records} records, "
                f"which exceeds the maximum of {max_rows} supported for a single report."
            )
