"""Prediction Analytics exceptions (Phase 6.2, ADR-038).

Extend the application's centralized `OncoVisionError` so they are
automatically handled by the existing global exception handlers and
never leak internal details to API clients -- mirroring the same
convention already used by `app.reports.exceptions`.

`AnalyticsError` is the shared base for every exception raised by the
`app.reports.analytics` package, letting future callers catch the whole
hierarchy with a single `except AnalyticsError:` when they don't need to
distinguish the specific failure.
"""

from fastapi import status

from app.core.exceptions import OncoVisionError


class AnalyticsError(OncoVisionError):
    """Base exception for every error raised by the Prediction Analytics package."""


class InvalidAnalyticsRequestError(AnalyticsError):
    """Raised when an analytics request fails `AnalyticsValidator` validation.

    For example, an unauthenticated caller (missing `user_id`). Never
    raised for conditions Prediction History retrieval already enforces
    (ownership, filter range consistency) -- `AnalyticsValidator` never
    duplicates that validation.
    """

    def __init__(
        self,
        message: str = "The analytics request is invalid.",
    ) -> None:
        super().__init__(message=message, status_code=status.HTTP_400_BAD_REQUEST)


class AnalyticsGenerationError(AnalyticsError):
    """Raised when analytics cannot be assembled for a reason other than invalid input.

    Reserved for unexpected `AnalyticsBuilder`/`PredictionAnalyticsService`
    failures; `AnalyticsBuilder` performs no I/O and no external calls, so
    this is not expected to be raised during normal Phase 6.2 operation.
    """

    def __init__(self, message: str = "Prediction analytics could not be generated.") -> None:
        super().__init__(message=message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AnalyticsExportLimitExceededError(AnalyticsError):
    """Raised when a user's matching prediction history exceeds the configured analytics limit.

    Introduced by Phase 6.6 Reporting Hardening (ADR-042). Raised by
    `AnalyticsValidator.validate_export_limit()` -- before any history
    rows are retrieved by `PredictionAnalyticsService` -- whenever
    `PredictionHistoryRepository.count_by_user()` reports more matching
    records than `Settings.REPORT_EXPORT_MAX_ROWS`. Mirrors
    `app.reports.exceptions.ReportExportLimitExceededError`.
    """

    def __init__(
        self,
        message: str = (
            "The matching prediction history exceeds the maximum number of "
            "records supported for a single analytics computation."
        ),
    ) -> None:
        super().__init__(message=message, status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
