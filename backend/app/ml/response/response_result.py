"""Prediction Response Result (Phase 4.8.1 - Response Builder Architecture, ADR-028).

`PredictionResponseResult` is the standardized, fully-serializable output
of the `PredictionResponseBuilder`
(`app.ml.response.response_builder`).

Per ADR-028, this phase only introduces the Response Builder
architecture. Every field on `PredictionResponseResult` is copied
directly from the `FinalPredictionResult`
(`app.ml.ensemble.final_prediction_result`, ADR-027) that produced it --
no prediction values, confidence, or agreement statistics are
recalculated, and no runtime statistics are attached. This object
remains internal; wiring it into `PredictionService` and the public API
response contract is introduced by a later phase:
    - Phase 4.7.4: Final Prediction Builder (completed)
    - Phase 4.8.1: Response Builder Architecture (this phase)
    - Phase 4.8.2: PredictionService Response Integration
    - Phase 4.8.3: Response Metadata & Runtime Statistics
"""

from pydantic import BaseModel, ConfigDict, Field


class PredictionResponseResult(BaseModel):
    """Reusable response object built from a `FinalPredictionResult`.

    Constructed exactly once per prediction request by
    `PredictionResponseBuilder`. Every field is copied verbatim from the
    supplied `FinalPredictionResult` -- this model never recalculates
    prediction values, confidence, or agreement statistics, and never
    attaches runtime statistics.

    Remains independent from the public API response contract; wiring
    this object into `app.api.v1.predictions.responses.PredictionResponseSchema`
    is introduced by a later phase.
    """

    model_config = ConfigDict(frozen=True)

    predicted_class: str | None = Field(
        default=None,
        description=(
            "Final predicted class label, copied from "
            "FinalPredictionResult.predicted_class. None when no winning "
            "class was produced upstream."
        ),
    )
    confidence: float = Field(
        default=0.0,
        description=(
            "Final prediction confidence percentage, copied from "
            "FinalPredictionResult.confidence."
        ),
    )
    agreement_ratio: float = Field(
        default=0.0,
        description=(
            "Proportion of successful models that agree with "
            "`predicted_class`, copied from FinalPredictionResult.agreement_ratio."
        ),
    )
    successful_models: list[str] = Field(
        default_factory=list,
        description=(
            "Model IDs whose predictions participated in the final "
            "prediction, copied from FinalPredictionResult.successful_models."
        ),
    )
    failed_models: list[str] = Field(
        default_factory=list,
        description=(
            "Model IDs that were attempted but failed to produce a "
            "prediction, copied from FinalPredictionResult.failed_models."
        ),
    )
    participating_models: int = Field(
        default=0,
        description=(
            "Total number of models attempted (successful and failed) for "
            "this request, copied from FinalPredictionResult.participating_models."
        ),
    )

    @classmethod
    def empty(cls) -> "PredictionResponseResult":
        """Return the zero-data `PredictionResponseResult`.

        Mirrors `FinalPredictionResult.empty()` -- the correct output of
        `PredictionResponseBuilder.build()` when supplied a
        `FinalPredictionResult` with no predicted class and no
        participating models.
        """
        return cls(
            predicted_class=None,
            confidence=0.0,
            agreement_ratio=0.0,
            successful_models=[],
            failed_models=[],
            participating_models=0,
        )
