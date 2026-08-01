"""Prediction Execution Result (Phase 4.6.5 - Prediction Result Collection, ADR-022).

`PredictionExecutionResult` is the standardized output of the Prediction
Result Collection layer. It wraps every `IndividualPrediction` and
`FailedModelPrediction` produced by
`PredictionEngine.predict_multi_model()` (ADR-021) into a single,
self-describing execution object, together with aggregate
`ExecutionStatistics` (`app.ml.prediction.execution_statistics`) and a
human-readable `ExecutionSummary` (`app.ml.prediction.execution_summary`).

Per ADR-022, `PredictionExecutionResult` becomes the ONLY input the
Adaptive Ensemble Engine (Phase 4.7, ADR-009) is allowed to consume. This
module performs NO ensemble voting, NO agreement calculation, and NO
final prediction selection or confidence calibration -- it only
standardizes already-produced individual model results into a stable,
serializable execution contract (ADR-008 remains in force: the
Prediction Engine, and this collection layer built on top of it, never
performs ensemble aggregation).

`PredictionResultCollector` is the single reusable place this
standardization happens, so `PredictionService` never assembles a
`PredictionExecutionResult` inline -- this mirrors the same stateless
builder pattern already used by `PredictionRequestBuilder` (ADR-019).

Phase 4.6.6 (Runtime Statistics & Performance Metrics) extends this same
module: `PredictionExecutionResult` now also carries a `RuntimeStatistics`
snapshot (`app.ml.prediction.runtime_statistics`), a `PerformanceMetrics`
snapshot (`app.ml.prediction.performance_metrics`), and the finalized
`ExecutionProfile` (`app.ml.prediction.execution_profiler`) they were
derived from -- so the Adaptive Ensemble Engine (Phase 4.7) can consume
complete execution metrics without re-deriving timing information
itself. No ensemble voting, agreement calculation, or final prediction
selection is performed by this phase either.

Future phases reuse this same module without change:
    - Phase 4.7 (Adaptive Ensemble Integration) consumes the returned
      `PredictionExecutionResult` as the Adaptive Ensemble Engine's only
      input.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.logging import get_logger
from app.ml.prediction.execution_profiler import ExecutionProfile, ExecutionProfiler
from app.ml.prediction.execution_statistics import ExecutionStatistics
from app.ml.prediction.execution_summary import ExecutionOverallStatus, ExecutionSummary
from app.ml.prediction.performance_metrics import PerformanceMetrics
from app.ml.prediction.prediction_result import (
    FailedModelPrediction,
    IndividualPrediction,
    PredictionEngineResult,
)
from app.ml.prediction.runtime_statistics import RuntimeStatistics
from app.ml.registry.model_registry import ModelRegistry
from app.utils.environment import get_current_timestamp

logger = get_logger(__name__)


class PredictionExecutionResult(BaseModel):
    """Standardized, ensemble-ready collection of a request's individual model results.

    Constructed exactly once per request by `PredictionResultCollector`.
    The Adaptive Ensemble Engine (Phase 4.7, ADR-009) is the sole intended
    consumer of this object; no ensemble voting, agreement calculation, or
    final prediction selection occurs here, or anywhere upstream of it
    (ADR-008/ADR-022).
    """

    model_config = ConfigDict(frozen=True)

    request_id: str = Field(description="Unique identifier for this prediction request.")
    execution_timestamp: str = Field(
        description="ISO 8601 timestamp this `PredictionExecutionResult` was assembled."
    )
    runtime_metadata: Any = Field(
        description=(
            "Point-in-time AI Runtime metadata snapshot "
            "(`app.services.runtime_metadata.RuntimeMetadata`, ADR-016), carried "
            "through unchanged from the RUNTIME pipeline stage. Typed `Any` so "
            "this ML-layer module never imports the service layer -- the same "
            "convention already used by `PredictionRequest.runtime_metadata` "
            "(ADR-019)."
        )
    )
    executed_models: list[str] = Field(
        description=(
            "Model IDs actually attempted for this request (successful and "
            "failed), in execution order."
        )
    )
    successful_models: list[str] = Field(
        description="Model IDs that executed successfully, in execution order."
    )
    failed_models: list[str] = Field(
        description="Model IDs that were attempted but failed to produce a prediction."
    )
    individual_predictions: list[IndividualPrediction] = Field(
        description=(
            "Every successful per-model prediction, unchanged from the "
            "Prediction Engine (ADR-008)."
        )
    )
    failed_model_predictions: list[FailedModelPrediction] = Field(
        description=(
            "Every failed per-model prediction record, unchanged from the "
            "Prediction Engine. Kept alongside `individual_predictions` so the "
            "Adaptive Ensemble Engine (Phase 4.7) can inspect failure reasons "
            "without re-deriving them from `failed_models`."
        )
    )
    execution_statistics: ExecutionStatistics = Field(
        description="Aggregate timing and outcome statistics for this request."
    )
    execution_summary: ExecutionSummary = Field(
        description="Human-readable, high-level outcome summary for this request."
    )
    execution_status: ExecutionOverallStatus = Field(
        description=(
            "Overall outcome of this request's model execution. Always equal "
            "to `execution_summary.overall_status`, surfaced at the top level "
            "for convenient access (e.g. by the Adaptive Ensemble Engine, "
            "Phase 4.7)."
        )
    )
    runtime_statistics: RuntimeStatistics = Field(
        description=(
            "Standardized per-stage and per-model timing and outcome "
            "statistics for this request (Phase 4.6.6)."
        )
    )
    performance_metrics: PerformanceMetrics = Field(
        description=(
            "Derived, comparative performance indicators computed from "
            "`runtime_statistics` (Phase 4.6.6)."
        )
    )
    execution_profile: ExecutionProfile = Field(
        description=(
            "Finalized, serializable record of every profiled pipeline stage "
            "for this request (`ExecutionProfiler.complete()`, Phase 4.6.6)."
        )
    )

    def has_any_successful_prediction(self) -> bool:
        """Return whether at least one model produced a successful prediction."""
        return len(self.individual_predictions) > 0


class PredictionResultCollector:
    """Standardizes `PredictionEngineResult` output into a `PredictionExecutionResult` (ADR-022).

    Stateless and side-effect free beyond logging: performs no AI
    inference, no I/O, and never touches the AI Runtime Manager,
    Prediction Engine, or Adaptive Ensemble Engine. `registry` is accepted
    only so registered models that were never attempted this request
    (skipped, e.g. not currently loaded) can be reported by ID; when
    omitted, `skipped_models` is always empty rather than raising.
    """

    def __init__(self, registry: ModelRegistry | None = None) -> None:
        self._registry = registry

    def collect(
        self,
        request_id: str,
        runtime_metadata: Any,
        engine_result: PredictionEngineResult,
        execution_profiler: ExecutionProfiler | None = None,
    ) -> PredictionExecutionResult:
        """Assemble a standardized `PredictionExecutionResult` from a completed engine run.

        Never raises: a partial execution (some models succeeded, some
        failed) and a total-failure execution (every attempted model
        failed) are both valid, fully represented results -- this method
        only standardizes whatever `PredictionEngineResult` it is handed.
        Rejecting an execution outcome (e.g. because zero models
        succeeded) remains the caller's decision, not this collector's.

        Args:
            request_id: The pipeline's request identifier for this request
                (shared with every other pipeline stage; never regenerated
                here).
            runtime_metadata: The RUNTIME stage's metadata snapshot
                (`app.services.runtime_metadata.RuntimeMetadata`), carried
                through unchanged for the Adaptive Ensemble Engine's future
                use.
            engine_result: The completed `PredictionEngineResult` produced
                by `PredictionEngine.predict_multi_model()` (ADR-021).
            execution_profiler: This request's `ExecutionProfiler`
                (Phase 4.6.6), carrying every profiled stage duration
                measured upstream (PREPROCESSING, RUNTIME_VALIDATION,
                REQUEST_BUILDING, PREDICTION_ENGINE). Finalized here via
                `execution_profiler.complete()`. Optional so existing
                callers keep working without profiling: the resulting
                `runtime_statistics.total_prediction_time_ms` and
                per-stage timing fields fall back to a zeroed
                `ExecutionProfile` when omitted, while per-model timing
                (derived from `engine_result` alone) is always fully
                populated.

        Returns:
            A fully standardized `PredictionExecutionResult`, ready for
            Adaptive Ensemble Engine processing (Phase 4.7), now also
            carrying `runtime_statistics`, `performance_metrics`, and
            `execution_profile` (Phase 4.6.6). No ensemble voting,
            agreement calculation, or final prediction selection is
            performed here (ADR-008/ADR-022).
        """
        logger.info("Prediction result collection started: request_id=%s", request_id)

        predictions = engine_result.predictions
        failed_models = engine_result.failed_models

        successful_model_ids = [prediction.model_id for prediction in predictions]
        failed_model_ids = [failed.model_id for failed in failed_models]
        executed_model_ids = successful_model_ids + failed_model_ids

        skipped_model_ids = self._resolve_skipped_models(executed_model_ids)
        total_models = len(executed_model_ids) + len(skipped_model_ids)

        statistics = ExecutionStatistics.from_results(
            total_models=total_models,
            predictions=predictions,
            failed_models=failed_models,
        )
        summary = ExecutionSummary.from_results(
            predictions=predictions,
            failed_models=failed_models,
            skipped_models=skipped_model_ids,
        )

        if execution_profiler is not None:
            execution_profile = execution_profiler.complete()
        else:
            now = get_current_timestamp()
            execution_profile = ExecutionProfile(
                request_id=request_id,
                profile_started_at=now,
                profile_completed_at=now,
                stages=[],
                total_duration_ms=None,
            )

        runtime_statistics = RuntimeStatistics.from_execution(
            execution_profile=execution_profile,
            executed_models=executed_model_ids,
            predictions=predictions,
            failed_models=failed_models,
        )
        performance_metrics = PerformanceMetrics.from_statistics(
            runtime_statistics=runtime_statistics,
            total_candidate_models=total_models,
        )

        execution_result = PredictionExecutionResult(
            request_id=request_id,
            execution_timestamp=get_current_timestamp(),
            runtime_metadata=runtime_metadata,
            executed_models=executed_model_ids,
            successful_models=successful_model_ids,
            failed_models=failed_model_ids,
            individual_predictions=predictions,
            failed_model_predictions=failed_models,
            execution_statistics=statistics,
            execution_summary=summary,
            execution_status=summary.overall_status,
            runtime_statistics=runtime_statistics,
            performance_metrics=performance_metrics,
            execution_profile=execution_profile,
        )

        logger.info(
            "Prediction result collection completed: request_id=%s executed_model_count=%d "
            "successful_model_count=%d failed_model_count=%d skipped_model_count=%d "
            "total_inference_time_ms=%.2f execution_status=%s",
            request_id,
            statistics.executed_model_count,
            statistics.successful_model_count,
            statistics.failed_model_count,
            len(skipped_model_ids),
            statistics.total_inference_time_ms,
            execution_result.execution_status.value,
        )
        logger.info(
            "Performance summary: request_id=%s average_inference_time_ms=%.2f "
            "fastest_model=%s slowest_model=%s execution_success_rate=%.2f%% "
            "model_utilization_rate=%.2f%% total_prediction_time_ms=%.2f",
            request_id,
            performance_metrics.average_inference_time_ms,
            performance_metrics.fastest_model,
            performance_metrics.slowest_model,
            performance_metrics.execution_success_rate,
            performance_metrics.model_utilization_rate,
            runtime_statistics.total_prediction_time_ms,
        )
        return execution_result

    def _resolve_skipped_models(self, executed_model_ids: list[str]) -> list[str]:
        """Return registered model IDs that were never attempted for this request.

        Returns an empty list when no `ModelRegistry` was supplied to this
        collector, rather than raising -- skipped-model reporting is a
        best-effort diagnostic, never a requirement for a valid
        `PredictionExecutionResult`.
        """
        if self._registry is None:
            return []

        executed_ids = set(executed_model_ids)
        return [
            entry.id
            for entry in self._registry.get_enabled_models_ordered_by_priority()
            if entry.id not in executed_ids
        ]
