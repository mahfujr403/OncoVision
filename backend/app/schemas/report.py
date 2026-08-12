"""Reporting request/response contracts (Phase 6.1, ADR-037).

These schemas represent the public, external shape of a report -- they
never expose `app.history.prediction_history.PredictionHistory` ORM
entities directly, mirroring the same internal/external separation
already established between `app.history` domain models and
`app.api.v1.history.responses`.

No API endpoint consumes these schemas in this phase (out of scope per
ADR-037); they are introduced now so the Reporting APIs phase (Phase
6.5), Analytics (Phase 6.2), CSV Export (Phase 6.3), and PDF Export
(Phase 6.4) can all depend on a single, stable contract without
redefining it.
"""

from pydantic import BaseModel, ConfigDict, Field

from app.history.filters import PredictionHistoryFilter
from app.reports.enums import ReportFormat, ReportStatus
from app.reports.report import Report


class ReportRequest(BaseModel):
    """Request contract for generating a report.

    `filters` reuses `PredictionHistoryFilter` (ADR-035) directly rather
    than redefining equivalent fields, so date-range and other filter
    validation continues to live in exactly one place.
    """

    model_config = ConfigDict(frozen=True)

    format: ReportFormat = Field(
        default=ReportFormat.JSON,
        description=(
            "Requested report output format. Only `JSON` (the "
            "dynamically-generated report object) is produced in this "
            "phase; `PDF` and `CSV` are reserved for later phases."
        ),
    )
    filters: PredictionHistoryFilter | None = Field(
        default=None,
        description=(
            "Optional filter criteria narrowing which prediction history "
            "records are included in the report. `None` applies no "
            "filtering."
        ),
    )


class ReportSummaryResponse(BaseModel):
    """Public response contract for a report's `ReportSummary`."""

    total_predictions: int = Field(
        description="Total number of prediction history records included in this report."
    )
    first_prediction_at: str | None = Field(
        description="ISO 8601 timestamp of the oldest included prediction, if any."
    )
    latest_prediction_at: str | None = Field(
        description="ISO 8601 timestamp of the newest included prediction, if any."
    )


class ReportStatisticsResponse(BaseModel):
    """Public response contract for a report's `ReportStatistics`."""

    successful_predictions: int = Field(
        description="Number of included predictions that fully succeeded."
    )
    partial_success_predictions: int = Field(
        description="Number of included predictions that partially succeeded."
    )
    failed_predictions: int = Field(description="Number of included predictions that failed.")
    average_confidence: float = Field(
        description="Mean final prediction confidence percentage across included predictions."
    )
    average_agreement_ratio: float = Field(
        description="Mean ensemble agreement ratio across included predictions."
    )
    most_predicted_class: str | None = Field(
        description="The most frequently predicted class label, if any."
    )
    prediction_distribution: dict[str, int] = Field(
        description="Count of included predictions per predicted class label."
    )


class ReportResult(BaseModel):
    """Public response contract for one generated report.

    Built exclusively via `ReportResult.from_domain()` from a `Report`
    domain object -- never constructed by hand -- so this schema can
    never drift out of sync with what `ReportBuilder` actually produced.
    """

    report_id: str = Field(description="Unique identifier for this report generation run.")
    generated_at: str = Field(description="ISO 8601 timestamp of when this report was generated.")
    status: ReportStatus = Field(description="Outcome of this report generation run.")
    summary: ReportSummaryResponse = Field(description="High-level summary of this report.")
    statistics: ReportStatisticsResponse = Field(
        description="Aggregated prediction metrics for this report."
    )
    total_records: int = Field(
        description="Number of prediction history records included in this report."
    )

    @classmethod
    def from_domain(cls, report: Report) -> "ReportResult":
        """Project an internal `Report` domain object onto its public response contract."""
        return cls(
            report_id=report.report_id,
            generated_at=report.generated_at,
            status=report.status,
            summary=ReportSummaryResponse(
                total_predictions=report.summary.total_predictions,
                first_prediction_at=report.summary.first_prediction_at,
                latest_prediction_at=report.summary.latest_prediction_at,
            ),
            statistics=ReportStatisticsResponse(
                successful_predictions=report.statistics.successful_predictions,
                partial_success_predictions=report.statistics.partial_success_predictions,
                failed_predictions=report.statistics.failed_predictions,
                average_confidence=report.statistics.average_confidence,
                average_agreement_ratio=report.statistics.average_agreement_ratio,
                most_predicted_class=report.statistics.most_predicted_class,
                prediction_distribution=report.statistics.prediction_distribution,
            ),
            total_records=len(report.history),
        )
