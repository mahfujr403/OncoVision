"""Ensemble Result (Phase 4.7.1 - Adaptive Ensemble Integration, ADR-024).

`EnsembleResult` is the standardized, fully-serializable output of the
Phase 4.7.1 `EnsembleEngine` entry point
(`app.ml.ensemble.ensemble_engine.EnsembleEngine`).

Per ADR-024, this phase only validates the incoming `EnsembleRequest`,
separates accepted (successful) predictions from rejected (failed) ones,
and prepares them for future ensemble processing. `EnsembleResult`
carries NO final predicted label, NO confidence score, and NO agreement
metrics -- those are introduced by later phases:
    - Phase 4.7.2: Voting & Agreement Engine
    - Phase 4.7.3: Confidence Calibration
    - Phase 4.7.4: Final Prediction Builder
"""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.ml.prediction.prediction_result import FailedModelPrediction, IndividualPrediction


class EnsembleStatus(str, Enum):
    """Qualitative outcome of Phase 4.7.1 ensemble validation and preparation.

    Neither value represents a final prediction outcome -- both describe
    only whether this request's accepted predictions are ready to be
    handed to future voting stages (Phase 4.7.2 onward).
    """

    READY_FOR_VOTING = "ready_for_voting"
    """Every attempted model succeeded; nothing was rejected."""

    DEGRADED = "degraded"
    """At least one accepted prediction exists, but one or more models
    were rejected (failed); voting can still proceed using only the
    accepted predictions (ADR-005/ADR-009)."""


class ValidationSummary(BaseModel):
    """Records the outcome of Phase 4.7.1 `EnsembleRequest` validation.

    Always describes a request that passed validation: `EnsembleEngine`
    raises rather than returning an `EnsembleResult` when validation
    fails (see `app.ml.ensemble.exceptions`), so every `ValidationSummary`
    reaching a caller has every check satisfied.
    """

    model_config = ConfigDict(frozen=True)

    execution_result_present: bool = Field(
        description="Whether a `PredictionExecutionResult` was present on the request."
    )
    has_successful_prediction: bool = Field(
        description="Whether at least one model produced a successful prediction."
    )
    runtime_metadata_present: bool = Field(
        description="Whether AI Runtime metadata was present on the request."
    )
    execution_statistics_present: bool = Field(
        description="Whether execution statistics were present on the request."
    )
    validation_message: str = Field(
        description="Human-readable summary of the validation outcome."
    )


class EnsembleResult(BaseModel):
    """Standardized output of the Phase 4.7.1 Adaptive Ensemble Integration layer.

    Constructed exactly once per prediction request by `EnsembleEngine`.
    Represents predictions validated and prepared for ensemble
    processing -- never a final prediction, confidence score, or
    agreement outcome.
    """

    model_config = ConfigDict(frozen=True)

    request_id: str = Field(description="Unique identifier for this prediction request.")
    accepted_predictions: list[IndividualPrediction] = Field(
        description=(
            "Individual predictions from every model that executed "
            "successfully, unchanged from the Prediction Engine (ADR-008), "
            "prepared for future voting (Phase 4.7.2 onward)."
        )
    )
    rejected_predictions: list[FailedModelPrediction] = Field(
        description=(
            "Models that were attempted but failed to produce a prediction, "
            "unchanged from the Prediction Engine. Reused directly rather "
            "than redefined, since a rejected prediction and a failed "
            "prediction are the same fact viewed from the Ensemble layer."
        )
    )
    successful_models: list[str] = Field(
        description="Model IDs whose predictions were accepted, in execution order."
    )
    failed_models: list[str] = Field(
        description="Model IDs whose predictions were rejected, in execution order."
    )
    ensemble_status: EnsembleStatus = Field(
        description=(
            "Qualitative readiness outcome of this request's ensemble "
            "preparation. Never a final prediction outcome."
        )
    )
    validation_summary: ValidationSummary = Field(
        description="Outcome of the validation checks performed before preparation."
    )
