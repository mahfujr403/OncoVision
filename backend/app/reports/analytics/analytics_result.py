"""Prediction Analytics Result domain model (Phase 6.2, ADR-038).

`PredictionAnalyticsResult` is the immutable, aggregated-metrics
projection of a user's prediction history collection. Every field is
derived by `AnalyticsBuilder` purely from already-retrieved
`app.history.prediction_history.PredictionHistory` records -- no
confidence recalculation, no agreement recalculation, and no ensemble
logic of any kind occurs here (ADR-038).

Designed to remain reusable, as-is, by every future reporting consumer
(dashboards, CSV Export, PDF Export, Reporting APIs) without requiring
its own recalculation of these metrics.
"""

from pydantic import BaseModel, ConfigDict, Field


class PredictionAnalyticsResult(BaseModel):
    """Immutable, aggregated prediction statistics for one analytics computation.

    Constructed exactly once per computation by `AnalyticsBuilder`. Never
    constructed, mutated, or recalculated by any other component.
    """

    model_config = ConfigDict(frozen=True)

    analytics_id: str = Field(description="Unique identifier for this analytics computation run.")
    user_id: str = Field(description="Unique identifier of the user this analytics was computed for.")
    generated_at: str = Field(
        description="ISO 8601 timestamp of when this analytics computation was generated."
    )

    total_predictions: int = Field(
        default=0, description="Total number of prediction history records considered."
    )
    successful_predictions: int = Field(
        default=0,
        description=(
            "Number of history records with a non-null predicted class "
            "(`PredictionHistorySummary.predicted_class`)."
        ),
    )
    failed_predictions: int = Field(
        default=0,
        description=(
            "Number of history records with no predicted class -- "
            "`total_predictions - successful_predictions`."
        ),
    )
    success_rate: float = Field(
        default=0.0,
        description=(
            "Percentage (0-100) of `total_predictions` that were "
            "successful. `0.0` when `total_predictions` is zero."
        ),
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
            "The predicted class label appearing most often across the "
            "considered history records. None when no record has a "
            "predicted class."
        ),
    )
    class_distribution: dict[str, int] = Field(
        default_factory=dict,
        description=(
            "Count of history records per predicted class label. Excludes "
            "records with no predicted class."
        ),
    )
    confidence_distribution: dict[str, int] = Field(
        default_factory=dict,
        description=(
            "Count of history records per fixed final-confidence percentage "
            "bucket ('0-20', '20-40', '40-60', '60-80', '80-100'). Excludes "
            "records with no predicted class. Added in Phase 6.5 (ADR-041) "
            "to support the Reporting APIs' analytics endpoint; computed "
            "the same way `class_distribution` already is -- a pure count "
            "over already-computed `PredictionHistorySummary.confidence` "
            "values, with no recalculation of confidence itself."
        ),
    )
    first_prediction_date: str | None = Field(
        default=None,
        description=(
            "ISO 8601 timestamp of the oldest history record considered. "
            "None when there are no records."
        ),
    )
    latest_prediction_date: str | None = Field(
        default=None,
        description=(
            "ISO 8601 timestamp of the newest history record considered. "
            "None when there are no records."
        ),
    )
    predictions_today: int = Field(
        default=0,
        description="Number of history records created since the start of the current UTC day.",
    )
    predictions_this_week: int = Field(
        default=0,
        description=(
            "Number of history records created since the start of the "
            "current ISO week (Monday, UTC)."
        ),
    )
    predictions_this_month: int = Field(
        default=0,
        description="Number of history records created since the start of the current UTC month.",
    )

    @classmethod
    def empty(cls, analytics_id: str, user_id: str, generated_at: str) -> "PredictionAnalyticsResult":
        """Return the zero-data `PredictionAnalyticsResult`.

        The correct analytics result for a user with no matching
        prediction history records.
        """
        return cls(
            analytics_id=analytics_id,
            user_id=user_id,
            generated_at=generated_at,
            total_predictions=0,
            successful_predictions=0,
            failed_predictions=0,
            success_rate=0.0,
            average_confidence=0.0,
            average_agreement_ratio=0.0,
            most_predicted_class=None,
            class_distribution={},
            confidence_distribution={},
            first_prediction_date=None,
            latest_prediction_date=None,
            predictions_today=0,
            predictions_this_week=0,
            predictions_this_month=0,
        )
