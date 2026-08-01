"""Final Prediction Result (Phase 4.7.4 - Final Prediction Builder, ADR-027).

`FinalPredictionResult` is the standardized, fully-serializable output of
the `FinalPredictionBuilder` (`app.ml.ensemble.final_prediction_builder`).

Per ADR-027, this phase only transforms the internal
`CalibratedEnsembleResult` (Phase 4.7.3 / ADR-026) into a reusable
production prediction object. It performs no calculations of its own --
every field is copied directly from the `CalibratedEnsembleResult` that
produced it. API response formatting is introduced by a later phase:
    - Phase 4.7.3: Confidence Calibration (completed)
    - Phase 4.7.4: Final Prediction Builder (this phase)
    - Phase 4.8: Response Builder
"""

from pydantic import BaseModel, ConfigDict, Field


class FinalPredictionResult(BaseModel):
    """Reusable production prediction object built from a `CalibratedEnsembleResult`.

    Constructed exactly once per prediction request by
    `FinalPredictionBuilder`. Every field is copied verbatim from the
    supplied `CalibratedEnsembleResult` -- this model never recalculates
    confidence, agreement, or vote scores.

    Remains independent from API response formatting; the Response
    Builder (Phase 4.8) is the only future component responsible for
    turning this object into an API response.
    """

    model_config = ConfigDict(frozen=True)

    predicted_class: str | None = Field(
        default=None,
        description=(
            "Final predicted class label, copied from "
            "CalibratedEnsembleResult.winning_class. None when calibration "
            "produced no winning class."
        ),
    )
    confidence: float = Field(
        default=0.0,
        description=(
            "Calibrated ensemble confidence percentage for `predicted_class`, "
            "copied from CalibratedEnsembleResult.calibrated_confidence."
        ),
    )
    agreement_ratio: float = Field(
        default=0.0,
        description=(
            "Proportion of successful models that agree with `predicted_class`, "
            "copied from CalibratedEnsembleResult.agreement_statistics.agreement_ratio."
        ),
    )
    successful_models: list[str] = Field(
        default_factory=list,
        description=(
            "Model IDs whose predictions participated in voting, copied from "
            "CalibratedEnsembleResult.agreement_statistics.successful_models."
        ),
    )
    failed_models: list[str] = Field(
        default_factory=list,
        description=(
            "Model IDs that were attempted but failed to produce a prediction, "
            "copied from CalibratedEnsembleResult.agreement_statistics.failed_models."
        ),
    )
    participating_models: int = Field(
        default=0,
        description=(
            "Total number of models attempted (successful and failed) for this "
            "request, copied from CalibratedEnsembleResult.agreement_statistics.total_models."
        ),
    )

    @classmethod
    def empty(cls) -> "FinalPredictionResult":
        """Return the zero-data `FinalPredictionResult`.

        Mirrors `CalibratedEnsembleResult.empty()` -- the correct output of
        `FinalPredictionBuilder.build` when supplied a `CalibratedEnsembleResult`
        with no winning class and no participating models.
        """
        return cls(
            predicted_class=None,
            confidence=0.0,
            agreement_ratio=0.0,
            successful_models=[],
            failed_models=[],
            participating_models=0,
        )
