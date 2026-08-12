"""Report Statistics domain model (Phase 6.1, ADR-037).

`ReportStatistics` is the immutable, aggregated-metrics projection of a
generated report's prediction history collection. Every field is derived
by `ReportBuilder` purely from the already-retrieved
`app.history.prediction_history.PredictionHistory` records and their
`PredictionHistorySummary` -- no confidence recalculation, no agreement
recalculation, and no ensemble logic of any kind occurs here (ADR-037).

Designed to remain reusable by future Analytics (Phase 6.2) without
requiring its own recalculation of these metrics.
"""

from pydantic import BaseModel, ConfigDict, Field


class ReportStatistics(BaseModel):
    """Immutable, aggregated prediction metrics for one report.

    Constructed exactly once per report by `ReportBuilder`.
    """

    model_config = ConfigDict(frozen=True)

    successful_predictions: int = Field(
        default=0,
        description="Number of history records with `PredictionHistoryStatus.SUCCESS`.",
    )
    partial_success_predictions: int = Field(
        default=0,
        description="Number of history records with `PredictionHistoryStatus.PARTIAL_SUCCESS`.",
    )
    failed_predictions: int = Field(
        default=0,
        description="Number of history records with `PredictionHistoryStatus.FAILED`.",
    )
    average_confidence: float = Field(
        default=0.0,
        description=(
            "Mean final prediction confidence percentage, averaged across "
            "every history record with a non-null predicted class."
        ),
    )
    average_agreement_ratio: float = Field(
        default=0.0,
        description=(
            "Mean ensemble agreement ratio, averaged across every history "
            "record with a non-null predicted class."
        ),
    )
    most_predicted_class: str | None = Field(
        default=None,
        description=(
            "The predicted class label appearing most often across this "
            "report's history records. None when no record has a "
            "predicted class."
        ),
    )
    prediction_distribution: dict[str, int] = Field(
        default_factory=dict,
        description=(
            "Count of history records per predicted class label. Excludes "
            "records with no predicted class."
        ),
    )

    @classmethod
    def empty(cls) -> "ReportStatistics":
        """Return the zero-data `ReportStatistics`.

        The correct statistics for a report whose prediction history
        collection was empty.
        """
        return cls(
            successful_predictions=0,
            partial_success_predictions=0,
            failed_predictions=0,
            average_confidence=0.0,
            average_agreement_ratio=0.0,
            most_predicted_class=None,
            prediction_distribution={},
        )
