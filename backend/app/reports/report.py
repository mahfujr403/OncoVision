"""Report domain model (Phase 6.1, ADR-037).

`Report` is the immutable aggregate root produced by `ReportBuilder`: a
single generation's `ReportSummary`, `ReportStatistics`, and the
underlying `PredictionHistory` collection it was derived from, bundled
together for `ReportService` to return.

Per ADR-037, reports are generated dynamically and are never persisted --
`Report` has no corresponding database table or ORM model, and no field
on it is ever written back to Prediction History.
"""

from pydantic import BaseModel, ConfigDict, Field

from app.history.prediction_history import PredictionHistory
from app.reports.enums import ReportStatus
from app.reports.statistics import ReportStatistics
from app.reports.summary import ReportSummary


class Report(BaseModel):
    """Immutable, dynamically-generated report over a user's prediction history.

    Constructed exactly once per generation request by `ReportBuilder`.
    Never constructed, mutated, or recalculated by any other component.
    """

    model_config = ConfigDict(frozen=True)

    report_id: str = Field(description="Unique identifier for this report generation run.")
    user_id: str = Field(description="Unique identifier of the user this report was generated for.")
    generated_at: str = Field(description="ISO 8601 timestamp of when this report was generated.")
    status: ReportStatus = Field(description="Outcome of this report generation run.")
    summary: ReportSummary = Field(description="High-level summary of this report's history collection.")
    statistics: ReportStatistics = Field(
        description="Aggregated prediction metrics for this report's history collection."
    )
    history: list[PredictionHistory] = Field(
        default_factory=list,
        description=(
            "The full `PredictionHistory` collection this report was "
            "generated from, newest first."
        ),
    )

    @classmethod
    def empty(cls, report_id: str, user_id: str, generated_at: str) -> "Report":
        """Return a `Report` with `EMPTY` status and zero-data summary/statistics.

        The correct report for a user with no matching prediction history
        records.
        """
        return cls(
            report_id=report_id,
            user_id=user_id,
            generated_at=generated_at,
            status=ReportStatus.EMPTY,
            summary=ReportSummary.empty(),
            statistics=ReportStatistics.empty(),
            history=[],
        )
