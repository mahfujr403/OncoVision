"""Prediction endpoints.

Routers only receive requests and delegate to services; no business logic
lives here. Phase 4.1 wired up the endpoint shape and JWT protection.
Phase 4.2 connected centralized upload validation (ADR-011) via the
Prediction Service. Phase 4.3 introduced the strongly typed public
request/response contract (ADR-012, `schemas.py` / `responses.py`). Phase
4.4 introduced the Prediction Service orchestration skeleton (ADR-013):
the router converts the validated request options into a service-layer
`PredictionOptions` and maps the returned `PredictionResult` onto the
public response contract. Phase 4.5.4 connects the RUNTIME stage: when
`include_runtime_statistics` is requested, the router projects the
`PredictionResult`'s runtime metadata onto `PredictionRuntimeSchema`
(`_build_runtime_statistics`). Phase 4.6.4 connects the PREDICTION_ENGINE
stage (ADR-021): when `include_individual_predictions` is requested, the
router projects the `PredictionResult`'s sequential multi-model inference
output onto `IndividualModelResultSchema` (`_build_individual_predictions`),
and `status` reflects `PARTIAL_SUCCESS` -- one or more executed models,
non-ensembled (Project Context, Section 19) -- once that stage has
completed. Phase 4.8.2 connects the RESPONSE stage (ADR-028): the router
projects the `PredictionResult`'s `response_result`
(`app.ml.response.response_result.PredictionResponseResult`, built by
`PredictionResponseBuilder`) onto `PredictionResultSchema`
(`_build_result`), so `result` is populated once the internal
FINAL_PREDICTION step and RESPONSE stage have both completed. Phase
4.8.3 connects the Runtime Statistics Integration stage (ADR-029):
`_build_runtime_statistics` additionally projects the PREDICTION_ENGINE
stage's already-computed `PredictionExecutionStats` and this request's
already-measured end-to-end wall-clock duration onto
`PredictionRuntimeSchema`, so `runtime_statistics` carries per-request
execution metrics (successful/failed prediction counts, participating
models, preprocessing/inference/execution timings) alongside the
existing AI Runtime health snapshot -- no value is recalculated here.

Phase 4.9 (ADR-030) is documentation-only: it completes the OpenAPI/Swagger
description of the already-implemented endpoint above -- `response_model`
for a fully typed Swagger schema, a complete `responses={...}` mapping
covering every status code this endpoint (or the shared HTTP/validation
middleware it runs behind) can produce, and named examples for upload
constraints (supported formats, maximum size) and request-field
validation. No request handling, validation, prediction, runtime, or
response-building code is modified by this phase.
"""

import time
from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile, status

from app.api.v1.predictions.constants import SUPPORTED_EXTENSIONS, SUPPORTED_MIME_TYPES
from app.api.v1.predictions.examples import (
    AUTHENTICATION_ERROR_EXAMPLE,
    FILE_TOO_LARGE_EXAMPLE,
    INTERNAL_ERROR_EXAMPLE,
    PREDICTION_UNAVAILABLE_EXAMPLE,
    REQUEST_FIELD_VALIDATION_ERROR_EXAMPLE,
    SUCCESS_RESPONSE_EXAMPLE,
    VALIDATION_ERROR_EXAMPLE,
)
from app.api.v1.predictions.responses import (
    IndividualModelResultSchema,
    PredictionMetadataSchema,
    PredictionResponseSchema,
    PredictionResultSchema,
    PredictionRuntimeSchema,
    PredictionStatus,
    RuntimeHealthStatus,
)
from app.api.v1.predictions.schemas import PredictionRequestSchema
from app.constants.app import API_V1_PREFIX, BYTES_IN_MEGABYTE, TAG_PREDICTIONS
from app.core.config import settings
from app.core.logging import get_logger
from app.dependencies.auth import get_current_active_user
from app.dependencies.services import get_prediction_history_service, get_prediction_service
from app.ml.prediction.prediction_result import IndividualPrediction, PredictionExecutionStats
from app.ml.response.response_result import PredictionResponseResult
from app.models.user import User
from app.schemas.response import APIResponse
from app.services.prediction_context import PredictionOptions
from app.services.prediction_history_service import PredictionHistoryService
from app.services.prediction_service import PredictionService
from app.services.runtime_metadata import RuntimeMetadata
from app.services.runtime_validator import RuntimeValidationResult
from app.utils.response import success_response

logger = get_logger(__name__)

router = APIRouter(prefix="/predictions", tags=[TAG_PREDICTIONS])

# Derived from the shared API prefix constant so the two never drift apart.
_API_VERSION = API_V1_PREFIX.rsplit("/", maxsplit=1)[-1]


def _build_runtime_statistics(
    request_id: str,
    runtime_metadata: RuntimeMetadata | None,
    runtime_validation: RuntimeValidationResult | None,
    execution_stats: PredictionExecutionStats | None,
    overall_processing_time_ms: float | None,
) -> PredictionRuntimeSchema | None:
    """Project internal runtime metadata and execution stats onto the public contract.

    `RuntimeMetadata` and `RuntimeValidationResult` (service layer,
    ADR-014/015/016) are never returned to API clients directly (ADR-012);
    this is the router-owned translation into `PredictionRuntimeSchema`.
    Returns `None` when the RUNTIME pipeline stage was skipped (Phase 4.4
    behavior, still reachable when the service is constructed without its
    runtime collaborators).

    Phase 4.8.3 (ADR-029) additionally projects `execution_stats`
    (`PredictionExecutionStats`, already produced by the PREDICTION_ENGINE
    stage) and `overall_processing_time_ms` (the request's already-measured
    end-to-end wall-clock duration) onto the same schema. Neither value is
    recalculated here -- this stage performs no timing calculations,
    preprocessing, or inference of its own. `execution_stats` is `None`
    whenever the PREDICTION_ENGINE stage did not complete, in which case
    the corresponding fields are simply left `None`.
    """
    if runtime_metadata is None or runtime_validation is None:
        return None

    logger.info("Runtime statistics aggregation started: request_id=%s", request_id)

    if runtime_validation.loaded_model_count == 0:
        runtime_status = RuntimeHealthStatus.UNAVAILABLE
    elif runtime_validation.failed_model_count > 0:
        runtime_status = RuntimeHealthStatus.DEGRADED
    else:
        runtime_status = RuntimeHealthStatus.OPERATIONAL

    known_model_ids = {
        model.model_id
        for model in (
            *runtime_metadata.loaded_models,
            *runtime_metadata.failed_models,
            *runtime_metadata.lazy_models,
        )
    }

    runtime_statistics = PredictionRuntimeSchema(
        loaded_models=[model.display_name for model in runtime_metadata.loaded_models],
        failed_models=[model.display_name for model in runtime_metadata.failed_models],
        total_models=len(known_model_ids),
        runtime_status=runtime_status,
        loaded_model_count=runtime_validation.loaded_model_count,
        successful_predictions=(
            execution_stats.successful_predictions if execution_stats is not None else None
        ),
        failed_predictions=(
            execution_stats.failed_predictions if execution_stats is not None else None
        ),
        participating_models=(
            execution_stats.total_models_attempted if execution_stats is not None else None
        ),
        preprocessing_time_ms=(
            execution_stats.preprocessing_time_ms if execution_stats is not None else None
        ),
        total_inference_time_ms=(
            execution_stats.total_inference_time_ms if execution_stats is not None else None
        ),
        total_execution_time_ms=(
            execution_stats.total_execution_time_ms if execution_stats is not None else None
        ),
        overall_processing_time_ms=overall_processing_time_ms,
    )

    logger.info(
        "Runtime statistics generated: request_id=%s runtime_status=%s loaded_model_count=%d "
        "successful_predictions=%s failed_predictions=%s participating_models=%s",
        request_id,
        runtime_statistics.runtime_status.value,
        runtime_statistics.loaded_model_count,
        runtime_statistics.successful_predictions,
        runtime_statistics.failed_predictions,
        runtime_statistics.participating_models,
    )

    return runtime_statistics


def _build_individual_predictions(
    individual_model_results: list[IndividualPrediction] | None,
) -> list[IndividualModelResultSchema] | None:
    """Project internal per-model predictions onto the public contract.

    `IndividualPrediction` (ML layer, ADR-008) is never returned to API
    clients directly (ADR-012); this is the router-owned translation into
    `IndividualModelResultSchema`. Returns `None` when the
    PREDICTION_ENGINE pipeline stage was skipped (Phase 4.4 behavior,
    still reachable when the service is constructed without its
    prediction-engine collaborator).
    """
    if not individual_model_results:
        return None

    return [
        IndividualModelResultSchema(
            model_name=prediction.model_name,
            prediction=prediction.predicted_label,
            confidence=prediction.confidence.confidence_percentage,
            inference_time_ms=prediction.inference_time_ms,
        )
        for prediction in individual_model_results
    ]


def _build_result(
    response_result: PredictionResponseResult | None,
) -> PredictionResultSchema | None:
    """Project the internal Response Builder output onto the public contract.

    `PredictionResponseResult` (ADR-028) is never returned to API clients
    directly (ADR-012); this is the router-owned translation into
    `PredictionResultSchema`. Every field is copied directly -- no
    calculation is performed here, consistent with `PredictionResponseBuilder`
    itself (ADR-028). Returns `None` when the RESPONSE pipeline stage was
    skipped (Phase 4.4 behavior, still reachable when the service is
    constructed without its response-builder collaborator) or produced no
    winning class.
    """
    if response_result is None or response_result.predicted_class is None:
        return None

    return PredictionResultSchema(
        prediction=response_result.predicted_class,
        confidence=response_result.confidence,
        agreement_ratio=response_result.agreement_ratio,
        successful_models=list(response_result.successful_models),
        failed_models=list(response_result.failed_models),
        participating_models=response_result.participating_models,
    )


_MAX_UPLOAD_SIZE_MB = settings.MAX_UPLOAD_SIZE // BYTES_IN_MEGABYTE
_SUPPORTED_FORMATS_LIST = ", ".join(sorted(SUPPORTED_MIME_TYPES))
_SUPPORTED_EXTENSIONS_LIST = ", ".join(f".{ext}" for ext in sorted(SUPPORTED_EXTENSIONS))


@router.post(
    "",
    status_code=status.HTTP_200_OK,
    summary="Submit an image for prediction",
    description=(
        "Accepts a single histopathology image via `multipart/form-data`, "
        "along with optional prediction control flags submitted as sibling "
        "form fields on the same request, and hands the image off to the "
        "Prediction Service, which runs it through centralized upload "
        "validation (ADR-011), validates AI Runtime readiness (ADR-015), "
        "and executes sequential multi-model inference through the "
        "Prediction Engine (ADR-021).\n\n"
        f"**Supported image formats:** {_SUPPORTED_FORMATS_LIST} "
        f"(extensions: {_SUPPORTED_EXTENSIONS_LIST}).\n\n"
        f"**Maximum upload size:** {_MAX_UPLOAD_SIZE_MB} MB.\n\n"
        "**Request options** (`PredictionRequestSchema`, sent as multipart "
        "form fields): `confidence_threshold` (0.0-1.0, reliability "
        "flagging only, never alters inference), "
        "`include_individual_predictions` (attach the per-model prediction "
        "breakdown), `include_runtime_statistics` (attach the AI Runtime "
        "health snapshot and per-request execution metrics), "
        "`save_history` and `generate_report` (accepted for API contract "
        "stability, not yet acted on -- Phase 5 / Phase 6).\n\n"
        "The response follows the Phase 4.3 public prediction contract "
        "(ADR-012). `result` carries the final prediction produced by the "
        "Adaptive Ensemble Engine, Final Prediction Builder, and Response "
        "Builder (ADR-028), and is `null` only when the RESPONSE pipeline "
        "stage did not complete for this request. `individual_predictions` "
        "carries the real per-model inference results (every currently "
        "loaded production model, executed sequentially) when "
        "`include_individual_predictions` is requested. `runtime_statistics` "
        "carries the AI Runtime health snapshot plus this request's "
        "execution metrics (ADR-029) when `include_runtime_statistics` is "
        "requested. `metadata` is always present and describes the API/"
        "backend version, active Model Manifest version, and end-to-end "
        "processing time for this request."
    ),
    response_model=APIResponse[PredictionResponseSchema],
    responses={
        200: {
            "description": "The uploaded image passed centralized validation.",
            "content": {"application/json": {"example": SUCCESS_RESPONSE_EXAMPLE}},
        },
        400: {
            "description": (
                "The uploaded file failed centralized upload validation "
                "(ADR-011): missing file, unsupported type/extension, empty "
                "file, oversized file, or an unreadable/corrupted image."
            ),
            "content": {
                "application/json": {
                    "examples": {
                        "unsupported_file_type": {
                            "summary": "Unsupported file type or extension",
                            "value": VALIDATION_ERROR_EXAMPLE,
                        },
                        "file_too_large": {
                            "summary": f"File exceeds the {_MAX_UPLOAD_SIZE_MB} MB limit",
                            "value": FILE_TOO_LARGE_EXAMPLE,
                        },
                    }
                }
            },
        },
        401: {
            "description": "Missing or invalid authentication credentials.",
            "content": {"application/json": {"example": AUTHENTICATION_ERROR_EXAMPLE}},
        },
        404: {
            "description": (
                "No route matches the request path. Not raised by this "
                "endpoint's business logic -- the standard framework-level "
                "response for an unknown URL under the versioned API "
                "surface, returned through the same global response "
                "envelope as every other error (`app.core.exceptions`)."
            ),
        },
        413: {
            "description": (
                "Reserved for stricter, size-specific HTTP semantics in a "
                "future phase. Today, an oversized upload is rejected by "
                f"centralized Upload Validation with `400` (see the "
                "`file_too_large` example above), not `413`."
            ),
        },
        415: {
            "description": (
                "Reserved for stricter, media-type-specific HTTP semantics "
                "in a future phase. Today, an unsupported file type or "
                "extension is rejected by centralized Upload Validation "
                "with `400` (see the `unsupported_file_type` example "
                "above), not `415`."
            ),
        },
        422: {
            "description": (
                "One or more request fields failed schema validation "
                "(e.g. `confidence_threshold` outside the 0.0-1.0 range)."
            ),
            "content": {
                "application/json": {"example": REQUEST_FIELD_VALIDATION_ERROR_EXAMPLE}
            },
        },
        429: {
            "description": (
                "Reserved for future rate-limiting middleware (Backend "
                "Progress, Phase 9 - Deployment Optimization). Not "
                "currently enforced by this endpoint."
            ),
        },
        500: {
            "description": "An unexpected internal server error occurred.",
            "content": {"application/json": {"example": INTERNAL_ERROR_EXAMPLE}},
        },
        503: {
            "description": (
                "The AI Runtime is not initialized, or no production models are "
                "currently loaded and ready to serve predictions (ADR-015). "
                "Prediction Engine inference and Adaptive Ensemble Engine "
                "unavailability outcomes are still introduced in later phases "
                "(Phase 4.6-4.7)."
            ),
            "content": {"application/json": {"example": PREDICTION_UNAVAILABLE_EXAMPLE}},
        },
    },
)
async def create_prediction(
    current_user: Annotated[User, Depends(get_current_active_user)],
    prediction_service: Annotated[PredictionService, Depends(get_prediction_service)],
    history_service: Annotated[PredictionHistoryService, Depends(get_prediction_history_service)],
    image: Annotated[UploadFile, File(description="Histopathology image to classify.")],
    request_options: Annotated[PredictionRequestSchema, Depends(PredictionRequestSchema.as_form)],
):
    """Accept an uploaded image and delegate it to the Prediction Service.

    The Prediction Service validates the upload through the centralized
    `UploadValidator` (ADR-011), builds a `PredictionContext`, and walks
    the full orchestration skeleton defined by ADR-013 -- including real
    image preprocessing (ADR-018), AI Runtime validation (ADR-015), and,
    as of Phase 4.6.4, real sequential multi-model inference through the
    Prediction Engine (ADR-021). `request_options` is converted into a
    service-layer `PredictionOptions` here; `include_individual_predictions`
    now governs whether the per-model results are projected onto the
    response, and `include_runtime_statistics` governs the runtime
    snapshot. `save_history` now governs whether this request's outcome
    is persisted to Prediction History (Phase 5.2, ADR-033) -- the
    request-scoped `history_service` resolved above is passed straight
    through to `PredictionService.predict()`, which performs the actual
    persistence after the RESPONSE stage completes. `confidence_threshold`
    and `generate_report` remain unused until later phases. Report
    generation is not yet performed.
    """
    started_at = time.perf_counter()
    options = PredictionOptions.from_request(request_options)
    prediction_result = await prediction_service.predict(
        image=image,
        current_user=current_user,
        options=options,
        history_service=history_service,
    )
    processing_time_ms = round((time.perf_counter() - started_at) * 1000, 2)

    runtime_metadata: RuntimeMetadata | None = prediction_result.runtime_statistics
    runtime_validation: RuntimeValidationResult | None = prediction_result.runtime_validation
    execution_stats: PredictionExecutionStats | None = prediction_result.execution_stats

    runtime_statistics = (
        _build_runtime_statistics(
            request_id=prediction_result.request_id,
            runtime_metadata=runtime_metadata,
            runtime_validation=runtime_validation,
            execution_stats=execution_stats,
            overall_processing_time_ms=processing_time_ms,
        )
        if options.include_runtime_statistics
        else None
    )

    individual_model_results: list[IndividualPrediction] | None = (
        prediction_result.individual_model_results
    )
    individual_predictions = (
        _build_individual_predictions(individual_model_results)
        if options.include_individual_predictions
        else None
    )

    # Phase 4.6.4 (ADR-021): one or more successfully executed models
    # with no ensemble result yet is a PARTIAL_SUCCESS (Project Context,
    # Section 19). PENDING remains the outcome whenever the
    # PREDICTION_ENGINE stage itself was skipped (e.g. the service was
    # constructed without its prediction-engine collaborator).
    response_status = (
        PredictionStatus.PARTIAL_SUCCESS
        if individual_model_results
        else PredictionStatus.PENDING
    )

    response_data = PredictionResponseSchema(
        prediction_id=prediction_result.request_id,
        status=response_status,
        message=prediction_result.message,
        timestamp=prediction_result.requested_at,
        result=_build_result(prediction_result.response_result),
        individual_predictions=individual_predictions,
        runtime_statistics=runtime_statistics,
        metadata=PredictionMetadataSchema(
            api_version=_API_VERSION,
            backend_version=settings.APP_VERSION,
            model_manifest_version=(
                runtime_metadata.manifest_version if runtime_metadata is not None else None
            ),
            processing_time_ms=processing_time_ms,
        ),
    )

    if runtime_statistics is not None:
        logger.info(
            "Runtime statistics attached to response: request_id=%s",
            prediction_result.request_id,
        )

    return success_response(
        data=response_data.model_dump(mode="json"),
        message="Prediction request received.",
    )
