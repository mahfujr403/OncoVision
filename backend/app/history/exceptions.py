"""Prediction History exceptions (Phase 5.1, ADR-032).

These extend the application's centralized `OncoVisionError` so they are
automatically handled by the existing global exception handlers and
never leak internal details (paths, stack traces, etc.) to API clients --
mirroring the same convention already used by `app.ml.ensemble.exceptions`
and `app.ml.response.exceptions`.

`PredictionHistoryError` is the shared base for every exception raised by
the `app.history` package, letting future callers catch the whole
hierarchy with a single `except PredictionHistoryError:` when they don't
need to distinguish the specific failure.
"""

from fastapi import status

from app.core.exceptions import OncoVisionError


class PredictionHistoryError(OncoVisionError):
    """Base exception for every error raised by the Prediction History package."""


class InvalidHistoryInputError(PredictionHistoryError):
    """Raised when the input supplied to `PredictionHistoryMapper` is structurally invalid.

    For example, when `PredictionHistoryMapper.to_history()` is not
    supplied a `PredictionResult`/`PredictionContext` pair. Mirrors
    `app.ml.response.exceptions.InvalidResponseInputError` for the same
    class of failure at this layer.
    """

    def __init__(
        self,
        message: str = "Invalid prediction input supplied to the Prediction History Mapper.",
    ) -> None:
        super().__init__(message=message, status_code=status.HTTP_400_BAD_REQUEST)


class PredictionHistoryNotFoundError(PredictionHistoryError):
    """Raised when a requested history record does not exist.

    Reserved for retrieval (Phase 5.3 onward); not raised by any code in
    this phase.
    """

    def __init__(self, message: str = "The requested prediction history record was not found.") -> None:
        super().__init__(message=message, status_code=status.HTTP_404_NOT_FOUND)


class PredictionHistoryAccessDeniedError(PredictionHistoryError):
    """Raised when a user attempts to access another user's history record.

    Reserved for ownership verification (ADR-032); not raised by any code
    in this phase.
    """

    def __init__(
        self,
        message: str = "You do not have permission to access this prediction history record.",
    ) -> None:
        super().__init__(message=message, status_code=status.HTTP_403_FORBIDDEN)


class PredictionHistoryPersistenceError(PredictionHistoryError):
    """Raised when a history record cannot be persisted.

    Per ADR-033, a persistence failure must never fail the originating
    prediction request -- callers are expected to catch and log this
    exception rather than let it propagate to the client. Reserved for
    persistence (Phase 5.2 onward); not raised by any code in this phase.
    """

    def __init__(self, message: str = "Prediction history record could not be persisted.") -> None:
        super().__init__(message=message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
