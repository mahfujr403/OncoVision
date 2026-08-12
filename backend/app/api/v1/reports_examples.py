"""OpenAPI/Swagger documentation examples for the Reporting API (Phase 6.6, ADR-042).

Plain dictionaries only -- no schema construction or validation happens
here. Each constant is wired into `app.api.v1.reports.router`'s
`responses={...}` mapping so Swagger renders a concrete example for the
new `413` response Phase 6.6 Reporting Hardening introduces, following
the same documentation-only-projection pattern already used by
`app.api.v1.predictions.examples`.

No new status codes or error-handling behavior are introduced by this
module itself; it documents exception shapes that already exist as of
Phase 6.6 (`app.reports.exceptions.ReportExportLimitExceededError`,
`app.reports.csv.exceptions.CSVExportLimitExceededError`,
`app.reports.pdf.exceptions.PDFExportLimitExceededError`,
`app.reports.analytics.exceptions.AnalyticsExportLimitExceededError`),
each handled by the existing centralized
`app.core.exceptions.oncovision_exception_handler`.
"""

from typing import Any, Final

#: Shared shape for every Phase 6.6 export-limit `413` response -- none of
#: `ReportExportLimitExceededError`, `CSVExportLimitExceededError`,
#: `PDFExportLimitExceededError`, or `AnalyticsExportLimitExceededError`
#: attach structured `errors` details (mirroring `INTERNAL_ERROR_EXAMPLE`'s
#: `errors: None` shape), so a single example illustrates all four -- only
#: the endpoint-specific `message` differs.
EXPORT_LIMIT_EXCEEDED_EXAMPLE: Final[dict[str, Any]] = {
    "success": False,
    "message": (
        "The matching prediction history contains 1450 records, which "
        "exceeds the maximum of 1000 supported for a single export."
    ),
    "data": None,
    "errors": None,
    "request_id": "6f7a8b9c-0d1e-4f2a-3b4c-5d6e7f809192",
    "timestamp": "2026-07-19T10:00:05Z",
}
