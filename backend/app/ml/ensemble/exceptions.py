"""Adaptive Ensemble Engine exceptions.

These extend the application's centralized `OncoVisionError` so they are
automatically handled by the existing global exception handlers and never
leak internal details (paths, stack traces, etc.) to API clients.
"""

from fastapi import status

from app.core.exceptions import OncoVisionError


class PredictionUnavailableError(OncoVisionError):
    """Raised when no production model produced a successful prediction.

    Corresponds to Case 4 of the Ensemble Decision Strategy (Project
    Context, Section 19): zero available models -> prediction failure.
    This is a fault-tolerance boundary, not a validation error; it only
    fires once every individual model has already failed (ADR-005).
    """

    def __init__(
        self,
        message: str = (
            "Prediction unavailable: no production model returned a "
            "successful result for this request."
        ),
    ) -> None:
        super().__init__(message=message, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)


class InvalidEnsembleInputError(OncoVisionError):
    """Raised when the prediction results supplied to the Ensemble Engine
    are structurally invalid (e.g. an empty successful-prediction list
    reaching a voting strategy), rather than simply "all models failed".
    """

    def __init__(
        self,
        message: str = "Invalid prediction input supplied to the Adaptive Ensemble Engine.",
    ) -> None:
        super().__init__(message=message, status_code=status.HTTP_400_BAD_REQUEST)


class EnsembleConfigurationError(OncoVisionError):
    """Raised when ensemble configuration cannot be resolved for a set of
    successfully executed models — for example, mismatched class label
    spaces across participating models' manifest entries, or a total
    resolved ensemble weight of zero.
    """

    def __init__(self, message: str = "Adaptive Ensemble Engine configuration error.") -> None:
        super().__init__(message=message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
