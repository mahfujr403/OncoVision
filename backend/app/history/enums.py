"""Prediction History enumerations (Phase 5.1, ADR-032).

`PredictionHistoryStatus` is Prediction History's own, independently
owned status projection. It intentionally mirrors the shape of
`app.api.v1.predictions.responses.PredictionStatus` without importing
that API-layer module: `app.history` sits below the API layer and must
never depend on it, the same reasoning already documented on
`app.services.prediction_context.PredictionOptions`.
"""

from enum import Enum


class PredictionHistoryStatus(str, Enum):
    """Outcome of the prediction pipeline run a history record describes.

    Derived by `PredictionHistoryMapper` from the already-completed
    `app.services.prediction_result.PredictionResult` -- never
    recalculated from raw model output.
    """

    PENDING = "pending"
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
