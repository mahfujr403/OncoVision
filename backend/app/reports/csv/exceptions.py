"""Prediction History CSV Export exceptions (Phase 6.3, ADR-039).

Extend the application's centralized `OncoVisionError` so they are
automatically handled by the existing global exception handlers and
never leak internal details to API clients -- mirroring the same
convention already used by `app.reports.exceptions` and
`app.reports.analytics.exceptions`.

`CSVExportError` is the shared base for every exception raised by the
`app.reports.csv` package, letting future callers catch the whole
hierarchy with a single `except CSVExportError:` when they don't need to
distinguish the specific failure.
"""

from fastapi import status

from app.core.exceptions import OncoVisionError


class CSVExportError(OncoVisionError):
    """Base exception for every error raised by the CSV Export package."""


class InvalidCSVExportRequestError(CSVExportError):
    """Raised when a `CSVExportRequest` fails `CSVValidator` validation.

    For example, an unauthenticated caller (missing `user_id`). Never
    raised for conditions Prediction History retrieval already enforces
    (ownership, filter range consistency) -- `CSVValidator` never
    duplicates that validation.
    """

    def __init__(
        self,
        message: str = "The CSV export request is invalid.",
    ) -> None:
        super().__init__(message=message, status_code=status.HTTP_400_BAD_REQUEST)


class CSVExportGenerationError(CSVExportError):
    """Raised when a CSV document cannot be assembled for a reason other than invalid input.

    Reserved for unexpected `CSVExportBuilder`/`CSVExportService`
    failures; `CSVExportBuilder` performs no I/O and no external calls
    beyond in-memory string serialization, so this is not expected to be
    raised during normal Phase 6.3 operation.
    """

    def __init__(self, message: str = "The CSV export could not be generated.") -> None:
        super().__init__(message=message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CSVExportLimitExceededError(CSVExportError):
    """Raised when a CSV export exceeds a configured Phase 6.6 export safeguard (ADR-042).

    Raised by `CSVValidator.validate_export_limit()` -- before any
    history rows are retrieved by `CSVExportService` -- whenever
    `PredictionHistoryRepository.count_by_user()` reports more matching
    records than `Settings.REPORT_EXPORT_MAX_ROWS`, or by
    `CSVValidator.validate_export_size()` -- after `CSVExportBuilder` has
    already serialized the document -- whenever the resulting content
    exceeds `Settings.REPORT_EXPORT_MAX_SIZE_BYTES`. Replaces the silent,
    non-configurable truncation `CSV_EXPORT_HISTORY_LIMIT` performed
    through Phase 6.5 with an explicit, client-visible failure.
    """

    def __init__(
        self,
        message: str = (
            "The CSV export exceeds the maximum number of records or "
            "document size supported for a single export."
        ),
    ) -> None:
        super().__init__(message=message, status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
