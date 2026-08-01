"""Execution Statistics (Phase 4.6.5, ADR-022).

Aggregate timing and outcome statistics computed once per prediction
request from the individual model results produced by `PredictionEngine`
(ADR-008): `IndividualPrediction` and `FailedModelPrediction` records
(`app.ml.prediction.prediction_result`).

`ExecutionStatistics` is the single reusable place these numbers are
computed, so `PredictionExecutionResult` construction (Phase 4.6.5,
ADR-022) never duplicates aggregation logic. This module performs no AI
inference and never communicates with the AI Runtime Manager, Prediction
Engine, or Adaptive Ensemble Engine -- it only aggregates already-computed
prediction records.
"""

from pydantic import BaseModel, ConfigDict, Field

from app.ml.prediction.prediction_result import FailedModelPrediction, IndividualPrediction


class ExecutionStatistics(BaseModel):
    """Aggregate timing and outcome statistics for a single prediction request.

    Every value here is derived exclusively from the `IndividualPrediction`
    and `FailedModelPrediction` records produced by the Prediction Engine
    for one request; nothing is recomputed by re-running inference.
    """

    model_config = ConfigDict(frozen=True)

    total_models: int = Field(
        description=(
            "Total number of production models that were candidates for "
            "this request -- successfully executed, failed, or skipped "
            "(e.g. not currently loaded)."
        )
    )
    executed_model_count: int = Field(
        description=(
            "Number of models actually attempted for this request "
            "(successful_model_count + failed_model_count)."
        )
    )
    successful_model_count: int = Field(
        description="Number of models that produced a successful prediction."
    )
    failed_model_count: int = Field(
        description="Number of models that were attempted but failed to produce a prediction."
    )
    total_inference_time_ms: float = Field(
        description="Sum of every successfully executed model's inference time, in milliseconds."
    )
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

    @classmethod
    def from_results(
        cls,
        total_models: int,
        predictions: list[IndividualPrediction],
        failed_models: list[FailedModelPrediction],
    ) -> "ExecutionStatistics":
        """Compute aggregate statistics from a completed execution's results.

        Never raises: zero successful predictions (a total-failure or
        empty execution) is a valid, fully computed statistics snapshot,
        not an error.

        Args:
            total_models: Total number of production models that were
                candidates for this request (executed, failed, or
                skipped), used only to report how many models were never
                attempted.
            predictions: Every model that executed successfully.
            failed_models: Every model that was attempted but failed.

        Returns:
            A fully computed `ExecutionStatistics` instance.
        """
        successful_model_count = len(predictions)
        failed_model_count = len(failed_models)
        executed_model_count = successful_model_count + failed_model_count

        total_inference_time_ms = round(
            sum(prediction.inference_time_ms for prediction in predictions), 2
        )
        average_inference_time_ms = (
            round(total_inference_time_ms / successful_model_count, 2)
            if successful_model_count
            else 0.0
        )

        fastest_model: str | None = None
        slowest_model: str | None = None
        if predictions:
            fastest_model = min(predictions, key=lambda prediction: prediction.inference_time_ms).model_id
            slowest_model = max(predictions, key=lambda prediction: prediction.inference_time_ms).model_id

        return cls(
            total_models=total_models,
            executed_model_count=executed_model_count,
            successful_model_count=successful_model_count,
            failed_model_count=failed_model_count,
            total_inference_time_ms=total_inference_time_ms,
            average_inference_time_ms=average_inference_time_ms,
            fastest_model=fastest_model,
            slowest_model=slowest_model,
        )
