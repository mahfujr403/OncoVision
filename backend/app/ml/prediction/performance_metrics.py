"""Performance Metrics (Phase 4.6.6 - Runtime Statistics & Performance Metrics).

Derives qualitative, comparative performance indicators from an
already-computed `RuntimeStatistics` snapshot
(`app.ml.prediction.runtime_statistics`) for a single prediction request.

This module performs no AI inference, no timing of its own, and never
communicates with the AI Runtime Manager, Prediction Engine, or Adaptive
Ensemble Engine -- every value here is derived exclusively from timing
and outcome numbers `RuntimeStatistics` already aggregated. No ensemble
voting, agreement calculation, or final prediction selection is performed
here (ADR-008/ADR-022).

`PerformanceMetrics` is the single reusable place these derived
indicators are computed, so `PredictionExecutionResult` construction
(Phase 4.6.5/4.6.6, ADR-022) never duplicates this derivation logic.
"""

from pydantic import BaseModel, ConfigDict, Field

from app.ml.prediction.runtime_statistics import RuntimeStatistics


class PerformanceMetrics(BaseModel):
    """Derived, comparative performance indicators for a single prediction request.

    Every value here is derived exclusively from an already-computed
    `RuntimeStatistics` snapshot; nothing is recomputed by re-running
    inference or re-timing any stage.
    """

    model_config = ConfigDict(frozen=True)

    average_inference_time_ms: float = Field(
        description=(
            "Average inference time across successfully executed models, in "
            "milliseconds. Zero when no model executed successfully."
        )
    )
    fastest_model: str | None = Field(
        default=None,
        description=(
            "Model ID of the fastest successfully executed model, or None "
            "when no model executed successfully."
        ),
    )
    slowest_model: str | None = Field(
        default=None,
        description=(
            "Model ID of the slowest successfully executed model, or None "
            "when no model executed successfully."
        ),
    )
    execution_success_rate: float = Field(
        description=(
            "Percentage of executed models that produced a successful "
            "prediction, in the range 0-100. Zero when no model was executed."
        )
    )
    model_utilization_rate: float = Field(
        description=(
            "Percentage of all candidate production models (executed, "
            "failed, or skipped) that were actually attempted for this "
            "request, in the range 0-100. Zero when there were no candidate "
            "models."
        )
    )

    @classmethod
    def from_statistics(
        cls,
        runtime_statistics: RuntimeStatistics,
        total_candidate_models: int,
    ) -> "PerformanceMetrics":
        """Derive comparative performance indicators from `RuntimeStatistics`.

        Never raises: zero executed models, zero successful models, or zero
        candidate models are all valid, fully derived (zeroed) results, not
        errors.

        Args:
            runtime_statistics: The already-computed `RuntimeStatistics`
                snapshot for this request.
            total_candidate_models: Total number of production models that
                were candidates for this request -- executed, failed, or
                skipped (e.g. not currently loaded).

        Returns:
            A fully derived `PerformanceMetrics` instance.
        """
        inference_times = runtime_statistics.inference_time_per_model

        average_inference_time_ms = (
            round(sum(inference_times.values()) / len(inference_times), 2)
            if inference_times
            else 0.0
        )
        fastest_model = min(inference_times, key=inference_times.get) if inference_times else None
        slowest_model = max(inference_times, key=inference_times.get) if inference_times else None

        execution_success_rate = (
            round(
                (runtime_statistics.successful_model_count
                 / runtime_statistics.executed_model_count) * 100,
                2,
            )
            if runtime_statistics.executed_model_count
            else 0.0
        )
        model_utilization_rate = (
            round((runtime_statistics.executed_model_count / total_candidate_models) * 100, 2)
            if total_candidate_models
            else 0.0
        )

        return cls(
            average_inference_time_ms=average_inference_time_ms,
            fastest_model=fastest_model,
            slowest_model=slowest_model,
            execution_success_rate=execution_success_rate,
            model_utilization_rate=model_utilization_rate,
        )

    @classmethod
    def empty(cls) -> "PerformanceMetrics":
        """Return a zeroed `PerformanceMetrics` for callers with nothing to report."""
        return cls(
            average_inference_time_ms=0.0,
            fastest_model=None,
            slowest_model=None,
            execution_success_rate=0.0,
            model_utilization_rate=0.0,
        )
