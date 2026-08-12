"""Reporting enumerations (Phase 6.1, ADR-037).

Mirrors the convention already established by
`app.history.enums.PredictionHistoryStatus`: each enum here is owned
independently by the `app.reports` package and never imports from the
API layer.
"""

from enum import Enum


class ReportFormat(str, Enum):
    """Output format requested for a generated report.

    Phase 6.1 produces only a dynamically-generated, in-memory `Report`
    domain object -- no file of any format is written to disk (ADR-037).
    This enum exists so `ReportRequest`/`ReportValidator` already carry a
    stable, typed contract for format selection, ready for CSV Export
    (Phase 6.3) and PDF Export (Phase 6.4) to extend without changing the
    shape of `ReportRequest` introduced in this phase. `JSON` is the only
    format actually exercised until those phases land.
    """

    JSON = "json"
    PDF = "pdf"
    CSV = "csv"


class ReportStatus(str, Enum):
    """Outcome of a single report generation run.

    Derived entirely by `ReportBuilder` from the `PredictionHistory`
    collection a report is built from -- never persisted, and never
    recalculated by any other component.
    """

    GENERATED = "generated"
    EMPTY = "empty"
