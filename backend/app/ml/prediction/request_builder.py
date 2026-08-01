"""Prediction Request Builder (ADR-019, Phase 4.6.2).

`PredictionRequestBuilder` is the single reusable place a `PredictionRequest`
(see `app.ml.prediction.prediction_request`) is assembled from the outputs
already produced by the PREPROCESSING stage (`PreprocessingResult`,
ADR-018) and the RUNTIME stage (`RuntimeValidationResult`,
`RuntimeMetadata`; ADR-015/ADR-016), plus the validated per-request options
and the authenticated user.

This module performs NO AI inference, NO image preprocessing, and never
calls the AI Runtime Manager, the Prediction Engine, or the Adaptive
Ensemble Engine -- it only validates and recombines objects those earlier
stages already produced.

`PredictionService` must delegate every `PredictionRequest` construction to
this builder rather than assembling one inline (see Backend Progress,
Phase 4.6.2).

Future prediction phases reuse this same module without change:
    - Phase 4.6.3 (Single Model Inference) consumes the returned
      `PredictionRequest` as the Prediction Engine's only input.
"""

from typing import Any

from app.core.logging import get_logger
from app.ml.prediction.exceptions import (
    MissingPreprocessingResultError,
    MissingProcessedTensorError,
    MissingRuntimeMetadataError,
    MissingRuntimeValidationError,
    NoLoadedModelsForRequestError,
    PreprocessingNotSuccessfulError,
    RuntimeValidationNotPassedError,
)
from app.ml.prediction.prediction_request import PredictionRequest
from app.ml.prediction.request_metadata import (
    PredictionConfiguration,
    PredictionRequestOptions,
    UserContext,
)
from app.ml.preprocessing.preprocessing_result import PreprocessingResult
from app.utils.environment import get_current_timestamp

logger = get_logger(__name__)


class PredictionRequestBuilder:
    """Builds a standardized `PredictionRequest` for a single prediction call (ADR-019).

    Stateless and side-effect free: performs no AI inference, no I/O, and
    never touches the AI Runtime Manager, Prediction Engine, or Adaptive
    Ensemble Engine. Every input is already-computed output from an earlier
    pipeline stage; this class only validates and recombines it.
    """

    def build(
        self,
        request_id: str,
        preprocessing_result: PreprocessingResult | None,
        runtime_validation: Any,
        runtime_metadata: Any,
        request_options: Any,
        current_user: Any,
    ) -> PredictionRequest:
        """Assemble a complete, validated `PredictionRequest`.

        Args:
            request_id: The pipeline's request identifier for this request
                (shared with every other pipeline stage; never regenerated
                here).
            preprocessing_result: The completed PREPROCESSING stage outcome
                (`app.ml.preprocessing.preprocessing_result.PreprocessingResult`).
            runtime_validation: The completed RUNTIME stage's validation
                outcome (`app.services.runtime_validator.RuntimeValidationResult`).
            runtime_metadata: The completed RUNTIME stage's metadata
                snapshot (`app.services.runtime_metadata.RuntimeMetadata`).
            request_options: The validated per-request control flags
                (`app.services.prediction_context.PredictionOptions`).
            current_user: The authenticated user submitting this request
                (`app.models.user.User`).

        Returns:
            A fully validated `PredictionRequest`, ready to be handed to
            the Prediction Engine (Phase 4.6.3 onward). No inference is
            performed by this method.

        Raises:
            MissingPreprocessingResultError: No `PreprocessingResult` was supplied.
            PreprocessingNotSuccessfulError: The supplied `PreprocessingResult` did not succeed.
            MissingProcessedTensorError: The supplied `PreprocessingResult` has no processed tensor.
            MissingRuntimeMetadataError: No runtime metadata snapshot was supplied.
            MissingRuntimeValidationError: No runtime validation outcome was supplied.
            RuntimeValidationNotPassedError: The supplied runtime validation outcome did not pass.
            NoLoadedModelsForRequestError: The runtime validation outcome reports zero loaded models.
        """
        logger.info("Prediction request creation started: request_id=%s", request_id)

        self._validate_preprocessing(preprocessing_result)
        self._validate_runtime(runtime_validation=runtime_validation, runtime_metadata=runtime_metadata)

        options = PredictionRequestOptions.from_source(request_options)
        user_context = UserContext.from_source(current_user)
        configuration = PredictionConfiguration.build(
            options=options,
            runtime_metadata=runtime_metadata,
            runtime_validation=runtime_validation,
        )

        prediction_request = PredictionRequest(
            request_id=request_id,
            request_timestamp=get_current_timestamp(),
            processed_tensor=preprocessing_result.processed_tensor,
            preprocessing_result=preprocessing_result,
            runtime_metadata=runtime_metadata,
            request_options=options,
            user_context=user_context,
            prediction_configuration=configuration,
        )

        logger.info(
            "Prediction request created: request_id=%s loaded_model_count=%d",
            request_id,
            configuration.loaded_model_count,
        )
        return prediction_request

    def _validate_preprocessing(self, preprocessing_result: PreprocessingResult | None) -> None:
        """Validate the PREPROCESSING stage outcome before building a request.

        Raises:
            MissingPreprocessingResultError: No `PreprocessingResult` was supplied.
            PreprocessingNotSuccessfulError: Preprocessing did not succeed.
            MissingProcessedTensorError: No processed tensor is present.
        """
        if preprocessing_result is None:
            raise MissingPreprocessingResultError()

        if not getattr(preprocessing_result, "preprocessing_success", False):
            raise PreprocessingNotSuccessfulError()

        if getattr(preprocessing_result, "processed_tensor", None) is None:
            raise MissingProcessedTensorError()

    def _validate_runtime(self, runtime_validation: Any, runtime_metadata: Any) -> None:
        """Validate the RUNTIME stage outcome before building a request.

        Raises:
            MissingRuntimeMetadataError: No runtime metadata snapshot was supplied.
            MissingRuntimeValidationError: No runtime validation outcome was supplied.
            RuntimeValidationNotPassedError: Runtime validation did not pass.
            NoLoadedModelsForRequestError: Zero models are currently loaded.
        """
        if runtime_metadata is None:
            raise MissingRuntimeMetadataError()

        if runtime_validation is None:
            raise MissingRuntimeValidationError()

        if not getattr(runtime_validation, "is_valid", False):
            raise RuntimeValidationNotPassedError()

        if getattr(runtime_validation, "loaded_model_count", 0) <= 0:
            raise NoLoadedModelsForRequestError()
