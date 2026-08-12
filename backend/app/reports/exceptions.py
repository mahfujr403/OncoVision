"""Reporting exceptions (Phase 6.1, ADR-037).

Extend the application's centralized `OncoVisionError` so they are
automatically handled by the existing global exception handlers and
never leak internal details to API clients -- mirroring the same
convention already used by `app.history.exceptions`.

`ReportError` is the shared base for every exception raised by the
`app.reports` package, letting future callers catch the whole hierarchy
with a single `except ReportError:` when they don't need to distinguish
the specific failure.
"""

from fastapi import status

from app.core.exceptions import OncoVisionError


class ReportError(OncoVisionError):
    """Base exception for every error raised by the Reporting package."""


class InvalidReportRequestError(ReportError):
    """Raised when a `ReportRequest` fails `ReportValidator` validation.

    For example, an unauthenticated caller (missing `user_id`) or an
    unsupported `ReportFormat` value. Never raised for conditions
    Prediction History retrieval already enforces (ownership, filter
    range consistency) -- `ReportValidator` never duplicates that
    validation.
    """

    def __init__(
        self,
        message: str = "The report request is invalid.",
    ) -> None:
        super().__init__(message=message, status_code=status.HTTP_400_BAD_REQUEST)


class ReportGenerationError(ReportError):
    """Raised when a report cannot be assembled for a reason other than invalid input.

    Reserved for unexpected `ReportBuilder`/`ReportService` failures;
    `ReportBuilder` performs no I/O and no external calls, so this is not
    expected to be raised during normal Phase 6.1 operation.
    """

    def __init__(self, message: str = "The report could not be generated.") -> None:
        super().__init__(message=message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ReportExportLimitExceededError(ReportError):
    """Raised when a user's matching prediction history exceeds the configured export limit.

    Introduced by Phase 6.6 Reporting Hardening (ADR-042). Raised by
    `ReportValidator.validate_export_limit()` -- before any history rows
    are retrieved by `ReportService` -- whenever
    `PredictionHistoryRepository.count_by_user()` reports more matching
    records than `Settings.REPORT_EXPORT_MAX_ROWS`. Replaces the silent,
    non-configurable truncation `REPORT_HISTORY_LIMIT` performed through
    Phase 6.5 with an explicit, client-visible failure.
    """

    def __init__(
        self,
        message: str = (
            "The matching prediction history exceeds the maximum number of "
            "records supported for a single report."
        ),
    ) -> None:
        super().__init__(message=message, status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
