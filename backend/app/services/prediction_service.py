"""Prediction service.

Phase 4.1 introduced only the service skeleton so the Prediction Router
has a stable dependency to call into. Phase 4.2 extended it to delegate
upload validation to the centralized `UploadValidator` (ADR-011). Phase
4.3 wired the public request/response contract (ADR-012) into the
router. Phase 4.4 introduced the full orchestration SKELETON (ADR-013):
every downstream pipeline stage is represented, logged, and recorded on
the returned `PredictionResult`. Phase 4.5.4 connected the RUNTIME stage
for real: `PredictionService` validates AI Runtime readiness
(`RuntimeValidator`, ADR-015) and collects a runtime metadata snapshot
(`RuntimeMetadataService`, ADR-016) -- both of which communicate with the
AI Runtime Manager only through `RuntimeAdapter` (ADR-014). Phase 4.6.1
connects the PREPROCESSING stage for real: `PredictionService` now hands
the already-validated upload bytes to the centralized `ImagePreprocessor`
(ADR-018), which converts them into a normalized, batched input tensor
*before* the RUNTIME stage runs. Phase 4.6.2 connects the REQUEST_BUILDING
stage for real: once both PREPROCESSING and RUNTIME have completed,
`PredictionService` delegates to `PredictionRequestBuilder` (ADR-019) to
assemble a single, standardized `PredictionRequest` -- the Prediction
Engine's only input. Phase 4.6.3 connects the PREDICTION_ENGINE stage for
real (ADR-020): once REQUEST_BUILDING has completed, `PredictionService`
delegated to `PredictionEngine.predict_single_model()`, which executed
inference using only the single highest-priority production model
(currently MobileNetV2), obtained exclusively through the AI Runtime
Manager (ADR-007). Phase 4.6.4 extends the PREDICTION_ENGINE stage
(ADR-021): `PredictionService` now delegates to
`PredictionEngine.predict_multi_model()`, which executes inference
sequentially across every currently loaded production model, in
ascending Model Manifest loading priority order, and continues even if
one or more models fail. No ensemble voting happens yet: this stage
never calls the Adaptive Ensemble Engine. Phase 4.6.5 connects the
RESULT_COLLECTION stage for real (ADR-022): once PREDICTION_ENGINE has
completed, `PredictionService` delegates to
`PredictionResultCollector.collect()`, which standardizes every
`IndividualPrediction`/`FailedModelPrediction` produced by the Prediction
Engine, together with aggregate execution statistics and a human-readable
execution summary, into a single `PredictionExecutionResult` -- the
Adaptive Ensemble Engine's only future input (Phase 4.7). No ensemble
voting, agreement calculation, or final prediction selection is performed
by this stage. Phase 4.7.1 connects the ENSEMBLE stage for real (ADR-024):
once RESULT_COLLECTION has completed, `PredictionService` builds an
`EnsembleRequest` from the resulting `PredictionExecutionResult` and
delegates to `EnsembleEngine.process()`, which validates the request,
separates accepted (successful) predictions from rejected (failed) ones,
and returns an `EnsembleResult` ready for future voting. No ensemble
voting, confidence calculation, or final prediction selection is
performed by this stage either -- that begins in Phase 4.7.2 onward.
Phase 4.7.4.2 connects the FINAL_PREDICTION step for real (ADR-027):
once the ENSEMBLE stage has completed, `PredictionService` chains the
`AdaptiveWeightedVotingEngine` (Phase 4.7.2, ADR-025), the
`ConfidenceCalibrationEngine` (Phase 4.7.3, ADR-026), and the
`FinalPredictionBuilder` (Phase 4.7.4, ADR-027) -- in that order,
unmodified -- to turn the completed PREDICTION_ENGINE stage output into
a populated `FinalPredictionResult`. This step produces an internal
diagnostics value only (`PredictionResult.final_prediction_result`); it
performs NO API response formatting and never changes the existing
RESPONSE, HISTORY, or REPORT placeholder stages or the public API
response contract -- that remained the Response Builder's
responsibility (Phase 4.8.1). Phase 4.8.2 connects the RESPONSE stage
for real (ADR-028): once the internal FINAL_PREDICTION step has
completed, `PredictionService` delegates to
`PredictionResponseBuilder.build()`, which copies the completed
`FinalPredictionResult` into a standardized `PredictionResponseResult`
-- recorded on `PredictionResult.response_result`. The Prediction
Router projects that value onto the public `result` field of
`PredictionResponseSchema`, replacing the `null` placeholder used by
every earlier phase. Phase 4.8.3 (ADR-029) carries the PREDICTION_ENGINE
stage's already-computed `PredictionExecutionStats`
(`app.ml.prediction.prediction_result.PredictionExecutionStats`) through
unchanged onto `PredictionResult.execution_stats`, so the Prediction
Router can project it onto the public `runtime_statistics` field
without `PredictionService` performing any additional timing
calculations, preprocessing, or inference itself.

Future phases extend this same class without changing its public
surface:
    - Phase 4.7.2 wires in the Voting & Agreement Engine (module ready).
    - Phase 4.7.3 wires in Confidence Calibration (module ready).
    - Phase 4.7.4.2 wires the Final Prediction Builder into this service
      (completed).
    - Phase 4.8.2 wires in the Response Builder (completed).
    - Phase 4.8.3 carries PredictionExecutionStats through onto
      PredictionResult for the router's runtime statistics projection
      (this phase).
    - Phase 5 wires in Prediction History.
    - Phase 6 wires in Report Generation.

The router must never bypass this service to reach the ML layer
directly.
"""

from fastapi import UploadFile

from app.core.logging import get_logger
from app.core.upload import UploadValidator
from app.history.exceptions import PredictionHistoryError
from app.ml.ensemble.calibration_engine import ConfidenceCalibrationEngine
from app.ml.ensemble.ensemble_engine import EnsembleEngine
from app.ml.ensemble.ensemble_request import EnsembleRequest
from app.ml.ensemble.ensemble_result import EnsembleResult
from app.ml.ensemble.exceptions import (
    EnsembleConfigurationError,
    InvalidEnsembleInputError,
    PredictionUnavailableError,
)
from app.ml.ensemble.final_prediction_builder import FinalPredictionBuilder
from app.ml.ensemble.final_prediction_result import FinalPredictionResult
from app.ml.ensemble.voting_engine import AdaptiveWeightedVotingEngine
from app.ml.exceptions import ModelNotFoundError
from app.ml.prediction.exceptions import NoModelsAvailableError, PredictionRequestBuildError
from app.ml.prediction.execution_profiler import ExecutionProfiler, ProfiledStage
from app.ml.prediction.prediction_engine import PredictionEngine
from app.ml.prediction.prediction_execution_result import (
    PredictionExecutionResult,
    PredictionResultCollector,
)
from app.ml.prediction.prediction_request import PredictionRequest
from app.ml.prediction.prediction_result import PredictionEngineResult
from app.ml.prediction.request_builder import PredictionRequestBuilder
from app.ml.preprocessing.exceptions import PreprocessingError
from app.ml.preprocessing.image_preprocessor import ImagePreprocessor
from app.ml.preprocessing.preprocessing_result import PreprocessingResult
from app.ml.response.exceptions import InvalidResponseInputError
from app.ml.response.response_builder import PredictionResponseBuilder
from app.ml.response.response_result import PredictionResponseResult
from app.ml.runtime.exceptions import ModelUnavailableError
from app.ml.runtime.exceptions import (
    RuntimeNotInitializedError as RuntimeManagerNotInitializedError,
)
from app.ml.runtime.runtime_manager import AIRuntimeManager
from app.models.user import User
from app.services.prediction_context import PredictionContext, PredictionOptions
from app.services.prediction_exceptions import (
    EnsembleUnavailableError,
    PredictionEngineExecutionError,
    PredictionPipelineError,
    ResponseBuildError,
)
from app.services.prediction_history_service import PredictionHistoryService
from app.services.prediction_result import (
    PipelineStageName,
    PipelineStageRecord,
    PipelineStageStatus,
    PredictionResult,
)
from app.services.runtime_metadata import RuntimeMetadata, RuntimeMetadataService
from app.services.runtime_validator import RuntimeValidationResult, RuntimeValidator
from app.utils.environment import generate_request_id, get_current_timestamp

logger = get_logger(__name__)

PIPELINE_PLACEHOLDER_MESSAGE = (
    "Prediction request accepted. Downstream pipeline stages (runtime, "
    "inference, ensemble, history, and reporting) are not yet connected."
)

RUNTIME_CONNECTED_PLACEHOLDER_MESSAGE = (
    "Prediction request accepted. AI Runtime Manager integration is connected "
    "(Phase 4.5); inference, ensemble, history, and reporting stages are not "
    "yet connected."
)

PREPROCESSING_CONNECTED_PLACEHOLDER_MESSAGE = (
    "Prediction request accepted. Image preprocessing is connected (Phase "
    "4.6.1); runtime, inference, ensemble, history, and reporting stages are "
    "not yet connected."
)

PREPROCESSING_AND_RUNTIME_CONNECTED_MESSAGE = (
    "Prediction request accepted. Image preprocessing (Phase 4.6.1) and AI "
    "Runtime Manager integration (Phase 4.5) are connected; inference, "
    "ensemble, history, and reporting stages are not yet connected."
)

REQUEST_BUILT_MESSAGE = (
    "Prediction request accepted. Image preprocessing (Phase 4.6.1), AI "
    "Runtime Manager integration (Phase 4.5), and Prediction Request "
    "construction (Phase 4.6.2) are connected; inference, ensemble, "
    "history, and reporting stages are not yet connected."
)

PREDICTION_ENGINE_CONNECTED_MESSAGE = (
    "Prediction request accepted. Image preprocessing (Phase 4.6.1), AI "
    "Runtime Manager integration (Phase 4.5), Prediction Request "
    "construction (Phase 4.6.2), and sequential multi-model inference via "
    "the Prediction Engine (Phase 4.6.4, ADR-021) are connected; ensemble "
    "aggregation (Phase 4.7), history (Phase 5), and reporting (Phase 6) "
    "stages are not yet connected."
)

RESULT_COLLECTION_CONNECTED_MESSAGE = (
    "Prediction request accepted. Image preprocessing (Phase 4.6.1), AI "
    "Runtime Manager integration (Phase 4.5), Prediction Request "
    "construction (Phase 4.6.2), sequential multi-model inference via the "
    "Prediction Engine (Phase 4.6.4, ADR-021), and standardized Prediction "
    "Result Collection (Phase 4.6.5, ADR-022) are connected; ensemble "
    "aggregation (Phase 4.7), history (Phase 5), and reporting (Phase 6) "
    "stages are not yet connected."
)

ENSEMBLE_CONNECTED_MESSAGE = (
    "Prediction request accepted. Image preprocessing (Phase 4.6.1), AI "
    "Runtime Manager integration (Phase 4.5), Prediction Request "
    "construction (Phase 4.6.2), sequential multi-model inference via the "
    "Prediction Engine (Phase 4.6.4, ADR-021), standardized Prediction "
    "Result Collection (Phase 4.6.5, ADR-022), and Adaptive Ensemble "
    "Integration (Phase 4.7.1, ADR-024) are connected; voting and "
    "agreement (Phase 4.7.2), confidence calibration (Phase 4.7.3), final "
    "prediction (Phase 4.7.4), response formatting, history (Phase 5), and "
    "reporting (Phase 6) stages are not yet connected."
)

FINAL_PREDICTION_CONNECTED_MESSAGE = (
    "Prediction request accepted. Image preprocessing (Phase 4.6.1), AI "
    "Runtime Manager integration (Phase 4.5), Prediction Request "
    "construction (Phase 4.6.2), sequential multi-model inference via the "
    "Prediction Engine (Phase 4.6.4, ADR-021), standardized Prediction "
    "Result Collection (Phase 4.6.5, ADR-022), Adaptive Ensemble "
    "Integration (Phase 4.7.1, ADR-024), and the internal Final Prediction "
    "Builder chain -- Adaptive Weighted Voting (Phase 4.7.2, ADR-025), "
    "Confidence Calibration (Phase 4.7.3, ADR-026), and the Final "
    "Prediction Builder (Phase 4.7.4, ADR-027) -- are connected; API "
    "response formatting (Phase 4.8), history (Phase 5), and reporting "
    "(Phase 6) stages are not yet connected."
)

RESPONSE_CONNECTED_MESSAGE = (
    "Prediction request accepted. Image preprocessing (Phase 4.6.1), AI "
    "Runtime Manager integration (Phase 4.5), Prediction Request "
    "construction (Phase 4.6.2), sequential multi-model inference via the "
    "Prediction Engine (Phase 4.6.4, ADR-021), standardized Prediction "
    "Result Collection (Phase 4.6.5, ADR-022), Adaptive Ensemble "
    "Integration (Phase 4.7.1, ADR-024), the internal Final Prediction "
    "Builder chain (Phase 4.7.2-4.7.4, ADR-025/ADR-026/ADR-027), and API "
    "Response Builder integration (Phase 4.8.2, ADR-028) are connected; "
    "history (Phase 5) and reporting (Phase 6) stages are not yet "
    "connected."
)

HISTORY_CONNECTED_MESSAGE = (
    "Prediction request accepted. Image preprocessing (Phase 4.6.1), AI "
    "Runtime Manager integration (Phase 4.5), Prediction Request "
    "construction (Phase 4.6.2), sequential multi-model inference via the "
    "Prediction Engine (Phase 4.6.4, ADR-021), standardized Prediction "
    "Result Collection (Phase 4.6.5, ADR-022), Adaptive Ensemble "
    "Integration (Phase 4.7.1, ADR-024), the internal Final Prediction "
    "Builder chain (Phase 4.7.2-4.7.4, ADR-025/ADR-026/ADR-027), API "
    "Response Builder integration (Phase 4.8.2, ADR-028), and Prediction "
    "History persistence integration (Phase 5.2, ADR-033) are connected; "
    "the reporting stage (Phase 6) is not yet connected."
)


class PredictionService:
    """Coordinates the prediction pipeline on behalf of the Prediction API.

    Phase 4.4 defined the complete orchestration shape described by
    ADR-013 -- upload validation, context creation, preprocessing, the AI
    Runtime Manager, the Prediction Engine, the Adaptive Ensemble Engine,
    response building, history, and reporting. Phase 4.5.4 connected the
    RUNTIME stage for real. Phase 4.6.1 connects the PREPROCESSING stage,
    Phase 4.6.2 connects the REQUEST_BUILDING stage, and Phase 4.6.3
    connected the PREDICTION_ENGINE stage to single-model inference.
    Phase 4.6.4 extends the PREDICTION_ENGINE stage (see below) to
    sequential multi-model execution for real. Phase 4.6.5 connects the
    RESULT_COLLECTION stage to real standardization of the Prediction
    Engine's output (ADR-022). Phase 4.7.1 connects the ENSEMBLE stage to
    real validation and preparation of the standardized
    `PredictionExecutionResult` via `EnsembleEngine` (ADR-024). Phase
    4.7.4.2 connects the internal FINAL_PREDICTION step to real voting,
    calibration, and final-prediction building via
    `AdaptiveWeightedVotingEngine`, `ConfidenceCalibrationEngine`, and
    `FinalPredictionBuilder` (ADR-025/ADR-026/ADR-027); every remaining
    stage (RESPONSE, HISTORY, REPORT) stays a logged placeholder.

    `image_preprocessor` is Phase 4.6.1's real collaborator for the
    PREPROCESSING stage (ADR-018); it depends only on `ModelRegistry` --
    a pure, static Model Manifest reader -- and never on
    `AIRuntimeManager`, so `PredictionService` still never gains a direct
    reference to the AI Runtime. `runtime_validator` and
    `runtime_metadata_service` are Phase 4.5.4's real collaborators for
    the RUNTIME stage (ADR-015, ADR-016); both depend only on
    `RuntimeAdapter` (ADR-014), never on `AIRuntimeManager` or
    `ModelRegistry` directly, so `PredictionService` never gains a direct
    reference to either. `request_builder` is Phase 4.6.2's real
    collaborator for the REQUEST_BUILDING stage (ADR-019); it is stateless
    and depends on nothing but the PREPROCESSING and RUNTIME stage outputs
    already held by this method, so it introduces no new external
    dependency either. `prediction_engine` is Phase 4.6.3's (and now
    Phase 4.6.4's) real collaborator for the PREDICTION_ENGINE stage
    (ADR-020/ADR-021); it depends on `AIRuntimeManager` and
    `ModelRegistry` directly (per ADR-007), which is consistent with the
    Prediction Engine's own layering rules and introduces no new
    dependency for `PredictionService` itself. `result_collector` is Phase
    4.6.5's real collaborator for the RESULT_COLLECTION stage (ADR-022);
    it depends only on `ModelRegistry` -- the same pure, static Model
    Manifest reader `image_preprocessor` already depends on -- and never
    on `AIRuntimeManager`, so this stage introduces no new dependency for
    `PredictionService` either. `ensemble_engine` is Phase 4.7.1's real
    collaborator for the ENSEMBLE stage (ADR-024); it is stateless and
    depends on nothing but the RESULT_COLLECTION stage output already
    held by this method, so it introduces no new external dependency
    either. It consumes an `EnsembleRequest` built from the completed
    `PredictionExecutionResult` and returns a validated `EnsembleResult`
    -- no voting, confidence calculation, or final prediction selection
    is performed by this stage (that begins in Phase 4.7.2 onward).
    `runtime_manager` remains accepted ahead of being used, purely so
    later phases can inject it through `app.dependencies.services`
    without changing this class's constructor signature.

    `voting_engine`, `calibration_engine`, and `final_prediction_builder`
    are Phase 4.7.4.2's real collaborators for the internal
    FINAL_PREDICTION step (ADR-025/ADR-026/ADR-027). Once the ENSEMBLE
    stage has completed, `PredictionService` feeds the completed
    PREDICTION_ENGINE stage's `PredictionEngineResult` to
    `voting_engine.calculate_votes()`, feeds the resulting `VotingResult`
    to `calibration_engine.calibrate()`, and feeds the resulting
    `CalibratedEnsembleResult` to `final_prediction_builder.build()`.
    None of the three collaborators is modified by this phase -- they are
    used exactly as Phase 4.7.2/4.7.3/4.7.4 defined them -- and none of
    them communicates with `AIRuntimeManager`, `PredictionEngine`, or
    TensorFlow models, so `PredictionService` gains no new external
    dependency beyond the three collaborators themselves. This step never
    touches the RESPONSE, HISTORY, or REPORT placeholder stages, and its
    output is recorded only on `PredictionResult.final_prediction_result`
    -- an internal diagnostics field, not the public API contract.

    `response_builder` is Phase 4.8.2's real collaborator for the
    RESPONSE stage (ADR-028). Once the internal FINAL_PREDICTION step has
    completed, `PredictionService` feeds the resulting
    `FinalPredictionResult` to `response_builder.build()`, recording the
    resulting `PredictionResponseResult` on
    `PredictionResult.response_result`. `PredictionResponseBuilder` is
    stateless and depends on nothing but the FINAL_PREDICTION step output
    already held by this method, so it introduces no new external
    dependency either. This stage never touches the HISTORY or REPORT
    placeholder stages, and it never communicates with
    `AIRuntimeManager`, `PredictionEngine`, or TensorFlow models.

    `image_preprocessor`, `runtime_validator`, `runtime_metadata_service`,
    `request_builder`, `result_collector`, `ensemble_engine`,
    `voting_engine`, `calibration_engine`, `final_prediction_builder`, and
    `response_builder` all default to `None` so existing callers that
    construct `PredictionService` without them keep working: the
    corresponding stage falls back to the Phase 4.4 skipped placeholder in
    that case.
    """

    def __init__(
        self,
        upload_validator: UploadValidator,
        image_preprocessor: ImagePreprocessor | None = None,
        runtime_validator: RuntimeValidator | None = None,
        runtime_metadata_service: RuntimeMetadataService | None = None,
        request_builder: PredictionRequestBuilder | None = None,
        runtime_manager: AIRuntimeManager | None = None,
        prediction_engine: PredictionEngine | None = None,
        result_collector: PredictionResultCollector | None = None,
        ensemble_engine: EnsembleEngine | None = None,
        voting_engine: AdaptiveWeightedVotingEngine | None = None,
        calibration_engine: ConfidenceCalibrationEngine | None = None,
        final_prediction_builder: FinalPredictionBuilder | None = None,
        response_builder: PredictionResponseBuilder | None = None,
    ) -> None:
        self._upload_validator = upload_validator
        self._image_preprocessor = image_preprocessor
        self._runtime_validator = runtime_validator
        self._runtime_metadata_service = runtime_metadata_service
        self._request_builder = request_builder
        self._runtime_manager = runtime_manager
        self._prediction_engine = prediction_engine
        self._result_collector = result_collector
        self._ensemble_engine = ensemble_engine
        self._voting_engine = voting_engine
        self._calibration_engine = calibration_engine
        self._final_prediction_builder = final_prediction_builder
        self._response_builder = response_builder

    async def predict(
        self,
        image: UploadFile,
        current_user: User,
        options: PredictionOptions,
        history_service: PredictionHistoryService | None = None,
    ) -> PredictionResult:
        """Run an uploaded image through the prediction pipeline.

        Upload validation, prediction-context creation, and (when the
        relevant collaborators were injected) the PREPROCESSING, RUNTIME,
        REQUEST_BUILDING, PREDICTION_ENGINE, RESULT_COLLECTION, ENSEMBLE,
        FINAL_PREDICTION, RESPONSE, and (as of Phase 5.2) HISTORY stages
        actually execute; every remaining stage is recorded as a logged
        placeholder on the returned `PredictionResult` (see the module
        docstring for which phase wires in each one).

        Args:
            image: The uploaded histopathology image.
            current_user: The authenticated user submitting the request.
            options: Validated prediction control flags for this request
                (see `PredictionOptions.from_request`).
            history_service: The request-scoped `PredictionHistoryService`
                to persist this prediction's history record with (Phase
                5.2, ADR-033). Supplied per-call rather than through the
                constructor because it is bound to a request-scoped
                database session (see
                `app.dependencies.services.get_prediction_history_service`),
                unlike this service's other, stateless collaborators.
                Defaults to `None`, in which case the HISTORY stage is
                recorded as skipped and `PredictionResult.history_reference`
                stays `None` -- preserving backward compatibility for
                callers that do not supply one.

        Returns:
            A `PredictionResult` describing every pipeline stage's outcome.

        Raises:
            app.core.upload.UploadValidationException:
                Propagated from `UploadValidator` if the uploaded image
                fails centralized validation.
            app.ml.preprocessing.exceptions.PreprocessingError (or a
                subclass): Propagated from `ImagePreprocessor` if the
                uploaded image cannot be preprocessed (ADR-018). The
                pipeline stops immediately and never reaches the RUNTIME
                stage.
            RuntimeNotInitializedError: The AI Runtime has not finished
                its startup loading sequence (ADR-015).
            NoLoadedModelsError: The AI Runtime is initialized but zero
                models are currently in the READY state (ADR-015).
            RuntimeUnavailableError: The AI Runtime is initialized with at
                least one loaded model, yet its qualitative availability
                is still unhealthy (ADR-015).
            RuntimeValidationFailedError: Runtime state could not be read.
            RuntimeMetadataCollectionFailedError: Runtime metadata could
                not be collected after validation passed.
            app.ml.prediction.exceptions.PredictionRequestBuildError (or a
                subclass): Propagated from `PredictionRequestBuilder` if a
                `PredictionRequest` cannot be assembled from the completed
                PREPROCESSING and RUNTIME stage outputs (ADR-019). Not
                expected to be reachable in normal operation, since both
                stages already validated their own outputs before this
                stage runs.
            app.services.prediction_exceptions.PredictionEngineExecutionError:
                Raised from the PREDICTION_ENGINE stage (Phase 4.6.4,
                ADR-021) when zero production models are currently loaded,
                or when every currently loaded production model fails
                during inference.
            app.services.prediction_exceptions.EnsembleUnavailableError:
                Raised from the ENSEMBLE stage (Phase 4.7.1, ADR-024) or
                the internal FINAL_PREDICTION step (Phase 4.7.4.2,
                ADR-025/ADR-026/ADR-027) when the Adaptive Ensemble
                Engine, Adaptive Weighted Voting Engine, Confidence
                Calibration Engine, or Final Prediction Builder rejects
                its input.
        """
        request_id = generate_request_id()
        requested_at = get_current_timestamp()

        logger.info(
            "Prediction request received: request_id=%s user_id=%s filename=%s",
            request_id,
            current_user.id,
            image.filename,
        )
        logger.info("Prediction started: request_id=%s", request_id)

        stages: list[PipelineStageRecord] = []
        profiler = ExecutionProfiler(request_id=request_id)

        self._enter_stage(PipelineStageName.UPLOAD_VALIDATION)
        validation = await self._upload_validator.validate(image)
        stages.append(
            PipelineStageRecord(
                name=PipelineStageName.UPLOAD_VALIDATION,
                status=PipelineStageStatus.COMPLETED,
                detail="Upload passed centralized validation (ADR-011).",
            )
        )

        self._enter_stage(PipelineStageName.CONTEXT_CREATION)
        context = PredictionContext.from_validated_upload(
            request_id=request_id,
            requested_at=requested_at,
            user_id=str(current_user.id),
            user_email=current_user.email,
            validation=validation,
            options=options,
        )
        logger.info("Prediction context created: request_id=%s", context.request_id)
        stages.append(
            PipelineStageRecord(
                name=PipelineStageName.CONTEXT_CREATION,
                status=PipelineStageStatus.COMPLETED,
                detail="Prediction context built from validated upload metadata.",
            )
        )

        preprocessing_result = await self._execute_preprocessing_stage(
            image=image, context=context, stages=stages, profiler=profiler
        )

        runtime_validation, runtime_metadata = await self._execute_runtime_stage(
            context=context, stages=stages, profiler=profiler
        )

        prediction_request = await self._execute_request_building_stage(
            context=context,
            current_user=current_user,
            preprocessing_result=preprocessing_result,
            runtime_validation=runtime_validation,
            runtime_metadata=runtime_metadata,
            stages=stages,
            profiler=profiler,
        )

        prediction_engine_result = await self._execute_prediction_engine_stage(
            context=context,
            prediction_request=prediction_request,
            stages=stages,
            profiler=profiler,
        )

        execution_result = await self._execute_result_collection_stage(
            context=context,
            runtime_metadata=runtime_metadata,
            profiler=profiler,
            prediction_engine_result=prediction_engine_result,
            stages=stages,
        )

        ensemble_result = await self._execute_ensemble_stage(
            context=context,
            execution_result=execution_result,
            stages=stages,
        )

        final_prediction_result = await self._execute_final_prediction_stage(
            context=context,
            prediction_engine_result=prediction_engine_result,
            ensemble_result=ensemble_result,
        )

        response_result = await self._execute_response_stage(
            context=context,
            final_prediction_result=final_prediction_result,
            stages=stages,
        )

        individual_model_results = (
            prediction_engine_result.predictions if prediction_engine_result is not None else None
        )
        execution_stats = (
            prediction_engine_result.execution_stats
            if prediction_engine_result is not None
            else None
        )

        history_reference = await self._execute_history_stage(
            context=context,
            stages=stages,
            response_result=response_result,
            individual_model_results=individual_model_results,
            execution_stats=execution_stats,
            runtime_metadata=runtime_metadata,
            history_service=history_service,
        )

        stages.append(
            self._skip_stage(
                PipelineStageName.REPORT,
                "Report generation is introduced in Phase 6.",
            )
        )

        logger.info("Prediction completed (placeholder): request_id=%s", context.request_id)
        if execution_result is not None:
            logger.info(
                "Total prediction execution time: request_id=%s total_prediction_time_ms=%.2f",
                context.request_id,
                execution_result.runtime_statistics.total_prediction_time_ms,
            )

        if response_result is not None:
            message = HISTORY_CONNECTED_MESSAGE
        elif final_prediction_result is not None:
            message = FINAL_PREDICTION_CONNECTED_MESSAGE
        elif ensemble_result is not None:
            message = ENSEMBLE_CONNECTED_MESSAGE
        elif execution_result is not None:
            message = RESULT_COLLECTION_CONNECTED_MESSAGE
        elif prediction_engine_result is not None:
            message = PREDICTION_ENGINE_CONNECTED_MESSAGE
        elif prediction_request is not None:
            message = REQUEST_BUILT_MESSAGE
        elif preprocessing_result is not None and runtime_metadata is not None:
            message = PREPROCESSING_AND_RUNTIME_CONNECTED_MESSAGE
        elif runtime_metadata is not None:
            message = RUNTIME_CONNECTED_PLACEHOLDER_MESSAGE
        elif preprocessing_result is not None:
            message = PREPROCESSING_CONNECTED_PLACEHOLDER_MESSAGE
        else:
            message = PIPELINE_PLACEHOLDER_MESSAGE

        prediction_result = PredictionResult(
            request_id=context.request_id,
            requested_at=context.requested_at,
            message=message,
            stages=stages,
            preprocessing_result=preprocessing_result,
            runtime_statistics=runtime_metadata,
            runtime_validation=runtime_validation,
            prediction_request=prediction_request,
            individual_model_results=individual_model_results,
            execution_stats=execution_stats,
            execution_result=execution_result,
            ensemble_result=ensemble_result,
            final_prediction_result=final_prediction_result,
            response_result=response_result,
            history_reference=history_reference,
        )

        if response_result is not None:
            logger.info(
                "Response successfully returned: request_id=%s predicted_class=%s",
                context.request_id,
                response_result.predicted_class,
            )

        return prediction_result

    async def _execute_preprocessing_stage(
        self,
        image: UploadFile,
        context: PredictionContext,
        stages: list[PipelineStageRecord],
        profiler: ExecutionProfiler,
    ) -> PreprocessingResult | None:
        """Run the PREPROCESSING pipeline stage (ADR-013, Phase 4.6.1).

        Phase 4.6.6 wraps this stage's existing work in
        `profiler.measure(ProfiledStage.PREPROCESSING)`, without changing
        any of its logic, so `RuntimeStatistics.preprocessing_time_ms`
        reflects this stage's real wall-clock duration.

        Reads the already-validated upload bytes and hands them to the
        centralized `ImagePreprocessor` (ADR-018), which converts them
        into a normalized, batched input tensor. This stage never calls
        `AIRuntimeManager`, `PredictionEngine`, or
        `AdaptiveEnsembleEngine`; it always runs, and must always
        complete, before the RUNTIME stage is attempted.

        Falls back to the Phase 4.4 skipped placeholder when no
        `ImagePreprocessor` was injected, preserving backward
        compatibility for callers that construct `PredictionService`
        without one.

        Args:
            image: The uploaded histopathology image, already accepted by
                `UploadValidator` (ADR-011).
            context: The prediction context for this request, used only
                for logging.
            stages: The in-progress pipeline stage list; the
                PREPROCESSING stage's outcome is appended to it.

        Returns:
            The `PreprocessingResult` for this request, or `None` when
            the PREPROCESSING stage was skipped.

        Raises:
            app.ml.preprocessing.exceptions.PreprocessingError (or a
                subclass): Propagated unchanged if the uploaded image
                cannot be preprocessed. The pipeline stops immediately
                and never reaches the RUNTIME stage.
        """
        if self._image_preprocessor is None:
            skipped_record = self._skip_stage(
                PipelineStageName.PREPROCESSING,
                "Image preprocessing pipeline integration is introduced in "
                "Phase 4.6.1.",
            )
            stages.append(skipped_record)
            return None

        self._enter_stage(PipelineStageName.PREPROCESSING)

        try:
            with profiler.measure(ProfiledStage.PREPROCESSING):
                image_bytes = await image.read()
                preprocessing_result = self._image_preprocessor.preprocess(image_bytes)
        except PreprocessingError:
            logger.warning(
                "Prediction halted at preprocessing stage: request_id=%s",
                context.request_id,
            )
            raise

        logger.info(
            "Preprocessing stage completed: request_id=%s size=%dx%d time_ms=%.2f",
            context.request_id,
            preprocessing_result.processed_width,
            preprocessing_result.processed_height,
            preprocessing_result.preprocessing_time_ms,
        )
        stages.append(
            PipelineStageRecord(
                name=PipelineStageName.PREPROCESSING,
                status=PipelineStageStatus.COMPLETED,
                detail=(
                    f"Image preprocessed to {preprocessing_result.processed_width}x"
                    f"{preprocessing_result.processed_height} in "
                    f"{preprocessing_result.preprocessing_time_ms:.2f} ms."
                ),
            )
        )
        return preprocessing_result

    async def _execute_runtime_stage(
        self,
        context: PredictionContext,
        stages: list[PipelineStageRecord],
        profiler: ExecutionProfiler,
    ) -> tuple[RuntimeValidationResult | None, RuntimeMetadata | None]:
        """Run the RUNTIME pipeline stage (ADR-013, Phase 4.5.4).

        Phase 4.6.6 wraps only the `RuntimeValidator.validate_or_raise()`
        call in `profiler.measure(ProfiledStage.RUNTIME_VALIDATION)`,
        without changing any of this stage's logic, so
        `RuntimeStatistics.runtime_validation_time_ms` reflects readiness
        validation's real wall-clock duration specifically (metadata
        collection is a separate concern and is not included in that
        measurement).

        Validates AI Runtime readiness through `RuntimeValidator`
        (ADR-015) and, only once validation passes, collects a runtime
        metadata snapshot through `RuntimeMetadataService` (ADR-016).
        Both collaborators communicate with the AI Runtime Manager only
        through `RuntimeAdapter` (ADR-014); no TensorFlow model is ever
        loaded, instantiated, or invoked here.

        Falls back to the Phase 4.4 skipped placeholder when either
        collaborator was not injected, preserving backward compatibility
        for callers that construct `PredictionService` without them.

        Args:
            context: The prediction context for this request, used only
                for logging.
            stages: The in-progress pipeline stage list; the RUNTIME
                stage's outcome is appended to it.

        Returns:
            A `(runtime_validation, runtime_metadata)` tuple. Both are
            `None` when the RUNTIME stage was skipped.

        Raises:
            RuntimeNotInitializedError: The runtime has not finished its
                startup loading sequence.
            NoLoadedModelsError: The runtime is initialized but zero
                models are currently in the READY state.
            RuntimeUnavailableError: The runtime is initialized with at
                least one loaded model, yet its qualitative availability
                is still unhealthy.
            RuntimeValidationFailedError: Runtime state could not be read.
            RuntimeMetadataCollectionFailedError: Runtime metadata could
                not be collected after validation passed.
        """
        if self._runtime_validator is None or self._runtime_metadata_service is None:
            skipped_record = self._skip_stage(
                PipelineStageName.RUNTIME,
                "AI Runtime Manager integration is introduced in Phase 4.5.",
            )
            stages.append(skipped_record)
            return None, None

        self._enter_stage(PipelineStageName.RUNTIME)

        try:
            with profiler.measure(ProfiledStage.RUNTIME_VALIDATION):
                runtime_validation = await self._runtime_validator.validate_or_raise()
            runtime_metadata = await self._runtime_metadata_service.collect()
        except PredictionPipelineError:
            logger.warning(
                "Prediction halted at runtime stage: request_id=%s", context.request_id
            )
            raise

        logger.info(
            "Runtime stage completed: request_id=%s loaded=%d failed=%d",
            context.request_id,
            runtime_validation.loaded_model_count,
            runtime_validation.failed_model_count,
        )
        stages.append(
            PipelineStageRecord(
                name=PipelineStageName.RUNTIME,
                status=PipelineStageStatus.COMPLETED,
                detail=runtime_validation.validation_message,
            )
        )
        return runtime_validation, runtime_metadata

    async def _execute_request_building_stage(
        self,
        context: PredictionContext,
        current_user: User,
        preprocessing_result: PreprocessingResult | None,
        runtime_validation: RuntimeValidationResult | None,
        runtime_metadata: RuntimeMetadata | None,
        stages: list[PipelineStageRecord],
        profiler: ExecutionProfiler,
    ) -> PredictionRequest | None:
        """Run the REQUEST_BUILDING pipeline stage (ADR-013, Phase 4.6.2).

        Delegates to `PredictionRequestBuilder` (ADR-019) to assemble a
        single, standardized `PredictionRequest` from the already-completed
        PREPROCESSING and RUNTIME stage outputs. This stage never calls
        `AIRuntimeManager`, `PredictionEngine`, or
        `AdaptiveEnsembleEngine`, and performs no AI inference.

        Phase 4.6.6 wraps this stage's existing work in
        `profiler.measure(ProfiledStage.REQUEST_BUILDING)`, without
        changing any of its logic, so
        `RuntimeStatistics.request_build_time_ms` reflects this stage's
        real wall-clock duration.

        Falls back to the Phase 4.4 skipped placeholder when no
        `PredictionRequestBuilder` was injected, or when the PREPROCESSING
        or RUNTIME stages did not complete (so this stage never runs ahead
        of the outputs it depends on).

        Args:
            context: The prediction context for this request, used only
                for logging.
            current_user: The authenticated user submitting the request.
            preprocessing_result: The completed PREPROCESSING stage
                outcome, or `None` when that stage was skipped.
            runtime_validation: The completed RUNTIME stage's validation
                outcome, or `None` when that stage was skipped.
            runtime_metadata: The completed RUNTIME stage's metadata
                snapshot, or `None` when that stage was skipped.
            stages: The in-progress pipeline stage list; the
                REQUEST_BUILDING stage's outcome is appended to it.

        Returns:
            The built `PredictionRequest` for this request, or `None` when
            the REQUEST_BUILDING stage was skipped.

        Raises:
            app.ml.prediction.exceptions.PredictionRequestBuildError (or a
                subclass): Propagated unchanged if a `PredictionRequest`
                cannot be assembled from the supplied inputs.
        """
        if self._request_builder is None:
            skipped_record = self._skip_stage(
                PipelineStageName.REQUEST_BUILDING,
                "Prediction Request Builder integration is introduced in "
                "Phase 4.6.2.",
            )
            stages.append(skipped_record)
            return None

        if preprocessing_result is None or runtime_validation is None or runtime_metadata is None:
            skipped_record = self._skip_stage(
                PipelineStageName.REQUEST_BUILDING,
                "Prediction Request Builder requires completed PREPROCESSING "
                "and RUNTIME stages.",
            )
            stages.append(skipped_record)
            return None

        self._enter_stage(PipelineStageName.REQUEST_BUILDING)

        try:
            with profiler.measure(ProfiledStage.REQUEST_BUILDING):
                prediction_request = self._request_builder.build(
                    request_id=context.request_id,
                    preprocessing_result=preprocessing_result,
                    runtime_validation=runtime_validation,
                    runtime_metadata=runtime_metadata,
                    request_options=context.options,
                    current_user=current_user,
                )
        except PredictionRequestBuildError:
            logger.warning(
                "Prediction halted at request-building stage: request_id=%s",
                context.request_id,
            )
            raise

        logger.info(
            "Request-building stage completed: request_id=%s loaded_model_count=%d",
            context.request_id,
            prediction_request.prediction_configuration.loaded_model_count,
        )
        stages.append(
            PipelineStageRecord(
                name=PipelineStageName.REQUEST_BUILDING,
                status=PipelineStageStatus.COMPLETED,
                detail=(
                    "Standardized PredictionRequest built from PREPROCESSING "
                    "and RUNTIME stage outputs (ADR-019)."
                ),
            )
        )
        return prediction_request

    async def _execute_prediction_engine_stage(
        self,
        context: PredictionContext,
        prediction_request: PredictionRequest | None,
        stages: list[PipelineStageRecord],
        profiler: ExecutionProfiler,
    ) -> PredictionEngineResult | None:
        """Run the PREDICTION_ENGINE pipeline stage (ADR-013, Phase 4.6.4).

        Delegates to `PredictionEngine.predict_multi_model()` (ADR-021),
        which executes inference sequentially across every currently
        loaded production model, in ascending Model Manifest loading
        priority order (Project Context, Section 14):

            1. MobileNetV2
            2. DenseNet121
            3. EfficientNetV2B0 + ResNet50 Feature Fusion

        A model that is unavailable or fails during inference is skipped;
        prediction continues as long as at least one model executes
        successfully (ADR-005/ADR-021). No ensemble voting is performed
        here (ADR-008); that begins in Phase 4.7.

        Falls back to the Phase 4.4 skipped placeholder when no
        `PredictionEngine` was injected, or when the REQUEST_BUILDING
        stage did not complete (so this stage never runs ahead of the
        `PredictionRequest` it depends on).

        Args:
            context: The prediction context for this request, used only
                for logging.
            prediction_request: The completed REQUEST_BUILDING stage
                output, or `None` when that stage was skipped.
            stages: The in-progress pipeline stage list; the
                PREDICTION_ENGINE stage's outcome is appended to it.

        Returns:
            The `PredictionEngineResult` for this request, or `None` when
            the PREDICTION_ENGINE stage was skipped.

        Raises:
            app.services.prediction_exceptions.PredictionEngineExecutionError:
                If zero production models are currently loaded, or if
                every currently loaded production model fails during
                inference.
        """
        if self._prediction_engine is None:
            skipped_record = self._skip_stage(
                PipelineStageName.PREDICTION_ENGINE,
                "Prediction Engine integration is introduced in Phase 4.6.3.",
            )
            stages.append(skipped_record)
            return None

        if prediction_request is None:
            skipped_record = self._skip_stage(
                PipelineStageName.PREDICTION_ENGINE,
                "Prediction Engine requires a completed REQUEST_BUILDING stage.",
            )
            stages.append(skipped_record)
            return None

        self._enter_stage(PipelineStageName.PREDICTION_ENGINE)

        try:
            with profiler.measure(ProfiledStage.PREDICTION_ENGINE):
                engine_result = await self._prediction_engine.predict_multi_model(
                    prediction_request
                )
        except (
            NoModelsAvailableError,
            ModelNotFoundError,
            ModelUnavailableError,
            RuntimeManagerNotInitializedError,
        ) as exc:
            logger.warning(
                "Prediction halted at prediction-engine stage: request_id=%s reason=%s",
                context.request_id,
                exc.message,
            )
            raise PredictionEngineExecutionError(message=exc.message) from exc

        if not engine_result.predictions:
            failure_reason = (
                engine_result.failed_models[0].failure_reason
                if engine_result.failed_models
                else "Every currently loaded production model failed to produce a prediction."
            )
            logger.warning(
                "Prediction halted at prediction-engine stage: request_id=%s reason=%s",
                context.request_id,
                failure_reason,
            )
            raise PredictionEngineExecutionError(message=failure_reason)

        executed_model_names = ", ".join(
            prediction.model_name for prediction in engine_result.predictions
        )
        logger.info(
            "Prediction-engine stage completed: request_id=%s executed_model_count=%d "
            "failed_model_count=%d models=[%s] total_execution_time_ms=%.2f",
            context.request_id,
            engine_result.execution_stats.successful_predictions,
            engine_result.execution_stats.failed_predictions,
            executed_model_names,
            engine_result.execution_stats.total_execution_time_ms,
        )
        stages.append(
            PipelineStageRecord(
                name=PipelineStageName.PREDICTION_ENGINE,
                status=PipelineStageStatus.COMPLETED,
                detail=(
                    f"Sequential multi-model inference completed (ADR-021): "
                    f"{engine_result.execution_stats.successful_predictions} model(s) "
                    f"executed successfully [{executed_model_names}], "
                    f"{engine_result.execution_stats.failed_predictions} model(s) failed "
                    f"or were unavailable."
                ),
            )
        )
        return engine_result

    async def _execute_result_collection_stage(
        self,
        context: PredictionContext,
        runtime_metadata: RuntimeMetadata | None,
        prediction_engine_result: PredictionEngineResult | None,
        stages: list[PipelineStageRecord],
        profiler: ExecutionProfiler,
    ) -> PredictionExecutionResult | None:
        """Run the RESULT_COLLECTION pipeline stage (ADR-013, Phase 4.6.5).

        Delegates to `PredictionResultCollector.collect()` (ADR-022), which
        standardizes every `IndividualPrediction` and `FailedModelPrediction`
        produced by the completed PREDICTION_ENGINE stage, together with
        aggregate execution statistics and a human-readable execution
        summary, into a single `PredictionExecutionResult`. This stage
        performs no AI inference and never calls `AIRuntimeManager` or
        `AdaptiveEnsembleEngine`; no ensemble voting, agreement calculation,
        or final prediction selection is performed here (ADR-008/ADR-022).

        Phase 4.6.6 additionally hands this request's `ExecutionProfiler`
        to `PredictionResultCollector.collect()`, which finalizes it and
        derives `runtime_statistics`, `performance_metrics`, and
        `execution_profile` on the returned `PredictionExecutionResult`.

        Falls back to the Phase 4.4 skipped placeholder when no
        `PredictionResultCollector` was injected, or when the
        PREDICTION_ENGINE stage did not complete (so this stage never runs
        ahead of the `PredictionEngineResult` it depends on).

        Args:
            context: The prediction context for this request, used only
                for logging.
            runtime_metadata: The completed RUNTIME stage's metadata
                snapshot, carried through unchanged onto the returned
                `PredictionExecutionResult` for the Adaptive Ensemble
                Engine's future use (Phase 4.7).
            prediction_engine_result: The completed PREDICTION_ENGINE stage
                output, or `None` when that stage was skipped.
            stages: The in-progress pipeline stage list; the
                RESULT_COLLECTION stage's outcome is appended to it.

        Returns:
            The `PredictionExecutionResult` for this request, or `None`
            when the RESULT_COLLECTION stage was skipped.
        """
        if self._result_collector is None:
            skipped_record = self._skip_stage(
                PipelineStageName.RESULT_COLLECTION,
                "Prediction Result Collector integration is introduced in "
                "Phase 4.6.5.",
            )
            stages.append(skipped_record)
            return None

        if prediction_engine_result is None:
            skipped_record = self._skip_stage(
                PipelineStageName.RESULT_COLLECTION,
                "Prediction Result Collector requires a completed "
                "PREDICTION_ENGINE stage.",
            )
            stages.append(skipped_record)
            return None

        self._enter_stage(PipelineStageName.RESULT_COLLECTION)

        execution_result = self._result_collector.collect(
            request_id=context.request_id,
            runtime_metadata=runtime_metadata,
            engine_result=prediction_engine_result,
            execution_profiler=profiler,
        )

        logger.info(
            "Result-collection stage completed: request_id=%s executed_model_count=%d "
            "successful_model_count=%d failed_model_count=%d execution_status=%s",
            context.request_id,
            execution_result.execution_statistics.executed_model_count,
            execution_result.execution_statistics.successful_model_count,
            execution_result.execution_statistics.failed_model_count,
            execution_result.execution_status.value,
        )
        stages.append(
            PipelineStageRecord(
                name=PipelineStageName.RESULT_COLLECTION,
                status=PipelineStageStatus.COMPLETED,
                detail=execution_result.execution_summary.execution_message,
            )
        )
        return execution_result

    async def _execute_ensemble_stage(
        self,
        context: PredictionContext,
        execution_result: PredictionExecutionResult | None,
        stages: list[PipelineStageRecord],
    ) -> EnsembleResult | None:
        """Run the ENSEMBLE pipeline stage (ADR-013, Phase 4.7.1, ADR-024).

        Builds an `EnsembleRequest` from the completed RESULT_COLLECTION
        stage output (`EnsembleRequest.from_execution_result`) and
        delegates to `EnsembleEngine.process()`, which validates the
        request, separates accepted (successful) predictions from
        rejected (failed) ones, and returns an `EnsembleResult` ready for
        future voting. This stage performs NO ensemble voting, NO
        confidence calculation, and NO final prediction selection
        (ADR-024) -- those begin in Phase 4.7.2 onward. It never calls
        `AIRuntimeManager` or `PredictionEngine`.

        Falls back to the Phase 4.4 skipped placeholder when no
        `EnsembleEngine` was injected, or when the RESULT_COLLECTION
        stage did not complete (so this stage never runs ahead of the
        `PredictionExecutionResult` it depends on).

        Args:
            context: The prediction context for this request, used only
                for logging.
            execution_result: The completed RESULT_COLLECTION stage
                output, or `None` when that stage was skipped.
            stages: The in-progress pipeline stage list; the ENSEMBLE
                stage's outcome is appended to it.

        Returns:
            The `EnsembleResult` for this request, or `None` when the
            ENSEMBLE stage was skipped.

        Raises:
            app.services.prediction_exceptions.EnsembleUnavailableError:
                If the Adaptive Ensemble Engine rejects the request --
                either because the `PredictionExecutionResult` has zero
                successful predictions, or because the request is
                structurally invalid (missing runtime metadata or
                execution statistics; not expected to be reachable in
                normal operation, since RESULT_COLLECTION already
                populates both).
        """
        if self._ensemble_engine is None:
            skipped_record = self._skip_stage(
                PipelineStageName.ENSEMBLE,
                "Adaptive Ensemble Engine integration is introduced in Phase 4.7.",
            )
            stages.append(skipped_record)
            return None

        if execution_result is None:
            skipped_record = self._skip_stage(
                PipelineStageName.ENSEMBLE,
                "Adaptive Ensemble Engine requires a completed RESULT_COLLECTION stage.",
            )
            stages.append(skipped_record)
            return None

        self._enter_stage(PipelineStageName.ENSEMBLE)

        ensemble_request = EnsembleRequest.from_execution_result(execution_result)

        try:
            ensemble_result = self._ensemble_engine.process(ensemble_request)
        except (PredictionUnavailableError, InvalidEnsembleInputError) as exc:
            logger.warning(
                "Prediction halted at ensemble stage: request_id=%s reason=%s",
                context.request_id,
                exc.message,
            )
            raise EnsembleUnavailableError(message=exc.message) from exc

        logger.info(
            "Ensemble stage completed: request_id=%s status=%s accepted_count=%d "
            "rejected_count=%d",
            context.request_id,
            ensemble_result.ensemble_status.value,
            len(ensemble_result.accepted_predictions),
            len(ensemble_result.rejected_predictions),
        )
        stages.append(
            PipelineStageRecord(
                name=PipelineStageName.ENSEMBLE,
                status=PipelineStageStatus.COMPLETED,
                detail=(
                    f"Adaptive Ensemble Integration completed (ADR-024): "
                    f"{len(ensemble_result.accepted_predictions)} prediction(s) accepted "
                    f"[{', '.join(ensemble_result.successful_models)}], "
                    f"{len(ensemble_result.rejected_predictions)} rejected "
                    f"[{', '.join(ensemble_result.failed_models)}]. "
                    f"Status: {ensemble_result.ensemble_status.value}. Ready for future "
                    f"voting (Phase 4.7.2)."
                ),
            )
        )
        return ensemble_result

    async def _execute_final_prediction_stage(
        self,
        context: PredictionContext,
        prediction_engine_result: PredictionEngineResult | None,
        ensemble_result: EnsembleResult | None,
    ) -> FinalPredictionResult | None:
        """Run the internal FINAL_PREDICTION step (Phase 4.7.4.2, ADR-027).

        Chains three already-completed collaborators, in order, without
        modifying any of them:

            1. `AdaptiveWeightedVotingEngine.calculate_votes()` (Phase
               4.7.2, ADR-025) turns the completed PREDICTION_ENGINE
               stage's `PredictionEngineResult` into a `VotingResult`.
            2. `ConfidenceCalibrationEngine.calibrate()` (Phase 4.7.3,
               ADR-026) turns that `VotingResult` into a
               `CalibratedEnsembleResult`.
            3. `FinalPredictionBuilder.build()` (Phase 4.7.4, ADR-027)
               turns that `CalibratedEnsembleResult` into the
               `FinalPredictionResult` this step returns.

        This step is purely internal bookkeeping: it never formats an API
        response, never touches the RESPONSE/HISTORY/REPORT placeholder
        stages, and its output is recorded only on
        `PredictionResult.final_prediction_result` -- not the public API
        contract (that remains the Response Builder's responsibility,
        Phase 4.8). It never calls `AIRuntimeManager`, `PredictionEngine`,
        or TensorFlow models directly.

        Falls back to skipped (returns `None`) when any of
        `voting_engine`, `calibration_engine`, or
        `final_prediction_builder` was not injected, or when the ENSEMBLE
        stage did not complete (so this step never runs ahead of the
        `EnsembleResult` it depends on) -- preserving backward
        compatibility for callers that construct `PredictionService`
        without these collaborators.

        Args:
            context: The prediction context for this request, used only
                for logging.
            prediction_engine_result: The completed PREDICTION_ENGINE
                stage output, or `None` when that stage was skipped.
            ensemble_result: The completed ENSEMBLE stage output, or
                `None` when that stage was skipped or halted.

        Returns:
            The `FinalPredictionResult` for this request, or `None` when
            this step was skipped.

        Raises:
            app.services.prediction_exceptions.EnsembleUnavailableError:
                If any of the three chained collaborators rejects its
                input as structurally invalid, or if `calculate_votes`
                cannot resolve a participating model's manifest entry
                (`app.ml.exceptions.ModelNotFoundError`) while reading
                its `ensemble_weight` or class label space (ADR-006).
        """
        if (
            self._voting_engine is None
            or self._calibration_engine is None
            or self._final_prediction_builder is None
        ):
            logger.info(
                "Final prediction step skipped: request_id=%s reason=%s",
                context.request_id,
                "Final Prediction Builder integration is introduced in Phase 4.7.4.2.",
            )
            return None

        if prediction_engine_result is None or ensemble_result is None:
            logger.info(
                "Final prediction step skipped: request_id=%s reason=%s",
                context.request_id,
                "Final Prediction Builder requires a completed ENSEMBLE stage.",
            )
            return None

        logger.info("Final prediction building started: request_id=%s", context.request_id)

        try:
            voting_result = self._voting_engine.calculate_votes(prediction_engine_result)
            calibrated_result = self._calibration_engine.calibrate(voting_result)
            final_result = self._final_prediction_builder.build(calibrated_result)
        except (
            InvalidEnsembleInputError,
            EnsembleConfigurationError,
            ModelNotFoundError,
        ) as exc:
            logger.warning(
                "Prediction halted at final-prediction step: request_id=%s reason=%s",
                context.request_id,
                exc.message,
            )
            raise EnsembleUnavailableError(message=exc.message) from exc

        logger.info(
            "Final prediction generated: request_id=%s predicted_class=%s "
            "final_confidence=%.4f agreement_ratio=%.4f",
            context.request_id,
            final_result.predicted_class,
            final_result.confidence,
            final_result.agreement_ratio,
        )
        logger.info(
            "Predicted class: request_id=%s predicted_class=%s",
            context.request_id,
            final_result.predicted_class,
        )
        logger.info(
            "Final confidence: request_id=%s final_confidence=%.4f",
            context.request_id,
            final_result.confidence,
        )
        logger.info(
            "Agreement ratio: request_id=%s agreement_ratio=%.4f",
            context.request_id,
            final_result.agreement_ratio,
        )

        return final_result

    async def _execute_response_stage(
        self,
        context: PredictionContext,
        final_prediction_result: FinalPredictionResult | None,
        stages: list[PipelineStageRecord],
    ) -> PredictionResponseResult | None:
        """Run the RESPONSE pipeline stage for real (Phase 4.8.2, ADR-028).

        Delegates to `PredictionResponseBuilder.build()` (Phase 4.8.1),
        which copies the completed FINAL_PREDICTION step's
        `FinalPredictionResult` into a standardized
        `PredictionResponseResult` -- performing NO additional
        calculations, confidence modification, agreement recalculation,
        or runtime statistics attachment (ADR-028). This stage never
        communicates with `AIRuntimeManager`, `PredictionEngine`, the
        Adaptive Ensemble Engine, or TensorFlow models; it consumes only
        the already-completed `FinalPredictionResult`.

        Falls back to the Phase 4.4 skipped placeholder when no
        `PredictionResponseBuilder` was injected, or when the internal
        FINAL_PREDICTION step did not complete (so this stage never runs
        ahead of the `FinalPredictionResult` it depends on) --preserving
        backward compatibility for callers that construct
        `PredictionService` without this collaborator.

        Args:
            context: The prediction context for this request, used only
                for logging.
            final_prediction_result: The completed internal
                FINAL_PREDICTION step output, or `None` when that step
                was skipped.
            stages: The in-progress pipeline stage list; the RESPONSE
                stage's outcome is appended to it.

        Returns:
            The `PredictionResponseResult` for this request, or `None`
            when this stage was skipped.

        Raises:
            app.services.prediction_exceptions.ResponseBuildError: If
                `PredictionResponseBuilder` rejects `final_prediction_result`
                as structurally invalid. Not expected to be reachable in
                normal operation, since the FINAL_PREDICTION step already
                validated its own output before this stage runs.
        """
        if self._response_builder is None:
            skipped_record = self._skip_stage(
                PipelineStageName.RESPONSE,
                "Response Builder integration is introduced in Phase 4.8.2.",
            )
            stages.append(skipped_record)
            return None

        if final_prediction_result is None:
            skipped_record = self._skip_stage(
                PipelineStageName.RESPONSE,
                "The Response Builder requires a completed FINAL_PREDICTION step.",
            )
            stages.append(skipped_record)
            return None

        self._enter_stage(PipelineStageName.RESPONSE)
        logger.info("Response building started: request_id=%s", context.request_id)

        try:
            response_result = self._response_builder.build(final_prediction_result)
        except InvalidResponseInputError as exc:
            logger.warning(
                "Prediction halted at response stage: request_id=%s reason=%s",
                context.request_id,
                exc.message,
            )
            raise ResponseBuildError(message=exc.message) from exc

        logger.info(
            "Prediction response generated: request_id=%s predicted_class=%s "
            "confidence=%.4f agreement_ratio=%.4f participating_models=%d",
            context.request_id,
            response_result.predicted_class,
            response_result.confidence,
            response_result.agreement_ratio,
            response_result.participating_models,
        )
        stages.append(
            PipelineStageRecord(
                name=PipelineStageName.RESPONSE,
                status=PipelineStageStatus.COMPLETED,
                detail=(
                    f"Prediction Response Builder integration completed (ADR-028): "
                    f"predicted_class={response_result.predicted_class}, "
                    f"confidence={response_result.confidence:.2f}%, "
                    f"agreement_ratio={response_result.agreement_ratio:.4f}."
                ),
            )
        )

        return response_result

    async def _execute_history_stage(
        self,
        context: PredictionContext,
        stages: list[PipelineStageRecord],
        response_result: PredictionResponseResult | None,
        individual_model_results: list | None,
        execution_stats: object | None,
        runtime_metadata: RuntimeMetadata | None,
        history_service: PredictionHistoryService | None,
    ) -> str | None:
        """Run the HISTORY pipeline stage for real (Phase 5.2, ADR-033).

        Per ADR-032/ADR-033, Prediction History remains completely
        independent from the Prediction Engine: this stage performs NO
        inference, NO ensemble voting, and NO confidence recalculation --
        it only builds a `PredictionHistory` record from already-computed
        pipeline outputs (via `PredictionHistoryService.prepare_history_record`,
        which delegates entirely to `PredictionHistoryMapper`) and persists
        it (via `PredictionHistoryService.persist`).

        This stage is skipped -- and `PredictionResult.history_reference`
        stays `None` -- whenever:
            - No `history_service` was supplied for this call (backward
              compatible with callers that construct/call this service
              without Prediction History wired in).
            - `PredictionOptions.save_history` is `false` for this request
              (ADR-033's `save_history` gate).

        Per ADR-033, a persistence failure must never fail the originating
        prediction request: any exception raised while preparing or
        persisting the history record is caught, logged, and recorded as
        a skipped HISTORY stage -- the already-completed `response_result`
        is still returned to the caller unchanged.

        Args:
            context: The prediction context for this request.
            stages: The in-progress pipeline stage list; the HISTORY
                stage's outcome is appended to it.
            response_result: The completed RESPONSE stage output, or
                `None` when that stage did not complete.
            individual_model_results: The completed PREDICTION_ENGINE
                stage's per-model predictions, or `None`.
            execution_stats: The completed PREDICTION_ENGINE stage's
                aggregate execution statistics, or `None`.
            runtime_metadata: The completed RUNTIME stage's metadata
                snapshot, or `None`.
            history_service: The request-scoped `PredictionHistoryService`
                to persist with, or `None` to skip this stage entirely.

        Returns:
            The persisted record's `history_id`, or `None` when this
            stage was skipped or failed.
        """
        if history_service is None:
            stages.append(
                self._skip_stage(
                    PipelineStageName.HISTORY,
                    "Prediction History persistence is not configured for this "
                    "service instance.",
                )
            )
            return None

        if not context.options.save_history:
            stages.append(
                self._skip_stage(
                    PipelineStageName.HISTORY,
                    "Prediction history persistence skipped: the save_history "
                    "request option is false.",
                )
            )
            return None

        self._enter_stage(PipelineStageName.HISTORY)
        logger.info("Prediction history persistence started: request_id=%s", context.request_id)

        # A snapshot of this request's outcome, built solely so the
        # Prediction History Mapper (ADR-032) has the `PredictionResult`
        # shape it expects. Never returned to the caller -- the actual
        # `PredictionResult` returned by `predict()` is built separately,
        # once this stage's own outcome is known.
        history_snapshot = PredictionResult(
            request_id=context.request_id,
            requested_at=context.requested_at,
            message="Prediction history snapshot (internal, not returned to callers).",
            stages=list(stages),
            response_result=response_result,
            individual_model_results=individual_model_results,
            execution_stats=execution_stats,
            runtime_statistics=runtime_metadata,
        )

        try:
            history = history_service.prepare_history_record(
                prediction_result=history_snapshot, context=context
            )
            await history_service.persist(history)
        except PredictionHistoryError as exc:
            logger.error(
                "Prediction history persistence failed and was skipped: "
                "request_id=%s reason=%s",
                context.request_id,
                exc.message,
            )
            stages.append(
                self._skip_stage(
                    PipelineStageName.HISTORY,
                    "Prediction history persistence failed; see server logs. "
                    "The prediction response is unaffected (ADR-033).",
                )
            )
            return None
        except Exception:
            # Defense in depth: per ADR-033, no history failure -- of any
            # kind -- may ever fail the originating prediction request.
            logger.exception(
                "Unexpected error during Prediction History persistence: request_id=%s",
                context.request_id,
            )
            stages.append(
                self._skip_stage(
                    PipelineStageName.HISTORY,
                    "Prediction history persistence failed unexpectedly; see "
                    "server logs. The prediction response is unaffected (ADR-033).",
                )
            )
            return None

        logger.info(
            "Prediction history persisted: request_id=%s history_id=%s status=%s",
            context.request_id,
            history.history_id,
            history.status.value,
        )
        stages.append(
            PipelineStageRecord(
                name=PipelineStageName.HISTORY,
                status=PipelineStageStatus.COMPLETED,
                detail=(
                    f"Prediction history record persisted (ADR-033): "
                    f"history_id={history.history_id}, status={history.status.value}."
                ),
            )
        )

        return history.history_id

    def _enter_stage(self, name: PipelineStageName) -> None:
        """Log entry into a pipeline stage before it is attempted."""
        logger.info("Pipeline stage entered: %s", name.value)

    def _skip_stage(self, name: PipelineStageName, reason: str) -> PipelineStageRecord:
        """Log and record a pipeline stage that is not yet connected.

        Args:
            name: The pipeline stage being skipped.
            reason: Human-readable explanation of why the stage is skipped.
        """
        self._enter_stage(name)
        logger.info("Pipeline stage skipped: %s (%s)", name.value, reason)
        return PipelineStageRecord(
            name=name,
            status=PipelineStageStatus.SKIPPED,
            detail=reason,
        )
