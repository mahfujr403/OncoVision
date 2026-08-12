"""CSV Export Validator (Phase 6.3, ADR-039).

`CSVValidator` validates a CSV export request before `CSVExportService`
performs any repository or analytics access. It intentionally duplicates
none of the validation Prediction History and Prediction Analytics
already perform:

- Filter date-range and confidence-range consistency is already enforced
  at construction time by `PredictionHistoryFilter` (ADR-035) -- a
  `CSVExportRequest.filters` value that exists at all has already passed
  that check.
- Ownership is already enforced by
  `PredictionHistoryRepository.list_by_user()` scoping every query to the
  supplied `user_id` (ADR-032/ADR-034) -- `CSVValidator` only checks that
  a `user_id` was actually supplied, never that it "owns" anything.

`CSVValidator` validates only what is genuinely this layer's own
responsibility: that an export request carries an authenticated user.
An empty prediction history collection is a valid, expected outcome
rather than a validation failure -- `CSVExportBuilder` produces a
correct, header-only CSV document for it, mirroring the same
"empty is not an error" convention already established by
`ReportBuilder.build()` / `Report.empty()` and
`AnalyticsBuilder.build()` / `PredictionAnalyticsResult.empty()`.
"""

from app.core.logging import get_logger
from app.history.prediction_history import PredictionHistory
from app.reports.csv.exceptions import CSVExportLimitExceededError, InvalidCSVExportRequestError

logger = get_logger(__name__)


class CSVValidator:
    """Validates CSV export requests before serialization proceeds.

    Stateless and side-effect free beyond logging, mirroring the
    convention already used by `app.reports.validator.ReportValidator`
    and `app.reports.analytics.analytics_validator.AnalyticsValidator`.
    """

    def validate(self, user_id: str) -> None:
        """Validate a CSV export request.

        Args:
            user_id: Identifier of the authenticated user requesting the
                CSV export.

        Raises:
            InvalidCSVExportRequestError: If `user_id` is missing or blank.
        """
        if not user_id or not user_id.strip():
            logger.warning("CSV export request rejected: missing authenticated user.")
            raise InvalidCSVExportRequestError(
                "CSV export requires an authenticated user."
            )

    def note_if_empty(self, user_id: str, history: list[PredictionHistory]) -> None:
        """Log (without raising) when `history` is empty.

        An empty prediction history collection is a valid outcome --
        `CSVExportBuilder` still produces a correct, header-only CSV
        document for it. This method exists purely for observability,
        matching the informational logging `ReportBuilder`/
        `AnalyticsBuilder` already emit for their own empty-history case.
        """
        if not history:
            logger.info("CSV export requested with an empty history collection: user_id=%s", user_id)

    def validate_export_limit(self, user_id: str, total_records: int, max_rows: int) -> None:
        """Reject a CSV export whose matching history collection is too large.

        Introduced by Phase 6.6 Reporting Hardening (ADR-042).
        `CSVExportService` calls this after determining `total_records`
        via `PredictionHistoryRepository.count_by_user()` and before
        retrieving any history rows, so an over-limit request never
        issues the larger `list_by_user()` query at all.

        Args:
            user_id: Identifier of the authenticated user requesting the
                CSV export. Used only for logging.
            total_records: The total number of matching history records,
                as reported by `PredictionHistoryRepository.count_by_user()`.
            max_rows: The configured maximum
                (`Settings.REPORT_EXPORT_MAX_ROWS`).

        Raises:
            CSVExportLimitExceededError: If `total_records` exceeds `max_rows`.
        """
        if total_records > max_rows:
            logger.warning(
                "CSV export rejected: total_records=%d exceeds max_rows=%d user_id=%s",
                total_records,
                max_rows,
                user_id,
            )
            raise CSVExportLimitExceededError(
                f"The matching prediction history contains {total_records} records, "
                f"which exceeds the maximum of {max_rows} supported for a single CSV export."
            )

    def validate_export_size(self, user_id: str, content_size_bytes: int, max_size_bytes: int) -> None:
        """Reject an already-serialized CSV document that exceeds the configured size cap.

        Introduced by Phase 6.6 Reporting Hardening (ADR-042) as a
        last-line-of-defense safety net, checked by `CSVExportService`
        only after `CSVExportBuilder` has already serialized the
        document. Not expected to be reached under normal operation at
        the default `Settings.REPORT_EXPORT_MAX_ROWS`.

        Args:
            user_id: Identifier of the authenticated user requesting the
                CSV export. Used only for logging.
            content_size_bytes: The UTF-8 encoded byte size of the
                already-generated `CSVExportResult.content`.
            max_size_bytes: The configured maximum
                (`Settings.REPORT_EXPORT_MAX_SIZE_BYTES`).

        Raises:
            CSVExportLimitExceededError: If `content_size_bytes` exceeds
                `max_size_bytes`.
        """
        if content_size_bytes > max_size_bytes:
            logger.warning(
                "CSV export rejected: content_size_bytes=%d exceeds max_size_bytes=%d "
                "user_id=%s",
                content_size_bytes,
                max_size_bytes,
                user_id,
            )
            raise CSVExportLimitExceededError(
                "The generated CSV document exceeds the maximum supported export size."
            )
