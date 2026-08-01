"""Prediction History Summary (Phase 5.1, ADR-032).

`PredictionHistorySummary` is the immutable, ensemble-level projection
of a completed prediction stored inside a `PredictionHistory` record.
Every field is copied directly from the `PredictionResponseResult`
(`app.ml.response.response_result`, ADR-028) that the original request
already produced -- this module performs no confidence recalculation,
no agreement recalculation, and no ensemble logic of its own.

`PredictionHistoryModelEntry` is the equivalent per-model projection,
copied directly from `IndividualPrediction`
(`app.ml.prediction.prediction_result`, ADR-008).
"""

from pydantic import BaseModel, ConfigDict, Field


class PredictionHistoryModelEntry(BaseModel):
    """Immutable, simplified per-model prediction record for history storage.

    A history-owned projection of
    `app.ml.prediction.prediction_result.IndividualPrediction` --
    intentionally omits internal-only fields such as the full raw
    probability vector, mirroring the same simplification already applied
    by `app.api.v1.predictions.responses.IndividualModelResultSchema`.
    """

    model_config = ConfigDict(frozen=True)

    model_name: str = Field(description="Human-readable display name of the model.")
    prediction: str = Field(description="This model's own predicted class label.")
    confidence: float = Field(
        description="This model's own top-class confidence, as a percentage (0-100)."
    )
    inference_time_ms: float = Field(
        description="Time spent running inference for this model, in milliseconds."
    )


class PredictionHistorySummary(BaseModel):
    """Immutable ensemble-level summary of a completed prediction.

    Constructed exactly once per history record by
    `PredictionHistoryMapper`. Every field is copied verbatim from the
    supplied `PredictionResponseResult` -- this model never recalculates
    confidence, agreement, or vote outcomes.
    """

    model_config = ConfigDict(frozen=True)

    predicted_class: str | None = Field(
        default=None,
        description=(
            "Final predicted class label, copied from "
            "PredictionResponseResult.predicted_class. None when no winning "
            "class was produced."
        ),
    )
    confidence: float = Field(
        default=0.0,
        description=(
            "Final prediction confidence percentage, copied from "
            "PredictionResponseResult.confidence."
        ),
    )
    agreement_ratio: float = Field(
        default=0.0,
        description=(
            "Proportion of successful models that agree with "
            "`predicted_class`, copied from PredictionResponseResult.agreement_ratio."
        ),
    )
    successful_models: list[str] = Field(
        default_factory=list,
        description=(
            "Model IDs whose predictions participated in the final "
            "prediction, copied from PredictionResponseResult.successful_models."
        ),
    )
    failed_models: list[str] = Field(
        default_factory=list,
        description=(
            "Model IDs that were attempted but failed to produce a "
            "prediction, copied from PredictionResponseResult.failed_models."
        ),
    )
    participating_models: int = Field(
        default=0,
        description=(
            "Total number of models attempted (successful and failed), "
            "copied from PredictionResponseResult.participating_models."
        ),
    )
    individual_predictions: list[PredictionHistoryModelEntry] = Field(
        default_factory=list,
        description=(
            "Per-model prediction breakdown for this request, copied from "
            "`PredictionResult.individual_model_results` "
            "(`app.ml.prediction.prediction_result.IndividualPrediction`). "
            "Empty when no individual model results are available at "
            "mapping time."
        ),
    )

    @classmethod
    def empty(cls) -> "PredictionHistorySummary":
        """Return the zero-data `PredictionHistorySummary`.

        Mirrors `PredictionResponseResult.empty()` -- the correct summary
        for a history record whose prediction pipeline did not reach the
        RESPONSE stage.
        """
        return cls(
            predicted_class=None,
            confidence=0.0,
            agreement_ratio=0.0,
            successful_models=[],
            failed_models=[],
            participating_models=0,
            individual_predictions=[],
        )
