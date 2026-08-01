"""Runtime Statistics (Phase 4.6.6 - Runtime Statistics & Performance Metrics).

Aggregates per-stage timing (`ExecutionProfile`,
`app.ml.prediction.execution_profiler`) together with per-model timing
and outcome counts (`IndividualPrediction` / `FailedModelPrediction`,
`app.ml.prediction.prediction_result`) into one standardized,
serializable `RuntimeStatistics` object for a single prediction request.

This module performs no AI inference, no timing of its own, and never
communicates with the AI Runtime Manager, Prediction Engine, or Adaptive
Ensemble Engine -- every value here is derived exclusively from
already-computed stage durations and already-computed per-model
prediction records.

`RuntimeStatistics` extends `PredictionExecutionResult` (Phase 4.6.5,
ADR-022) alongside `PerformanceMetrics`
(`app.ml.prediction.performance_metrics`), finalizing the execution
metrics contract before Adaptive Ensemble Integration (Phase 4.7). No
ensemble voting, agreement calculation, or final prediction selection is
performed here (ADR-008/ADR-022).
"""

from pydantic import BaseModel, ConfigDict, Field

from app.ml.prediction.execution_profiler import ExecutionProfile, ProfiledStage
from app.ml.prediction.prediction_result import FailedModelPrediction, IndividualPrediction


class RuntimeStatistics(BaseModel):
    """Standardized runtime timing and outcome statistics for a single prediction request.

    Every value here is derived exclusively from an already-completed
    `ExecutionProfile` and the `IndividualPrediction` /
    `FailedModelPrediction` records produced by the Prediction Engine for
    one request; nothing is recomputed by re-running inference or
    re-timing any stage.
    """

    model_config = ConfigDict(frozen=True)

    preprocessing_time_ms: float = Field(
        description="Wall-clock duration of the PREPROCESSING pipeline stage, in milliseconds."
    )
    runtime_validation_time_ms: float = Field(
        description="Wall-clock duration of AI Runtime readiness validation, in milliseconds."
    )
    request_build_time_ms: float = Field(
        description="Wall-clock duration of the REQUEST_BUILDING pipeline stage, in milliseconds."
    )
    inference_time_per_model: dict[str, float] = Field(
        description=(
            "Inference time in milliseconds for every successfully executed "
            "model, keyed by model ID."
        )
    )
    total_inference_time_ms: float = Field(
        description="Sum of every successfully executed model's inference time, in milliseconds."
    )
    total_prediction_time_ms: float = Field(
        description=(
            "Total wall-clock duration of the prediction pipeline measured by "
            "the `ExecutionProfiler`, from request receipt through "
            "RESULT_COLLECTION, in milliseconds."
        )
    )
    model_execution_order: list[str] = Field(
        description="Model IDs in the order they were attempted (successful and failed)."
    )
    executed_model_count: int = Field(
        description="Number of models actually attempted for this request."
    )
    successful_model_count: int = Field(
        description="Number of models that produced a successful prediction."
    )
    failed_model_count: int = Field(
        description="Number of models that were attempted but failed to produce a prediction."
    )

    @classmethod
    def from_execution(
        cls,
        execution_profile: ExecutionProfile,
        executed_models: list[str],
        predictions: list[IndividualPrediction],
        failed_models: list[FailedModelPrediction],
    ) -> "RuntimeStatistics":
        """Compute standardized runtime statistics from a completed execution.

        Never raises: zero successful predictions, or an `ExecutionProfile`
        with zero profiled stages (e.g. no `ExecutionProfiler` was
        supplied upstream), are both valid, fully computed snapshots, not
        errors.

        Args:
            execution_profile: The finalized `ExecutionProfile` for this
                request (`ExecutionProfiler.complete()`).
            executed_models: Model IDs actually attempted for this
                request, in execution order.
            predictions: Every model that executed successfully.
            failed_models: Every model that was attempted but failed.

        Returns:
            A fully computed `RuntimeStatistics` instance.
        """
        inference_time_per_model = {
            prediction.model_id: prediction.inference_time_ms for prediction in predictions
        }
        total_inference_time_ms = round(sum(inference_time_per_model.values()), 2)
        total_prediction_time_ms = (
            execution_profile.total_duration_ms
            if execution_profile.total_duration_ms is not None
            else round(
                sum(stage.duration_ms for stage in execution_profile.stages)
                + total_inference_time_ms,
                2,
            )
        )

        return cls(
            preprocessing_time_ms=execution_profile.get_stage_duration_ms(
                ProfiledStage.PREPROCESSING
            ),
            runtime_validation_time_ms=execution_profile.get_stage_duration_ms(
                ProfiledStage.RUNTIME_VALIDATION
            ),
            request_build_time_ms=execution_profile.get_stage_duration_ms(
                ProfiledStage.REQUEST_BUILDING
            ),
            inference_time_per_model=inference_time_per_model,
            total_inference_time_ms=total_inference_time_ms,
            total_prediction_time_ms=total_prediction_time_ms,
            model_execution_order=list(executed_models),
            executed_model_count=len(executed_models),
            successful_model_count=len(predictions),
            failed_model_count=len(failed_models),
        )

    @classmethod
    def empty(cls) -> "RuntimeStatistics":
        """Return a zeroed `RuntimeStatistics` for callers with nothing to report."""
        return cls(
            preprocessing_time_ms=0.0,
            runtime_validation_time_ms=0.0,
            request_build_time_ms=0.0,
            inference_time_per_model={},
            total_inference_time_ms=0.0,
            total_prediction_time_ms=0.0,
            model_execution_order=[],
            executed_model_count=0,
            successful_model_count=0,
            failed_model_count=0,
        )
