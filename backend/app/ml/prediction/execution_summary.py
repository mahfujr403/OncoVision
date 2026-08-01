"""Execution Summary (Phase 4.6.5, ADR-022).

Human-readable, high-level outcome summary of a single prediction
request's execution, derived from the same `IndividualPrediction` /
`FailedModelPrediction` records `ExecutionStatistics`
(`app.ml.prediction.execution_statistics`) aggregates numerically.
`ExecutionSummary` is kept as its own reusable value object so
`PredictionExecutionResult` (Phase 4.6.5, ADR-022) never inlines this
derivation logic, and so callers that only need a quick, qualitative
outcome (logging, dashboards) do not need to interpret raw statistics.

This module performs no AI inference and never communicates with the AI
Runtime Manager, Prediction Engine, or Adaptive Ensemble Engine.
"""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.ml.prediction.prediction_result import FailedModelPrediction, IndividualPrediction


class ExecutionOverallStatus(str, Enum):
    """Overall, qualitative outcome of a single prediction request's model execution."""

    ALL_SUCCEEDED = "all_succeeded"
    PARTIALLY_SUCCEEDED = "partially_succeeded"
    ALL_FAILED = "all_failed"


class ExecutionSummary(BaseModel):
    """High-level, human-readable summary of a completed execution.

    Every value here is derived exclusively from the `IndividualPrediction`
    and `FailedModelPrediction` records produced by the Prediction Engine
    for one request, plus the set of registered models that were never
    attempted (skipped).
    """

    model_config = ConfigDict(frozen=True)

    overall_status: ExecutionOverallStatus = Field(
        description="Overall, qualitative outcome of this request's model execution."
    )
    completed_models: list[str] = Field(
        description="Model IDs that executed successfully, in execution order."
    )
    skipped_models: list[str] = Field(
        description=(
            "Model IDs that were registered candidates for this request "
            "but were never attempted (e.g. not currently loaded)."
        )
    )
    failed_models: list[str] = Field(
        description="Model IDs that were attempted but failed to produce a prediction."
    )
    execution_message: str = Field(
        description="Human-readable summary of the execution outcome."
    )

    @classmethod
    def from_results(
        cls,
        predictions: list[IndividualPrediction],
        failed_models: list[FailedModelPrediction],
        skipped_models: list[str],
    ) -> "ExecutionSummary":
        """Derive an `ExecutionSummary` from a completed execution's results.

        Never raises: a total-failure or empty execution is a valid,
        fully derived summary, not an error.

        Args:
            predictions: Every model that executed successfully.
            failed_models: Every model that was attempted but failed.
            skipped_models: Model IDs never attempted for this request.

        Returns:
            A fully derived `ExecutionSummary`.
        """
        completed_model_ids = [prediction.model_id for prediction in predictions]
        failed_model_ids = [failed.model_id for failed in failed_models]

        if completed_model_ids and not failed_model_ids:
            overall_status = ExecutionOverallStatus.ALL_SUCCEEDED
            execution_message = (
                f"All {len(completed_model_ids)} executed model(s) completed successfully."
            )
        elif completed_model_ids and failed_model_ids:
            overall_status = ExecutionOverallStatus.PARTIALLY_SUCCEEDED
            execution_message = (
                f"{len(completed_model_ids)} model(s) completed successfully; "
                f"{len(failed_model_ids)} model(s) failed."
            )
        elif failed_model_ids:
            overall_status = ExecutionOverallStatus.ALL_FAILED
            execution_message = (
                f"All {len(failed_model_ids)} attempted model(s) failed to produce a prediction."
            )
        else:
            overall_status = ExecutionOverallStatus.ALL_FAILED
            execution_message = "No production model was attempted for this request."

        if skipped_models:
            execution_message = (
                f"{execution_message} {len(skipped_models)} model(s) were skipped "
                "(not currently loaded)."
            )

        return cls(
            overall_status=overall_status,
            completed_models=completed_model_ids,
            skipped_models=skipped_models,
            failed_models=failed_model_ids,
            execution_message=execution_message,
        )
