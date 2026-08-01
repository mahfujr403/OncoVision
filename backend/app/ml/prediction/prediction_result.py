"""Schemas describing individual model prediction results.

The Prediction Engine returns only individual, per-model predictions and
execution statistics (ADR-008). Ensemble aggregation is a future phase's
responsibility and has no representation in this module.
"""

from pydantic import BaseModel, Field, computed_field


class TopClassPrediction(BaseModel):
    """A single ranked class prediction within a top-k breakdown."""

    label: str = Field(description="Class label.")
    class_index: int = Field(description="Index of the class within the model's output.")
    confidence_percentage: float = Field(
        description="Predicted probability for this class, as a percentage."
    )


class ConfidenceResult(BaseModel):
    """Reusable confidence breakdown for a single model's raw prediction output."""

    raw_probabilities: list[float] = Field(
        description="Raw probability for every class, in class-index order."
    )
    confidence_percentage: float = Field(
        description="Confidence percentage of the top predicted class."
    )
    top_class: str = Field(description="Label of the highest-confidence predicted class.")
    top_class_index: int = Field(
        description="Class index of the highest-confidence predicted class."
    )
    top_k_predictions: list[TopClassPrediction] = Field(
        description="The top-k ranked class predictions, descending by confidence."
    )


class IndividualPrediction(BaseModel):
    """A single loaded model's prediction result for one uploaded image."""

    model_id: str = Field(description="Unique identifier of the model that produced this prediction.")
    model_name: str = Field(description="Human-readable display name of the model.")
    model_version: str = Field(description="Version identifier of the model.")
    predicted_label: str = Field(description="Predicted class label.")
    predicted_class_index: int = Field(
        description="Index of the predicted class within the model's output."
    )
    confidence: ConfidenceResult = Field(description="Full confidence breakdown for this prediction.")
    probability_vector: list[float] | None = Field(
        default=None,
        description=(
            "Raw probability for every class, in class-index order. Mirrors "
            "`confidence.raw_probabilities`, surfaced at the top level for "
            "convenient access (e.g. by the Adaptive Ensemble Engine, Phase 4.7)."
        ),
    )
    inference_time_ms: float = Field(
        description="Time spent running inference for this model, in milliseconds."
    )
    execution_status: str = Field(
        default="success",
        description="Execution outcome for this model. Always 'success' for `IndividualPrediction`.",
    )


class FailedModelPrediction(BaseModel):
    """Record of a loaded model that failed to produce a prediction."""

    model_id: str = Field(description="Unique identifier of the model that failed.")
    model_name: str = Field(description="Human-readable display name of the model.")
    failure_reason: str = Field(description="Descriptive reason the model failed to produce a prediction.")
    execution_status: str = Field(
        default="failed",
        description="Execution outcome for this model. Always 'failed' for `FailedModelPrediction`.",
    )

    @computed_field(  # type: ignore[misc]
        description=(
            "Alias of `failure_reason`, exposed under the `error_message` name "
            "for API consumers that expect that field on a failed model record."
        )
    )
    @property
    def error_message(self) -> str:
        return self.failure_reason


class PredictionExecutionStats(BaseModel):
    """Aggregate timing and outcome statistics for a prediction request."""

    total_models_attempted: int = Field(
        description="Total number of loaded models a prediction was attempted with."
    )
    successful_predictions: int = Field(
        description="Number of models that produced a successful prediction."
    )
    failed_predictions: int = Field(
        description="Number of models that failed to produce a prediction."
    )
    preprocessing_time_ms: float = Field(
        description="Total time spent validating and preprocessing the image, in milliseconds."
    )
    total_inference_time_ms: float = Field(
        description="Sum of individual model inference times, in milliseconds."
    )
    total_execution_time_ms: float = Field(
        description="Total wall-clock time for the full prediction request, in milliseconds."
    )


class PredictionEngineResult(BaseModel):
    """Complete output of the Prediction Engine for a single image.

    Contains only individual, per-model predictions. Ensemble aggregation
    is intentionally out of scope (ADR-008).
    """

    predictions: list[IndividualPrediction] = Field(
        description="Successful individual model predictions."
    )
    failed_models: list[FailedModelPrediction] = Field(
        description="Models that were attempted but failed to produce a prediction."
    )
    execution_stats: PredictionExecutionStats = Field(
        description="Aggregate execution statistics for this prediction request."
    )
