"""Ensemble Request (Phase 4.7.1 - Adaptive Ensemble Integration, ADR-024).

`EnsembleRequest` is the standardized, fully-serializable input contract
consumed by the Phase 4.7.1 `EnsembleEngine` entry point
(`app.ml.ensemble.ensemble_engine.EnsembleEngine`).

Per ADR-024 (and ADR-022), `PredictionExecutionResult` is the ONLY
prediction-side object the Adaptive Ensemble layer is allowed to consume.
`EnsembleRequest` never reaches back into `AIRuntimeManager`,
`PredictionEngine`, or TensorFlow models -- it only carries the already
-standardized execution result, together with the runtime metadata and
execution statistics needed to validate that result, forward to future
ensemble processing (Phase 4.7.2 onward).

This module performs NO voting, NO confidence calculation, and NO final
prediction selection.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.ml.prediction.execution_statistics import ExecutionStatistics
from app.ml.prediction.prediction_execution_result import PredictionExecutionResult


class EnsembleRequest(BaseModel):
    """Standardized input to the Phase 4.7.1 Adaptive Ensemble Integration layer.

    Constructed exactly once per prediction request, immediately after the
    RESULT_COLLECTION pipeline stage (ADR-022) completes. Fully
    serializable: every field is either a plain Pydantic model or a
    JSON-compatible primitive, so an `EnsembleRequest` can be logged or
    persisted without special handling.
    """

    model_config = ConfigDict(frozen=True)

    request_id: str = Field(description="Unique identifier for this prediction request.")
    execution_result: PredictionExecutionResult = Field(
        description=(
            "The complete, standardized `PredictionExecutionResult` for this "
            "request (ADR-022) -- the only prediction-side object the "
            "Adaptive Ensemble layer is allowed to consume."
        )
    )
    runtime_metadata: Any = Field(
        description=(
            "Point-in-time AI Runtime metadata snapshot "
            "(`app.services.runtime_metadata.RuntimeMetadata`, ADR-016), "
            "carried through unchanged from `execution_result.runtime_metadata`. "
            "Typed `Any` so this ML-layer module never imports the service "
            "layer, mirroring the same convention already used by "
            "`PredictionRequest.runtime_metadata` (ADR-019) and "
            "`PredictionExecutionResult.runtime_metadata` (ADR-022)."
        )
    )
    prediction_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Optional, additional request-level metadata for future ensemble "
            "processing stages (e.g. Phase 4.7.2 Voting & Agreement Engine, "
            "Phase 4.7.3 Confidence Calibration) to extend without changing "
            "this contract. Empty by default; never interpreted by this "
            "phase."
        ),
    )
    execution_statistics: ExecutionStatistics = Field(
        description=(
            "Aggregate timing and outcome statistics for this request "
            "(ADR-022), carried through unchanged from "
            "`execution_result.execution_statistics`."
        )
    )

    @classmethod
    def from_execution_result(
        cls,
        execution_result: PredictionExecutionResult,
        prediction_metadata: dict[str, Any] | None = None,
    ) -> "EnsembleRequest":
        """Build an `EnsembleRequest` from a completed `PredictionExecutionResult`.

        The single reusable place this standardization happens, so
        `PredictionService` never assembles an `EnsembleRequest` inline --
        mirroring the same stateless builder convention already used by
        `PredictionRequestBuilder` (ADR-019) and `PredictionResultCollector`
        (ADR-022).

        Args:
            execution_result: The completed RESULT_COLLECTION stage output
                (ADR-022) for this request.
            prediction_metadata: Optional additional request-level metadata.
                Defaults to an empty mapping.

        Returns:
            A fully populated `EnsembleRequest`.
        """
        return cls(
            request_id=execution_result.request_id,
            execution_result=execution_result,
            runtime_metadata=execution_result.runtime_metadata,
            prediction_metadata=prediction_metadata or {},
            execution_statistics=execution_result.execution_statistics,
        )
