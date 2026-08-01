"""Prediction pipeline result (Phase 4.4 - ADR-013).

`PredictionResult` is the internal, service-layer object returned by
`PredictionService.predict()`. It is intentionally distinct from
`app.api.v1.predictions.responses.PredictionResponseSchema` -- the public
API contract (ADR-012) -- which the Prediction Router builds separately
from this object's fields. Keeping the two separate lets the service
layer carry richer internal diagnostics (such as per-stage pipeline
bookkeeping) without affecting the public contract, and keeps the
service layer from depending on API-layer schema modules (see
`app.services.prediction_context` for why that dependency direction is
avoided).

Phase 4.4 populates only pipeline-stage bookkeeping (`stages`); every
placeholder outcome field below stays `None` until the phase that wires
in the corresponding stage:
    - `preprocessing_result`: Phase 4.6.1 (Image Preprocessing Integration)
    - `runtime_statistics`, `runtime_validation`: Phase 4.5 (Runtime Integration)
    - `prediction_request`: Phase 4.6.2 (Prediction Request Builder)
    - `individual_model_results`: Phase 4.6.3 onward (Prediction Engine Integration)
    - `execution_result`: Phase 4.6.5 (Prediction Result Collection, ADR-022)
    - `ensemble_result`, `prediction`, `confidence`: Phase 4.7 (Ensemble Integration)
    - `final_prediction_result`: Phase 4.7.4.2 (Final Prediction Builder
      Integration, ADR-027) -- the internal `FinalPredictionResult`
      produced by chaining the Adaptive Weighted Voting Engine
      (ADR-025), Confidence Calibration Engine (ADR-026), and Final
      Prediction Builder (ADR-027). This is an internal diagnostics
      field only; it is never returned to API clients directly, and API
      response formatting from it remains the responsibility of the
      Response Builder (Phase 4.8).
    - `response_result`: Phase 4.8.2 (PredictionService Response
      Integration, ADR-028) -- the `PredictionResponseResult`
      (`app.ml.response.response_result.PredictionResponseResult`)
      produced by `PredictionResponseBuilder.build()` from
      `final_prediction_result`. Still an internal, service-layer value
      (not the public API contract itself); the Prediction Router
      projects it onto `PredictionResultSchema` for the public `result`
      field.
    - `execution_stats`: Phase 4.8.3 (Runtime Statistics Integration,
      ADR-029) -- the `PredictionExecutionStats`
      (`app.ml.prediction.prediction_result.PredictionExecutionStats`)
      already produced by the PREDICTION_ENGINE stage, carried through
      unchanged so the Prediction Router can project it onto the public
      `runtime_statistics` field without recomputing any timing or
      outcome counts. Null whenever the PREDICTION_ENGINE stage did not
      complete for this request.
    - `history_reference`: Phase 5 (Prediction History)
    - `report_reference`: Phase 6 (Reports)
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PipelineStageName(str, Enum):
    """Identifies a single stage of the prediction pipeline (ADR-013)."""

    UPLOAD_VALIDATION = "upload_validation"
    CONTEXT_CREATION = "context_creation"
    PREPROCESSING = "preprocessing"
    RUNTIME = "runtime"
    REQUEST_BUILDING = "request_building"
    PREDICTION_ENGINE = "prediction_engine"
    RESULT_COLLECTION = "result_collection"
    ENSEMBLE = "ensemble"
    RESPONSE = "response"
    HISTORY = "history"
    REPORT = "report"


class PipelineStageStatus(str, Enum):
    """Execution status of a single pipeline stage."""

    COMPLETED = "completed"
    SKIPPED = "skipped"


class PipelineStageRecord(BaseModel):
    """Records the outcome of a single pipeline stage for diagnostics."""

    model_config = ConfigDict(frozen=True)

    name: PipelineStageName = Field(description="The pipeline stage this record describes.")
    status: PipelineStageStatus = Field(description="Whether the stage executed or was skipped.")
    detail: str = Field(description="Human-readable explanation of the stage outcome.")


class PredictionResult(BaseModel):
    """Internal, service-layer outcome of a single prediction pipeline run.

    Returned by `PredictionService.predict()`. The Prediction Router maps
    this object's fields onto the public
    `app.api.v1.predictions.responses.PredictionResponseSchema`; it is
    never returned to API clients directly (ADR-012).
    """

    model_config = ConfigDict(frozen=True)

    request_id: str = Field(description="Unique identifier for this prediction request.")
    requested_at: str = Field(description="ISO 8601 timestamp of when this request was received.")
    message: str = Field(description="Human-readable summary of the current pipeline outcome.")
    stages: list[PipelineStageRecord] = Field(
        description="Ordered record of every pipeline stage and its outcome."
    )

    prediction: str | None = Field(
        default=None,
        description="Final predicted class label. Null until Ensemble Integration (Phase 4.7).",
    )
    confidence: float | None = Field(
        default=None,
        description=(
            "Final prediction confidence percentage. Null until Ensemble "
            "Integration (Phase 4.7)."
        ),
    )
    preprocessing_result: Any | None = Field(
        default=None,
        description=(
            "Centralized image preprocessing output "
            "(`app.ml.preprocessing.preprocessing_result.PreprocessingResult`, "
            "ADR-018). Null until Image Preprocessing Integration (Phase 4.6.1)."
        ),
    )
    prediction_request: Any | None = Field(
        default=None,
        description=(
            "Standardized Prediction Engine input "
            "(`app.ml.prediction.prediction_request.PredictionRequest`, "
            "ADR-019). Null until Prediction Request Builder Integration "
            "(Phase 4.6.2)."
        ),
    )
    individual_model_results: list[Any] | None = Field(
        default=None,
        description=(
            "Per-model prediction breakdown. Null until Prediction Engine "
            "Integration (Phase 4.6.3 onward)."
        ),
    )
    execution_result: Any | None = Field(
        default=None,
        description=(
            "Standardized, ensemble-ready collection of this request's "
            "individual model results "
            "(`app.ml.prediction.prediction_execution_result.PredictionExecutionResult`, "
            "ADR-022). Null until Prediction Result Collection Integration "
            "(Phase 4.6.5)."
        ),
    )
    ensemble_result: Any | None = Field(
        default=None,
        description="Raw Adaptive Ensemble Engine output. Null until Ensemble Integration (Phase 4.7).",
    )
    final_prediction_result: Any | None = Field(
        default=None,
        description=(
            "Internal final prediction outcome "
            "(`app.ml.ensemble.final_prediction_result.FinalPredictionResult`, "
            "ADR-027), produced by chaining Adaptive Weighted Voting "
            "(ADR-025), Confidence Calibration (ADR-026), and the Final "
            "Prediction Builder (ADR-027) from the completed ENSEMBLE stage "
            "output. Null until Final Prediction Builder Integration (Phase "
            "4.7.4.2). Internal diagnostics only -- API response formatting "
            "from this field is introduced by the future Response Builder "
            "(Phase 4.8)."
        ),
    )
    response_result: Any | None = Field(
        default=None,
        description=(
            "Standardized API response payload "
            "(`app.ml.response.response_result.PredictionResponseResult`, "
            "ADR-028), built from `final_prediction_result` by "
            "`PredictionResponseBuilder`. Null until Response Builder "
            "Integration (Phase 4.8.2)."
        ),
    )
    runtime_statistics: Any | None = Field(
        default=None,
        description="AI Runtime health snapshot. Null until Runtime Integration (Phase 4.5).",
    )
    execution_stats: Any | None = Field(
        default=None,
        description=(
            "Aggregate PREDICTION_ENGINE timing and outcome statistics "
            "(`app.ml.prediction.prediction_result.PredictionExecutionStats`), "
            "carried through unchanged from `PredictionEngineResult.execution_stats`. "
            "Null until Prediction Engine Integration (Phase 4.6.3 onward); "
            "consumed by the Prediction Router's runtime statistics projection "
            "(Phase 4.8.3, ADR-029) without any recalculation."
        ),
    )
    runtime_validation: Any | None = Field(
        default=None,
        description=(
            "AI Runtime readiness validation outcome (`RuntimeValidationResult`, "
            "ADR-015). Null until Runtime Integration (Phase 4.5)."
        ),
    )
    history_reference: str | None = Field(
        default=None,
        description="Identifier of the persisted history record. Null until Phase 5.",
    )
    report_reference: str | None = Field(
        default=None,
        description="Identifier of the generated report. Null until Phase 6.",
    )

    def is_stage_completed(self, name: PipelineStageName) -> bool:
        """Return whether the given pipeline stage completed (rather than was skipped)."""
        return any(
            stage.name == name and stage.status == PipelineStageStatus.COMPLETED
            for stage in self.stages
        )
