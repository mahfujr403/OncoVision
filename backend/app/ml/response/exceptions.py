"""Prediction Response Builder exceptions (Phase 4.8.1, ADR-028).

These extend the application's centralized `OncoVisionError` so they are
automatically handled by the existing global exception handlers and never
leak internal details (paths, stack traces, etc.) to API clients --
mirroring the same convention already used by
`app.ml.ensemble.exceptions`.
"""

from fastapi import status

from app.core.exceptions import OncoVisionError


class InvalidResponseInputError(OncoVisionError):
    """Raised when the input supplied to the Response Builder is structurally invalid.

    For example, when `PredictionResponseBuilder.build()` is not supplied
    a `FinalPredictionResult` instance. Mirrors
    `app.ml.ensemble.exceptions.InvalidEnsembleInputError` for the same
    class of failure at this layer.
    """

    def __init__(
        self,
        message: str = "Invalid prediction input supplied to the Response Builder.",
    ) -> None:
        super().__init__(message=message, status_code=status.HTTP_400_BAD_REQUEST)
