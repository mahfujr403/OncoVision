"""Prediction API response schemas (Phase 4.3 - ADR-012).

Defines the public response contract for `POST /api/v1/predictions`.

These schemas represent the EXTERNAL API only. Internal runtime objects
produced by the Prediction Engine (`app.ml.prediction.prediction_result`)
and the Adaptive Ensemble Engine (`app.ml.ensemble.response`) must never
be returned directly -- ADR-012. Where a public field's meaning exactly
matches an existing internal enum, that enum is reused (e.g.
`AgreementLevel`, `EnsembleStrategyType`) so the two layers cannot drift
out of sync; every other shape here is intentionally a simplified,
stable, external-facing projection of the richer internal result.

This module defines the CONTRACT only. Populating these schemas with real
inference output is introduced in later phases (see Backend Progress,
Phase 4.5 onward). Phase 4.3 wires them into the router only as
placeholder responses.
"""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.ml.ensemble.response import AgreementLevel, EnsembleStrategyType

__all__ = [
    "AgreementLevel",
    "EnsembleStrategyType",
    "PredictionStatus",
    "RuntimeHealthStatus",
    "PredictionErrorCode",
    "IndividualModelResultSchema",
    "PredictionRuntimeSchema",
    "PredictionResultSchema",
    "PredictionMetadataSchema",
    "PredictionResponseSchema",
    "PredictionErrorDetailSchema",
    "PredictionErrorResponseSchema",
]


class PredictionStatus(str, Enum):
    """Overall outcome of a prediction request.

    Mirrors the fault-tolerant ensemble decision strategy (ADR-009,
    Project Context section 19): three or two available models still
    produce a usable ensemble result (`SUCCESS`); exactly one available
    model produces a usable but non-ensembled result (`PARTIAL_SUCCESS`);
    zero available models is a hard `FAILED`. `PENDING` is reserved for
    responses -- such as this phase's placeholder -- where the pipeline
    has not executed yet.
    """

    PENDING = "pending"
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"


class RuntimeHealthStatus(str, Enum):
    """Qualitative AI Runtime health bucket surfaced to API clients.

    A simplified, external-facing projection of the richer internal
    runtime snapshot produced by `app.ml.runtime.health.RuntimeHealthService`.
    """

    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class PredictionErrorCode(str, Enum):
    """Categorizes a prediction error for API clients."""

    VALIDATION_ERROR = "validation_error"
    AUTHENTICATION_ERROR = "authentication_error"
    PREDICTION_ERROR = "prediction_error"
    INTERNAL_ERROR = "internal_error"


class IndividualModelResultSchema(BaseModel):
    """Simplified per-model prediction result exposed to API clients.

    A public projection of `app.ml.prediction.prediction_result.IndividualPrediction`;
    intentionally omits internal-only fields such as `model_id`, `model_version`,
    and the full raw-probability breakdown.
    """

    model_name: str = Field(description="Human-readable display name of the model.")
    prediction: str = Field(description="This model's own predicted class label.")
    confidence: float = Field(
        ge=0.0,
        le=100.0,
        description="This model's own top-class confidence, as a percentage (0-100).",
    )
    inference_time_ms: float = Field(
        description="Time spent running inference for this model, in milliseconds."
    )


class PredictionRuntimeSchema(BaseModel):
    """AI Runtime health snapshot and per-request execution statistics exposed to API clients.

    `loaded_models`, `failed_models`, `total_models`, and `runtime_status`
    are a simplified, external-facing projection of
    `app.ml.runtime.health.RuntimeHealthService.runtime_status` (Phase
    4.5.4). `loaded_model_count`, `successful_predictions`,
    `failed_predictions`, `participating_models`, `preprocessing_time_ms`,
    `total_inference_time_ms`, `total_execution_time_ms`, and
    `overall_processing_time_ms` are Phase 4.8.3's (ADR-029) additive
    projection of this specific request's already-computed
    `PredictionExecutionStats`
    (`app.ml.prediction.prediction_result.PredictionExecutionStats`) and
    the request's end-to-end wall-clock duration -- no value here is
    recalculated by this schema or by the router.
    """

    loaded_models: list[str] = Field(
        description="Display names of models currently loaded and available for inference."
    )
    failed_models: list[str] = Field(
        description="Display names of models that failed to load or execute."
    )
    total_models: int = Field(description="Total number of models registered in the manifest.")
    runtime_status: RuntimeHealthStatus = Field(
        description="Qualitative AI Runtime health bucket."
    )
    loaded_model_count: int | None = Field(
        default=None,
        description=(
            "Number of models currently in the READY state, copied from "
            "`RuntimeValidationResult.loaded_model_count` (ADR-015). Null "
            "when the RUNTIME pipeline stage did not complete."
        ),
    )
    successful_predictions: int | None = Field(
        default=None,
        description=(
            "Number of models that produced a successful prediction for "
            "this request, copied from `PredictionExecutionStats.successful_predictions` "
            "(ADR-029). Null when the PREDICTION_ENGINE stage did not complete."
        ),
    )
    failed_predictions: int | None = Field(
        default=None,
        description=(
            "Number of models that were attempted but failed to produce a "
            "prediction for this request, copied from "
            "`PredictionExecutionStats.failed_predictions` (ADR-029). Null "
            "when the PREDICTION_ENGINE stage did not complete."
        ),
    )
    participating_models: int | None = Field(
        default=None,
        description=(
            "Total number of models attempted (successful and failed) for "
            "this request, copied from "
            "`PredictionExecutionStats.total_models_attempted` (ADR-029). Null "
            "when the PREDICTION_ENGINE stage did not complete."
        ),
    )
    preprocessing_time_ms: float | None = Field(
        default=None,
        description=(
            "Time spent validating and preprocessing the uploaded image for "
            "this request, in milliseconds, copied from "
            "`PredictionExecutionStats.preprocessing_time_ms` (ADR-029). Null "
            "when the PREDICTION_ENGINE stage did not complete."
        ),
    )
    total_inference_time_ms: float | None = Field(
        default=None,
        description=(
            "Sum of every successfully executed model's inference time for "
            "this request, in milliseconds, copied from "
            "`PredictionExecutionStats.total_inference_time_ms` (ADR-029). Null "
            "when the PREDICTION_ENGINE stage did not complete."
        ),
    )
    total_execution_time_ms: float | None = Field(
        default=None,
        description=(
            "Total wall-clock time spent in the PREDICTION_ENGINE stage for "
            "this request, in milliseconds, copied from "
            "`PredictionExecutionStats.total_execution_time_ms` (ADR-029). Null "
            "when the PREDICTION_ENGINE stage did not complete."
        ),
    )
    overall_processing_time_ms: float | None = Field(
        default=None,
        description=(
            "Total end-to-end wall-clock time spent handling this request, "
            "in milliseconds. Mirrors `PredictionMetadataSchema.processing_time_ms` "
            "(ADR-029); reused rather than recomputed."
        ),
    )


class PredictionResultSchema(BaseModel):
    """Final ensemble (or single-model) prediction result exposed to API clients.

    A public projection of
    `app.ml.response.response_result.PredictionResponseResult` (ADR-028),
    built by `PredictionResponseBuilder` from the completed internal
    FINAL_PREDICTION step's `FinalPredictionResult` (ADR-027). Every
    field below is copied directly from `PredictionResponseResult` --
    this schema performs no additional calculation (Phase 4.8.2).
    """

    prediction: str = Field(description="Final predicted class label.")
    confidence: float = Field(
        ge=0.0,
        le=100.0,
        description="Final prediction confidence, as a percentage (0-100).",
    )
    agreement_ratio: float = Field(
        ge=0.0,
        le=1.0,
        description="Proportion of successful models that agree with the final label.",
    )
    successful_models: list[str] = Field(
        description="Model IDs whose predictions participated in the final prediction."
    )
    failed_models: list[str] = Field(
        description="Model IDs that were attempted but failed to produce a prediction."
    )
    participating_models: int = Field(
        description="Total number of models attempted (successful and failed) for this request."
    )


class PredictionMetadataSchema(BaseModel):
    """Request-level metadata attached to every prediction response."""

    api_version: str = Field(description="API version that served this request.")
    backend_version: str = Field(description="Deployed backend application version.")
    model_manifest_version: str | None = Field(
        default=None,
        description=(
            "Version identifier of the Model Manifest active at prediction time. "
            "Null until the AI Runtime Manager is wired in (Phase 4.5)."
        ),
    )
    processing_time_ms: float = Field(
        description="Total wall-clock time spent handling this request, in milliseconds."
    )


class PredictionResponseSchema(BaseModel):
    """Complete public response payload for a prediction request.

    Carried as the `data` field of the application's global `APIResponse`
    envelope (`app.schemas.response.APIResponse`) -- never returned
    standalone.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "prediction_id": "b1f0c6b2-5c1a-4e9e-9c3a-2f6a0e0f9a11",
                "status": "success",
                "message": "Prediction completed successfully.",
                "timestamp": "2026-07-19T10:00:00Z",
                "result": {
                    "prediction": "lung_adenocarcinoma",
                    "confidence": 96.42,
                    "agreement_ratio": 1.0,
                    "successful_models": ["mobilenetv2", "densenet121"],
                    "failed_models": [],
                    "participating_models": 2,
                },
                "individual_predictions": [
                    {
                        "model_name": "MobileNetV2",
                        "prediction": "lung_adenocarcinoma",
                        "confidence": 95.10,
                        "inference_time_ms": 42.3,
                    },
                    {
                        "model_name": "DenseNet121",
                        "prediction": "lung_adenocarcinoma",
                        "confidence": 97.05,
                        "inference_time_ms": 88.7,
                    },
                ],
                "runtime_statistics": {
                    "loaded_models": ["MobileNetV2", "DenseNet121"],
                    "failed_models": [],
                    "total_models": 3,
                    "runtime_status": "operational",
                    "loaded_model_count": 2,
                    "successful_predictions": 2,
                    "failed_predictions": 0,
                    "participating_models": 2,
                    "preprocessing_time_ms": 18.4,
                    "total_inference_time_ms": 131.0,
                    "total_execution_time_ms": 134.6,
                    "overall_processing_time_ms": 158.9,
                },
                "metadata": {
                    "api_version": "v1",
                    "backend_version": "1.0.0",
                    "model_manifest_version": "1.0.0",
                    "processing_time_ms": 131.4,
                },
            }
        }
    )

    prediction_id: str = Field(description="Unique identifier for this prediction request.")
    status: PredictionStatus = Field(description="Overall outcome of this prediction request.")
    message: str = Field(description="Human-readable summary of the outcome.")
    timestamp: str = Field(description="ISO 8601 timestamp of when this response was produced.")
    result: PredictionResultSchema | None = Field(
        default=None,
        description=(
            "Final prediction result, built from the Response Builder's "
            "`PredictionResponseResult` (ADR-028). Null when the RESPONSE "
            "pipeline stage did not complete for this request."
        ),
    )
    individual_predictions: list[IndividualModelResultSchema] | None = Field(
        default=None,
        description=(
            "Per-model prediction breakdown, present only when "
            "`include_individual_predictions` was requested. Null until "
            "Prediction Engine Integration (Phase 4.6)."
        ),
    )
    runtime_statistics: PredictionRuntimeSchema | None = Field(
        default=None,
        description=(
            "AI Runtime health snapshot, present only when "
            "`include_runtime_statistics` was requested. Null until "
            "Runtime Integration (Phase 4.5)."
        ),
    )
    metadata: PredictionMetadataSchema = Field(description="Request-level metadata.")


class PredictionErrorDetailSchema(BaseModel):
    """A single structured error detail.

    Shaped to remain compatible with the `errors` field already produced
    by the application's centralized exception handlers
    (`app.core.exceptions`), which emit `{"field": ..., "message": ...}`
    entries. `code` is an additional, optional categorization for
    prediction-domain errors.
    """

    code: PredictionErrorCode | None = Field(
        default=None, description="Categorization of this error, when applicable."
    )
    field: str | None = Field(
        default=None, description="Name of the offending request field, when applicable."
    )
    message: str = Field(description="Human-readable description of the error.")


class PredictionErrorResponseSchema(BaseModel):
    """Documentation-only shape of a failed prediction request.

    Errors are always ultimately serialized through the application's
    global `APIResponse` envelope via `app.utils.response.error_response`;
    this schema exists to give OpenAPI/Swagger a concrete, typed example
    of that envelope's shape for prediction-domain failures and is never
    constructed or returned directly by application code.
    """

    success: bool = Field(default=False, description="Always `false` for an error response.")
    message: str = Field(description="Human-readable summary of the failure.")
    errors: list[PredictionErrorDetailSchema] | None = Field(
        default=None, description="Structured error details, if any."
    )
    request_id: str = Field(description="Unique identifier for the failed request.")
    timestamp: str = Field(description="ISO 8601 timestamp of the error response.")
