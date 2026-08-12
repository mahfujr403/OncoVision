"""Prediction Report PDF Export exceptions (Phase 6.4, ADR-040).

Extend the application's centralized `OncoVisionError` so they are
automatically handled by the existing global exception handlers and
never leak internal details to API clients -- mirroring the same
convention already used by `app.reports.csv.exceptions`.

`PDFExportError` is the shared base for every exception raised by the
`app.reports.pdf` package, letting future callers catch the whole
hierarchy with a single `except PDFExportError:` when they don't need to
distinguish the specific failure.
"""

from fastapi import status

from app.core.exceptions import OncoVisionError


class PDFExportError(OncoVisionError):
    """Base exception for every error raised by the PDF Export package."""


class InvalidPDFExportRequestError(PDFExportError):
    """Raised when a PDF export request fails `PDFValidator` validation.

    For example, an unauthenticated caller (missing `user_id`) or an
    unsupported `PDFPageSize` value. Never raised for conditions
    Prediction History retrieval already enforces (ownership, filter
    range consistency) -- `PDFValidator` never duplicates that
    validation.
    """

    def __init__(
        self,
        message: str = "The PDF export request is invalid.",
    ) -> None:
        super().__init__(message=message, status_code=status.HTTP_400_BAD_REQUEST)


class PDFExportGenerationError(PDFExportError):
    """Raised when a PDF document cannot be rendered for a reason other than invalid input.

    Reserved for unexpected `PDFBuilder`/`PDFExportService` failures --
    for example, an underlying ReportLab rendering error -- so a broken
    render never propagates a raw internal exception to a caller.
    """

    def __init__(self, message: str = "The PDF report could not be generated.") -> None:
        super().__init__(message=message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PDFExportLimitExceededError(PDFExportError):
    """Raised when a PDF export exceeds a configured Phase 6.6 export safeguard (ADR-042).

    Raised by `PDFValidator.validate_export_limit()` -- before any
    history rows are retrieved by `PDFExportService` -- whenever
    `PredictionHistoryRepository.count_by_user()` reports more matching
    records than `Settings.REPORT_EXPORT_MAX_ROWS`, or by
    `PDFValidator.validate_export_size()` -- after `PDFBuilder` has
    already rendered the document -- whenever the resulting content
    exceeds `Settings.REPORT_EXPORT_MAX_SIZE_BYTES`. Replaces the silent,
    non-configurable truncation `PDF_EXPORT_HISTORY_LIMIT` performed
    through Phase 6.5 with an explicit, client-visible failure. Mirrors
    `app.reports.csv.exceptions.CSVExportLimitExceededError`.
    """

    def __init__(
        self,
        message: str = (
            "The PDF export exceeds the maximum number of records or "
            "document size supported for a single export."
        ),
    ) -> None:
        super().__init__(message=message, status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
