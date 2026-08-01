"""Centralized Prediction Engine (ADR-008).

Produces one individual prediction per currently loaded model for a
single uploaded image. The Prediction Engine never performs ensemble
voting; the Adaptive Ensemble Engine (a future phase) is the sole
consumer of the individual predictions returned here.

Per ADR-007, this engine never communicates with TensorFlow directly. It
obtains loaded model instances only through the `AIRuntimeManager`, and
model metadata only through the `ModelRegistry`.

`predict_single_model()` (Phase 4.6.3, ADR-020) restricted inference to
the single highest-priority production model. `predict_multi_model()`
(Phase 4.6.4, ADR-021) is the entry point `PredictionService` currently
calls: it extends the same fault-tolerant per-model execution to every
currently loaded production model, attempted sequentially in ascending
Model Manifest loading priority order. Neither method performs ensemble
voting; that remains the Adaptive Ensemble Engine's responsibility
(Phase 4.7, ADR-008/ADR-009).
"""

import time
from typing import Iterable

import numpy as np
from PIL import Image

from app.core.logging import get_logger
from app.ml.prediction.exceptions import NoModelsAvailableError, PredictionExecutionError
from app.ml.prediction.prediction_result import (
    FailedModelPrediction,
    IndividualPrediction,
    PredictionEngineResult,
    PredictionExecutionStats,
)
from app.ml.prediction.predictor import ModelPredictor
from app.ml.prediction.prediction_request import PredictionRequest
from app.ml.prediction.preprocessor import ImagePreprocessor
from app.ml.prediction.validator import ImageValidator
from app.ml.registry.model_registry import ModelRegistry
from app.ml.runtime.runtime_manager import AIRuntimeManager
from app.ml.schemas import ModelManifestEntry

logger = get_logger(__name__)

SINGLE_MODEL_LOADING_PRIORITY = 1
"""Model Manifest loading priority (ADR-006) resolved for Phase 4.6.3's
single-model inference (ADR-020). Matches the first entry in the Hybrid
Loading Strategy's startup sequence (Project Context, Section 14) --
currently MobileNetV2 -- so the executed model is always resolved from
the manifest rather than a hardcoded model ID.
"""


class PredictionEngine:
    """Produces individual model predictions for a single uploaded image.

    Responsibilities: image validation, image preprocessing, and per-model
    inference orchestration via the AI Runtime Manager. Ensemble voting is
    explicitly out of scope (ADR-008) and is never performed here.
    """

    def __init__(
        self,
        runtime_manager: AIRuntimeManager,
        registry: ModelRegistry,
        validator: ImageValidator | None = None,
        preprocessor: ImagePreprocessor | None = None,
        predictor: ModelPredictor | None = None,
    ) -> None:
        self._runtime_manager = runtime_manager
        self._registry = registry
        self._validator = validator or ImageValidator()
        self._preprocessor = preprocessor or ImagePreprocessor()
        self._predictor = predictor or ModelPredictor()

    async def predict(self, image_bytes: bytes) -> PredictionEngineResult:
        """Validate, preprocess, and run inference across every loaded model.

        Every loaded model is attempted independently; a single model's
        preprocessing or inference failure never stops the remaining
        models from being attempted (fault tolerance, see ADR-005/ADR-007).

        Raises:
            ImageValidationError: If the uploaded image fails validation.
            NoModelsAvailableError: If no models are currently loaded.
        """
        request_started_at = time.perf_counter()

        image = self._validator.validate(image_bytes)

        loaded_models = await self._runtime_manager.get_loaded_models()
        if not loaded_models:
            raise NoModelsAvailableError()

        entries_by_id = {
            model_id: self._registry.get_model_by_id(model_id) for model_id in loaded_models
        }

        preprocessing_started_at = time.perf_counter()
        tensors_by_input_size = self._preprocess_for_all_sizes(image, entries_by_id.values())
        preprocessing_time_ms = round(
            (time.perf_counter() - preprocessing_started_at) * 1000, 2
        )

        predictions: list[IndividualPrediction] = []
        failed_models: list[FailedModelPrediction] = []
        total_inference_time_ms = 0.0

        for model_id, model_instance in loaded_models.items():
            entry = entries_by_id[model_id]
            input_tensor = tensors_by_input_size[entry.input_size]

            try:
                prediction = await self._predictor.predict(entry, model_instance, input_tensor)
            except PredictionExecutionError as exc:
                logger.warning(
                    "Model '%s' failed to produce a prediction: %s", model_id, exc.message
                )
                failed_models.append(
                    FailedModelPrediction(
                        model_id=entry.id,
                        model_name=entry.display_name,
                        failure_reason=exc.message,
                    )
                )
                continue

            predictions.append(prediction)
            total_inference_time_ms += prediction.inference_time_ms

        total_execution_time_ms = round((time.perf_counter() - request_started_at) * 1000, 2)

        execution_stats = PredictionExecutionStats(
            total_models_attempted=len(loaded_models),
            successful_predictions=len(predictions),
            failed_predictions=len(failed_models),
            preprocessing_time_ms=preprocessing_time_ms,
            total_inference_time_ms=round(total_inference_time_ms, 2),
            total_execution_time_ms=total_execution_time_ms,
        )

        return PredictionEngineResult(
            predictions=predictions,
            failed_models=failed_models,
            execution_stats=execution_stats,
        )

    async def predict_single_model(
        self, prediction_request: PredictionRequest
    ) -> PredictionEngineResult:
        """Execute inference using only the single highest-priority production model (ADR-020).

        Phase 4.6.3 intentionally restricts inference to one model --
        currently MobileNetV2, resolved from the Model Manifest via
        `SINGLE_MODEL_LOADING_PRIORITY` rather than a hardcoded model ID --
        ahead of Phase 4.6.4's sequential multi-model execution and Phase
        4.7's Adaptive Ensemble Engine. No ensemble voting is performed
        here (ADR-008).

        Unlike `predict()`, this method never re-validates or
        re-preprocesses the uploaded image: it consumes the already
        validated, already preprocessed tensor carried on
        `prediction_request` (ADR-019), which `ImagePreprocessor` sized
        for this exact model (ADR-018's priority-based input size
        resolution).

        Per ADR-007, the model instance is obtained exclusively through
        `AIRuntimeManager.get_model()`; this method never instantiates,
        loads, or unloads a TensorFlow model itself.

        Args:
            prediction_request: The standardized `PredictionRequest` built
                by `PredictionRequestBuilder`, already carrying a
                preprocessed tensor sized for this model.

        Returns:
            A `PredictionEngineResult` containing either the single
            successful `IndividualPrediction`, or a single
            `FailedModelPrediction`, produced for this request.

        Raises:
            app.ml.exceptions.ModelNotFoundError: If the resolved model is
                not registered in the Model Manifest.
            app.ml.runtime.exceptions.RuntimeNotInitializedError: If the AI
                Runtime has not finished its startup loading sequence.
            app.ml.runtime.exceptions.ModelUnavailableError: If the
                resolved model is disabled, or fails to load.
        """
        request_started_at = time.perf_counter()

        entry = self._registry.get_model_by_priority(SINGLE_MODEL_LOADING_PRIORITY)
        logger.info("Single-model inference started: model_id=%s", entry.id)

        model_instance = await self._runtime_manager.get_model(entry.id)
        logger.info(
            "Model selected for inference: model_id=%s model_name=%s version=%s",
            entry.id,
            entry.display_name,
            entry.version,
        )

        input_tensor = prediction_request.processed_tensor

        predictions: list[IndividualPrediction] = []
        failed_models: list[FailedModelPrediction] = []

        try:
            prediction = await self._predictor.predict(entry, model_instance, input_tensor)
        except PredictionExecutionError as exc:
            logger.error(
                "Single-model inference failed: model_id=%s reason=%s", entry.id, exc.message
            )
            failed_models.append(
                FailedModelPrediction(
                    model_id=entry.id,
                    model_name=entry.display_name,
                    failure_reason=exc.message,
                )
            )
        else:
            predictions.append(prediction)
            logger.info(
                "Single-model inference completed: model_id=%s prediction=%s "
                "confidence=%.2f%% inference_time_ms=%.2f",
                entry.id,
                prediction.predicted_label,
                prediction.confidence.confidence_percentage,
                prediction.inference_time_ms,
            )

        total_execution_time_ms = round((time.perf_counter() - request_started_at) * 1000, 2)
        total_inference_time_ms = predictions[0].inference_time_ms if predictions else 0.0

        execution_stats = PredictionExecutionStats(
            total_models_attempted=1,
            successful_predictions=len(predictions),
            failed_predictions=len(failed_models),
            # Preprocessing already ran upstream as its own pipeline stage
            # (Phase 4.6.1, ADR-018) against `prediction_request`; it is
            # never repeated here.
            preprocessing_time_ms=0.0,
            total_inference_time_ms=round(total_inference_time_ms, 2),
            total_execution_time_ms=total_execution_time_ms,
        )

        return PredictionEngineResult(
            predictions=predictions,
            failed_models=failed_models,
            execution_stats=execution_stats,
        )

    async def predict_multi_model(
        self, prediction_request: PredictionRequest
    ) -> PredictionEngineResult:
        """Execute every currently loaded production model sequentially (ADR-021, Phase 4.6.4).

        Extends Phase 4.6.3's single-model inference (ADR-020) to the full
        Hybrid Loading Strategy: every production model the AI Runtime
        Manager currently reports as loaded is attempted, in ascending
        Model Manifest loading priority order (Project Context, Section
        14; ADR-021):

            1. MobileNetV2
            2. DenseNet121
            3. EfficientNetV2B0 + ResNet50 Feature Fusion

        Execution order is always resolved from the Model Manifest via
        `ModelRegistry.get_enabled_models_ordered_by_priority()`, never
        hardcoded. A model that is not currently loaded (for example a
        lazily-loaded model that has not yet been triggered) is skipped
        rather than force-loaded here: lazy loading remains the AI
        Runtime Manager's responsibility alone (ADR-007). A single
        model's inference failure never stops the remaining models from
        being attempted (ADR-005/ADR-021): fault tolerance is preserved
        by catching `PredictionExecutionError` per model and recording a
        `FailedModelPrediction` instead of raising. Prediction continues
        as long as at least one model executes successfully; this method
        never raises when every model fails -- it returns an empty
        `predictions` list and lets the caller (`PredictionService`)
        decide how to respond.

        No ensemble voting, agreement calculation, or final-prediction
        selection is performed here (ADR-008); the Adaptive Ensemble
        Engine (Phase 4.7) is the sole consumer of the individual
        predictions returned by this method.

        Unlike `predict()`, this method never re-validates or
        re-preprocesses the uploaded image: like `predict_single_model()`,
        it consumes the already validated, already preprocessed tensor
        carried on `prediction_request` (ADR-019). Every currently
        registered production model shares the same Model Manifest
        `input_size` today, so the same tensor is reused for every model;
        a model whose manifest `input_size` ever diverges from the tensor
        `prediction_request` was preprocessed for is skipped and recorded
        as a failed model, rather than passed a mismatched tensor.

        Args:
            prediction_request: The standardized `PredictionRequest` built
                by `PredictionRequestBuilder`, already carrying a
                preprocessed tensor and the current AI Runtime metadata
                snapshot.

        Returns:
            A `PredictionEngineResult` containing one `IndividualPrediction`
            per successfully executed model (in execution order), one
            `FailedModelPrediction` per model that was attempted but
            failed (or skipped due to an input-size mismatch), and
            aggregate execution statistics.

        Raises:
            NoModelsAvailableError: If the AI Runtime Manager currently
                reports zero loaded models.
        """
        request_started_at = time.perf_counter()

        loaded_models = await self._runtime_manager.get_loaded_models()
        if not loaded_models:
            raise NoModelsAvailableError()

        ordered_entries = self._registry.get_enabled_models_ordered_by_priority()
        input_tensor = prediction_request.processed_tensor
        preprocessed_input_size = prediction_request.preprocessing_result.input_size

        logger.info(
            "Sequential multi-model execution started: request_id=%s loaded_model_count=%d "
            "candidate_model_count=%d",
            prediction_request.request_id,
            len(loaded_models),
            len(ordered_entries),
        )

        predictions: list[IndividualPrediction] = []
        failed_models: list[FailedModelPrediction] = []
        total_inference_time_ms = 0.0

        for entry in ordered_entries:
            if entry.id not in loaded_models:
                logger.info(
                    "Model skipped (not currently loaded): model_id=%s priority=%d",
                    entry.id,
                    entry.priority,
                )
                continue

            logger.info(
                "Model selected for inference: model_id=%s model_name=%s version=%s priority=%d",
                entry.id,
                entry.display_name,
                entry.version,
                entry.priority,
            )

            if entry.input_size != preprocessed_input_size:
                mismatch_reason = (
                    f"Model '{entry.id}' requires input size {entry.input_size}, but this "
                    f"request was preprocessed for input size {preprocessed_input_size}."
                )
                logger.warning(
                    "Model skipped (input size mismatch): model_id=%s reason=%s",
                    entry.id,
                    mismatch_reason,
                )
                failed_models.append(
                    FailedModelPrediction(
                        model_id=entry.id,
                        model_name=entry.display_name,
                        failure_reason=mismatch_reason,
                    )
                )
                continue

            model_instance = loaded_models[entry.id]

            try:
                prediction = await self._predictor.predict(entry, model_instance, input_tensor)
            except PredictionExecutionError as exc:
                logger.warning(
                    "Inference failed: model_id=%s reason=%s", entry.id, exc.message
                )
                failed_models.append(
                    FailedModelPrediction(
                        model_id=entry.id,
                        model_name=entry.display_name,
                        failure_reason=exc.message,
                    )
                )
                continue

            logger.info(
                "Inference completed: model_id=%s prediction=%s confidence=%.2f%% "
                "inference_time_ms=%.2f",
                entry.id,
                prediction.predicted_label,
                prediction.confidence.confidence_percentage,
                prediction.inference_time_ms,
            )
            predictions.append(prediction)
            total_inference_time_ms += prediction.inference_time_ms

        total_execution_time_ms = round((time.perf_counter() - request_started_at) * 1000, 2)

        execution_stats = PredictionExecutionStats(
            total_models_attempted=len(predictions) + len(failed_models),
            successful_predictions=len(predictions),
            failed_predictions=len(failed_models),
            # Preprocessing already ran upstream as its own pipeline stage
            # (Phase 4.6.1, ADR-018) against `prediction_request`; it is
            # never repeated here.
            preprocessing_time_ms=0.0,
            total_inference_time_ms=round(total_inference_time_ms, 2),
            total_execution_time_ms=total_execution_time_ms,
        )

        logger.info(
            "Sequential multi-model execution completed: request_id=%s executed_model_count=%d "
            "failed_model_count=%d total_execution_time_ms=%.2f",
            prediction_request.request_id,
            len(predictions),
            len(failed_models),
            total_execution_time_ms,
        )

        return PredictionEngineResult(
            predictions=predictions,
            failed_models=failed_models,
            execution_stats=execution_stats,
        )

    def _preprocess_for_all_sizes(
        self, image: Image.Image, entries: Iterable[ModelManifestEntry]
    ) -> dict[int, np.ndarray]:
        """Preprocess `image` once per distinct input size required by loaded models.

        Multiple models frequently share the same manifest-defined input
        size, so preprocessing is de-duplicated by size rather than
        repeated once per model.
        """
        distinct_sizes = {entry.input_size for entry in entries}
        return {size: self._preprocessor.preprocess(image, size) for size in distinct_sizes}
