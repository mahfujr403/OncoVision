"""AI Runtime Manager exceptions.

These extend the application's centralized `OncoVisionError` so they are
automatically handled by the existing global exception handlers and never
leak internal details (paths, stack traces, etc.) to API clients.
"""

from fastapi import status

from app.core.exceptions import OncoVisionError


class RuntimeNotInitializedError(OncoVisionError):
    """Raised when the runtime is accessed before initialization has run."""

    def __init__(
        self, message: str = "The AI runtime has not been initialized yet."
    ) -> None:
        super().__init__(message=message, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)


class ModelLoadError(OncoVisionError):
    """Raised when a model fails to download, verify, or load into memory."""

    def __init__(self, message: str = "Failed to load the requested model.") -> None:
        super().__init__(message=message, status_code=status.HTTP_502_BAD_GATEWAY)


class ModelUnavailableError(OncoVisionError):
    """Raised when a requested model is not in a READY state at runtime."""

    def __init__(
        self, message: str = "The requested model is not currently available."
    ) -> None:
        super().__init__(message=message, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
