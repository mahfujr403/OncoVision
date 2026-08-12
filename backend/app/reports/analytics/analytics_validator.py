"""Analytics Validator (Phase 6.2, ADR-038).

`AnalyticsValidator` validates an analytics computation request before
`PredictionAnalyticsService` performs any repository access. It
intentionally duplicates none of the validation Prediction History
already performs:

- Filter date-range and confidence-range consistency is already enforced
  at construction time by `PredictionHistoryFilter` (ADR-035) -- a
  `filters` value that exists at all has already passed that check.
- Ownership is already enforced by
  `PredictionHistoryRepository.list_by_user()` scoping every query to the
  supplied `user_id` (ADR-032/ADR-034) -- `AnalyticsValidator` only
  checks that a `user_id` was actually supplied, never that it "owns"
  anything.

`AnalyticsValidator` validates only what is genuinely this layer's own
responsibility: that an analytics request carries an authenticated user.
Mirrors `app.reports.validator.ReportValidator`.
"""

from app.core.logging import get_logger
from app.reports.analytics.exceptions import (
    AnalyticsExportLimitExceededError,
    InvalidAnalyticsRequestError,
)

logger = get_logger(__name__)


class AnalyticsValidator:
    """Validates analytics computation requests before aggregation proceeds.

    Stateless and side-effect free beyond logging, mirroring the
    convention already used by `app.reports.validator.ReportValidator`.
    """

    def validate(self, user_id: str) -> None:
        """Validate an analytics computation request.

        Args:
            user_id: Identifier of the authenticated user requesting the
                analytics computation.

        Raises:
            InvalidAnalyticsRequestError: If `user_id` is missing or blank.
        """
        if not user_id or not user_id.strip():
            logger.warning("Analytics request rejected: missing authenticated user.")
            raise InvalidAnalyticsRequestError(
                "Analytics computation requires an authenticated user."
            )

    def validate_export_limit(self, user_id: str, total_records: int, max_rows: int) -> None:
        """Reject analytics computation over a matching history collection that is too large.

        Introduced by Phase 6.6 Reporting Hardening (ADR-042).
        `PredictionAnalyticsService` calls this after determining
        `total_records` via `PredictionHistoryRepository.count_by_user()`
        and before retrieving any history rows, so an over-limit request
        never issues the larger `list_by_user()` query at all.

        Args:
            user_id: Identifier of the authenticated user requesting the
                analytics computation. Used only for logging.
            total_records: The total number of matching history records,
                as reported by `PredictionHistoryRepository.count_by_user()`.
            max_rows: The configured maximum
                (`Settings.REPORT_EXPORT_MAX_ROWS`).

        Raises:
            AnalyticsExportLimitExceededError: If `total_records` exceeds
                `max_rows`.
        """
        if total_records > max_rows:
            logger.warning(
                "Analytics request rejected: total_records=%d exceeds max_rows=%d "
                "user_id=%s",
                total_records,
                max_rows,
                user_id,
            )
            raise AnalyticsExportLimitExceededError(
                f"The matching prediction history contains {total_records} records, "
                f"which exceeds the maximum of {max_rows} supported for a single "
                "analytics computation."
            )
