"""Report Summary domain model (Phase 6.1, ADR-037).

`ReportSummary` is the immutable, high-level projection of a generated
report's prediction history collection. Every field is derived by
`ReportBuilder` purely from the already-retrieved
`app.history.prediction_history.PredictionHistory` records -- this module
performs no database access, no filtering, and no business logic of its
own.
"""

from pydantic import BaseModel, ConfigDict, Field


class ReportSummary(BaseModel):
    """Immutable, high-level summary of one report's prediction history collection.

    Constructed exactly once per report by `ReportBuilder`. Reusable as-is
    by future Analytics (Phase 6.2), CSV Export (Phase 6.3), and PDF
    Export (Phase 6.4) services.
    """

    model_config = ConfigDict(frozen=True)

    total_predictions: int = Field(
        default=0,
        description="Total number of prediction history records included in this report.",
    )
    first_prediction_at: str | None = Field(
        default=None,
        description=(
            "ISO 8601 timestamp of the oldest prediction history record "
            "included in this report. None when the report has no records."
        ),
    )
    latest_prediction_at: str | None = Field(
        default=None,
        description=(
            "ISO 8601 timestamp of the newest prediction history record "
            "included in this report. None when the report has no records."
        ),
    )

    @classmethod
    def empty(cls) -> "ReportSummary":
        """Return the zero-data `ReportSummary`.

        The correct summary for a report whose prediction history
        collection was empty.
        """
        return cls(total_predictions=0, first_prediction_at=None, latest_prediction_at=None)
