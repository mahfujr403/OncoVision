"""ML infrastructure exceptions.

These extend the application's centralized `OncoVisionError` so they are
automatically handled by the existing global exception handlers and never
leak internal details (paths, stack traces, etc.) to API clients.
"""

from typing import Any

from fastapi import status

from app.core.exceptions import OncoVisionError


class ModelManifestError(OncoVisionError):
    """Raised when the model manifest is missing, malformed, or fails validation."""

    def __init__(
        self,
        message: str = "The model manifest is invalid.",
        errors: Any | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            errors=errors,
        )


class ModelNotFoundError(OncoVisionError):
    """Raised when a requested model ID or priority is not registered."""

    def __init__(
        self, message: str = "The requested model was not found in the registry."
    ) -> None:
        super().__init__(message=message, status_code=status.HTTP_404_NOT_FOUND)


class ModelDownloadError(OncoVisionError):
    """Raised when downloading a model file from Hugging Face Hub fails."""

    def __init__(self, message: str = "Failed to download the requested model.") -> None:
        super().__init__(message=message, status_code=status.HTTP_502_BAD_GATEWAY)


class ChecksumVerificationError(OncoVisionError):
    """Raised when a model file fails SHA-256 checksum verification."""

    def __init__(self, message: str = "Model file checksum verification failed.") -> None:
        super().__init__(message=message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
