"""Standardized Prediction Request contract (ADR-019, Phase 4.6.2).

`PredictionRequest` is the single, reusable object `PredictionRequestBuilder`
(see `app.ml.prediction.request_builder`) produces for every prediction
call. It is the ONLY input the Prediction Engine (Phase 4.6.3 onward) will
consume: routers, upload validation, preprocessing, and AI Runtime
implementation details are all hidden behind it (ADR-019).

`PredictionRequest` performs no AI inference and never communicates with
the AI Runtime Manager, Prediction Engine, or Adaptive Ensemble Engine --
it is a pure data contract, assembled once per request and never mutated.

`runtime_metadata` is typed `Any` rather than
`app.services.runtime_metadata.RuntimeMetadata` so this ML-layer module
never imports the service layer (the project never allows `app/ml` to
import `app/services`); this mirrors the same `Any` typing already used by
`app.services.prediction_result.PredictionResult` for the same object.
Every other field is strongly typed.

`PredictionRequest` is serializable except for `processed_tensor` (a raw
NumPy array): use `to_serializable_dict()` for logging or diagnostics,
which excludes the tensor both at the top level and inside the nested
`preprocessing_result`.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.ml.preprocessing.preprocessing_result import PreprocessingResult
from app.ml.prediction.request_metadata import (
    PredictionConfiguration,
    PredictionRequestOptions,
    UserContext,
)


class PredictionRequest(BaseModel):
    """Standardized, framework-independent input to the Prediction Engine (ADR-019).

    Constructed exactly once per request by `PredictionRequestBuilder`.
    Never reconstructed or mutated mid-pipeline.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    request_id: str = Field(description="Unique identifier for this prediction request.")
    request_timestamp: str = Field(
        description="ISO 8601 timestamp of when this `PredictionRequest` was built."
    )
    processed_tensor: Any = Field(
        description=(
            "Normalized, batched NumPy array ready for model inference -- the "
            "same object as `preprocessing_result.processed_tensor`, surfaced "
            "at the top level for convenient access. Typed `Any` rather than "
            "`numpy.ndarray` so this model remains usable wherever a plain "
            "Pydantic type is expected; always excluded when serializing "
            "(see `to_serializable_dict()`)."
        )
    )
    preprocessing_result: PreprocessingResult = Field(
        description="Full centralized image preprocessing outcome (ADR-018)."
    )
    runtime_metadata: Any = Field(
        description=(
            "Point-in-time AI Runtime metadata snapshot "
            "(`app.services.runtime_metadata.RuntimeMetadata`, ADR-016). "
            "Typed `Any` so this ML-layer module never imports the service "
            "layer; the object itself is always a plain, serializable "
            "Pydantic model."
        )
    )
    request_options: PredictionRequestOptions = Field(
        description="Validated per-request control flags submitted with this request."
    )
    user_context: UserContext = Field(
        description="Plain projection of the authenticated user submitting this request."
    )
    prediction_configuration: PredictionConfiguration = Field(
        description="Finalized, engine-facing configuration derived from request options and runtime state."
    )

    def to_serializable_dict(self) -> dict[str, Any]:
        """Return a JSON-safe projection of this request for logging or diagnostics.

        Excludes `processed_tensor` at both the top level and inside the
        nested `preprocessing_result`, since raw NumPy arrays are not
        JSON-serializable.
        """
        return self.model_dump(
            mode="json",
            exclude={
                "processed_tensor": True,
                "preprocessing_result": {"processed_tensor"},
            },
        )
