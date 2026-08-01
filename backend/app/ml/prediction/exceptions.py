"""Prediction Engine exceptions.

These extend the application's centralized `OncoVisionError` so they are
automatically handled by the existing global exception handlers and never
leak internal details (paths, stack traces, etc.) to API clients.
"""

from fastapi import status

from app.core.exceptions import OncoVisionError


class ImageValidationError(OncoVisionError):
    """Base exception for uploaded image validation failures."""

    def __init__(self, message: str = "The uploaded image is invalid.") -> None:
        super().__init__(message=message, status_code=status.HTTP_400_BAD_REQUEST)


class EmptyUploadError(ImageValidationError):
    """Raised when the uploaded image file contains no data."""

    def __init__(self, message: str = "The uploaded file is empty.") -> None:
        super().__init__(message=message)


class ImageTooLargeError(ImageValidationError):
    """Raised when the uploaded image exceeds the maximum allowed file size."""

    def __init__(
        self, message: str = "The uploaded image exceeds the maximum allowed file size."
    ) -> None:
        super().__init__(message=message)


class UnsupportedImageFormatError(ImageValidationError):
    """Raised when the uploaded image format is not supported."""

    def __init__(self, message: str = "The uploaded image format is not supported.") -> None:
        super().__init__(message=message)


class CorruptedImageError(ImageValidationError):
    """Raised when the uploaded image cannot be read or decoded."""

    def __init__(
        self, message: str = "The uploaded image is corrupted or unreadable."
    ) -> None:
        super().__init__(message=message)


class ImageResolutionError(ImageValidationError):
    """Raised when the uploaded image resolution is outside the allowed range."""

    def __init__(
        self, message: str = "The uploaded image resolution is not within the allowed range."
    ) -> None:
        super().__init__(message=message)


class NoModelsAvailableError(OncoVisionError):
    """Raised when no AI models are currently loaded and available for prediction."""

    def __init__(
        self,
        message: str = "No AI models are currently available to perform a prediction.",
    ) -> None:
        super().__init__(message=message, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)


class PredictionExecutionError(OncoVisionError):
    """Raised when a single model fails during preprocessing or inference.

    Always caught internally by `PredictionEngine` and recorded as a failed
    model entry so the rest of the loaded models can still be attempted;
    never expected to propagate to an API client directly.
    """

    def __init__(self, message: str = "Model prediction failed.") -> None:
        super().__init__(message=message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PredictionRequestBuildError(OncoVisionError):
    """Base exception for `PredictionRequestBuilder` failures (ADR-019, Phase 4.6.2).

    Raised only when the inputs handed to `PredictionRequestBuilder` do not
    satisfy the `PredictionRequest` contract. Every subclass is a defensive
    contract check: by the time `PredictionService` reaches the request-build
    stage, the PREPROCESSING and RUNTIME stages have already succeeded, so
    these are not expected to be reachable through the normal pipeline --
    they guard `PredictionRequestBuilder` against misuse by any other
    caller (e.g. tests, future refactors).
    """

    def __init__(
        self,
        message: str = "The prediction request could not be built.",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    ) -> None:
        super().__init__(message=message, status_code=status_code)


class MissingPreprocessingResultError(PredictionRequestBuildError):
    """Raised when no `PreprocessingResult` was supplied to the builder."""

    def __init__(
        self, message: str = "A completed image preprocessing result is required."
    ) -> None:
        super().__init__(message=message)


class PreprocessingNotSuccessfulError(PredictionRequestBuildError):
    """Raised when the supplied `PreprocessingResult` did not succeed."""

    def __init__(
        self, message: str = "Image preprocessing did not complete successfully."
    ) -> None:
        super().__init__(message=message)


class MissingProcessedTensorError(PredictionRequestBuildError):
    """Raised when the supplied `PreprocessingResult` has no processed tensor."""

    def __init__(
        self, message: str = "The preprocessed image tensor is missing."
    ) -> None:
        super().__init__(message=message)


class MissingRuntimeMetadataError(PredictionRequestBuildError):
    """Raised when no AI Runtime metadata snapshot was supplied to the builder."""

    def __init__(self, message: str = "AI Runtime metadata is required.") -> None:
        super().__init__(message=message)


class MissingRuntimeValidationError(PredictionRequestBuildError):
    """Raised when no AI Runtime validation outcome was supplied to the builder."""

    def __init__(self, message: str = "AI Runtime validation is required.") -> None:
        super().__init__(message=message)


class RuntimeValidationNotPassedError(PredictionRequestBuildError):
    """Raised when the supplied runtime validation outcome did not pass."""

    def __init__(
        self, message: str = "AI Runtime validation did not pass for this request."
    ) -> None:
        super().__init__(message=message, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)


class NoLoadedModelsForRequestError(PredictionRequestBuildError):
    """Raised when the runtime validation outcome reports zero loaded models."""

    def __init__(
        self,
        message: str = "No AI models are currently loaded and ready to serve this request.",
    ) -> None:
        super().__init__(message=message, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
