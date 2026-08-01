"""Prediction pipeline exceptions (Phase 4.4 - forward declarations, ADR-013).

Phase 4.4 introduces only the prediction orchestration skeleton; no stage
downstream of centralized upload validation (ADR-011) executes yet, so
none of these exceptions are raised anywhere in this phase. They are
declared now so later phases (Phase 4.5 - AI Runtime integration onward)
can raise them without introducing a new exception module or changing
`PredictionService`'s public surface.

Each extends the application's centralized `OncoVisionError` so it is
handled automatically by the existing global exception handlers
(`app.core.exceptions`) and never leaks internal details to API clients.

These are distinct from `app.api.v1.predictions.exceptions`, which cover
centralized upload validation failures (ADR-011) that occur earlier in
the pipeline, before a `PredictionContext` even exists.
"""

from fastapi import status

from app.core.exceptions import OncoVisionError


class PredictionPipelineError(OncoVisionError):
    """Base exception for failures occurring inside the prediction pipeline."""

    def __init__(
        self,
        message: str = "The prediction pipeline failed to process this request.",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    ) -> None:
        super().__init__(message=message, status_code=status_code)


class RuntimeUnavailableError(PredictionPipelineError):
    """Reserved for Phase 4.5 (Runtime Integration).

    Raised when the AI Runtime Manager has no production models
    available to serve a prediction request.
    """

    def __init__(
        self, message: str = "No AI models are currently available to serve predictions."
    ) -> None:
        super().__init__(message=message, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)


class PredictionEngineExecutionError(PredictionPipelineError):
    """Reserved for Phase 4.6 (Prediction Engine Integration).

    Raised when the Prediction Engine fails to produce a result for
    every loaded model.
    """

    def __init__(
        self, message: str = "Prediction Engine inference failed for all loaded models."
    ) -> None:
        super().__init__(message=message)


class EnsembleUnavailableError(PredictionPipelineError):
    """Reserved for Phase 4.7 (Ensemble Integration).

    Raised when the Adaptive Ensemble Engine cannot produce a final
    prediction result from the available individual model predictions.
    """

    def __init__(
        self,
        message: str = "The Adaptive Ensemble Engine could not produce a prediction result.",
    ) -> None:
        super().__init__(message=message, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)


class ResponseBuildError(PredictionPipelineError):
    """Phase 4.8.2 (PredictionService Response Integration, ADR-028).

    Raised when `PredictionResponseBuilder` rejects its input as
    structurally invalid. Not expected to be reachable in normal
    operation, since the FINAL_PREDICTION step already validated
    `final_prediction_result` before this stage runs.
    """

    def __init__(
        self,
        message: str = "The Response Builder could not produce a prediction response.",
    ) -> None:
        super().__init__(message=message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RuntimeNotInitializedError(PredictionPipelineError):
    """Phase 4.5.2 (Runtime Validation, ADR-015).

    Raised when a prediction request arrives before the AI Runtime
    Manager has completed its startup loading sequence.
    """

    def __init__(
        self, message: str = "The AI runtime has not finished initializing yet."
    ) -> None:
        super().__init__(message=message, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)


class NoLoadedModelsError(PredictionPipelineError):
    """Phase 4.5.2 (Runtime Validation, ADR-015).

    Raised when the AI Runtime Manager has completed initialization but
    zero models are currently in the READY state. Distinct from
    `RuntimeUnavailableError`, which covers runtime-unavailability outcomes
    other than a plain zero-loaded-model count.
    """

    def __init__(
        self,
        message: str = "No AI models are currently loaded and ready to serve predictions.",
    ) -> None:
        super().__init__(message=message, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)


class RuntimeValidationFailedError(PredictionPipelineError):
    """Phase 4.5.2 (Runtime Validation, ADR-015).

    Raised when runtime validation itself cannot be completed due to an
    unexpected error (e.g. a `RuntimeAdapter` collaborator failure),
    rather than a determinate runtime-state outcome.
    """

    def __init__(self, message: str = "Runtime validation could not be completed.") -> None:
        super().__init__(message=message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RuntimeMetadataCollectionFailedError(PredictionPipelineError):
    """Phase 4.5.3 (Runtime Metadata, ADR-016).

    Raised when `RuntimeMetadataService` cannot assemble a
    `RuntimeMetadata` snapshot due to an unexpected error (e.g. a
    `RuntimeAdapter` collaborator failure), rather than a normal absence
    of loaded, failed, or lazy models -- which is a valid metadata
    snapshot, not an error.
    """

    def __init__(
        self, message: str = "Runtime metadata could not be collected."
    ) -> None:
        super().__init__(message=message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
