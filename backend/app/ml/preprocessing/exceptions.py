"""Centralized Image Preprocessing exceptions (ADR-018, Phase 4.6.1).

These extend the application's centralized `OncoVisionError` so they are
automatically handled by the existing global exception handlers and never
leak internal details (paths, stack traces, etc.) to API clients.

Distinct from `app.core.upload` (ADR-011, raw upload acceptance) and
`app.ml.prediction.exceptions` (ADR-008, the Prediction Engine's own
image validator, which runs later against already-accepted data): these
exceptions cover failures inside the centralized preprocessing pipeline
itself -- readability, RGB conversion, resizing, and normalization.
"""

from fastapi import status

from app.core.exceptions import OncoVisionError


class PreprocessingError(OncoVisionError):
    """Base exception for centralized image preprocessing failures."""

    def __init__(
        self,
        message: str = "Image preprocessing failed.",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    ) -> None:
        super().__init__(message=message, status_code=status_code)


class UnreadableImageError(PreprocessingError):
    """Raised when the uploaded image cannot be decoded for preprocessing."""

    def __init__(
        self,
        message: str = "The uploaded image could not be read for preprocessing.",
    ) -> None:
        super().__init__(message=message, status_code=status.HTTP_400_BAD_REQUEST)


class ImageConversionError(PreprocessingError):
    """Raised when the uploaded image cannot be converted to RGB."""

    def __init__(
        self,
        message: str = "The uploaded image could not be converted to RGB.",
    ) -> None:
        super().__init__(message=message, status_code=status.HTTP_400_BAD_REQUEST)


class ImageResizeError(PreprocessingError):
    """Raised when the uploaded image cannot be resized to the target input size."""

    def __init__(
        self, message: str = "The uploaded image could not be resized."
    ) -> None:
        super().__init__(message=message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ImageNormalizationError(PreprocessingError):
    """Raised when pixel normalization or tensor conversion fails."""

    def __init__(
        self, message: str = "The uploaded image could not be normalized."
    ) -> None:
        super().__init__(message=message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
