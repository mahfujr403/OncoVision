"""Schemas describing the Adaptive Ensemble Engine's output.

The Ensemble Engine consumes `IndividualPrediction` and
`FailedModelPrediction` objects produced by the Prediction Engine
(ADR-008) and never redefines its own copy of that input contract.
"""

from enum import Enum

from pydantic import BaseModel, Field

from app.ml.prediction.prediction_result import FailedModelPrediction, IndividualPrediction


class AgreementLevel(str, Enum):
    """Qualitative bucket describing how strongly executed models agree."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class EnsembleStrategyType(str, Enum):
    """Identifies which ensemble decision strategy produced a result."""

    SINGLE_MODEL = "single_model"
    TWO_MODEL_WEIGHTED = "two_model_weighted"
    THREE_MODEL_ADAPTIVE = "three_model_adaptive"


class ModelContribution(BaseModel):
    """Describes how strongly a single executed model influenced the final decision."""

    model_id: str = Field(description="Unique identifier of the contributing model.")
    model_name: str = Field(description="Human-readable display name of the contributing model.")
    predicted_label: str = Field(description="This model's own individual predicted label.")
    confidence_percentage: float = Field(
        description="This model's own individual top-class confidence percentage."
    )
    weight: float = Field(
        ge=0,
        le=1,
        description="Normalized weight (0-1) this model contributed to the final ensemble decision.",
    )
    agreed_with_final_prediction: bool = Field(
        description="Whether this model's own predicted label matches the final ensemble label."
    )


class ConfidenceMetrics(BaseModel):
    """Aggregate confidence statistics across every executed model."""

    final_confidence_percentage: float = Field(
        description="Ensemble-weighted confidence percentage of the final predicted label."
    )
    average_confidence_percentage: float = Field(
        description="Mean of each executed model's own top-class confidence percentage."
    )
    maximum_confidence_percentage: float = Field(
        description="Highest individual model confidence percentage among executed models."
    )
    minimum_confidence_percentage: float = Field(
        description="Lowest individual model confidence percentage among executed models."
    )
    confidence_spread_percentage: float = Field(
        description="Difference between the maximum and minimum individual confidence percentages."
    )


class AgreementMetrics(BaseModel):
    """Describes how strongly executed models agree with the final ensemble label."""

    agreeing_models: int = Field(
        description="Number of executed models whose own prediction matches the final label."
    )
    total_executed_models: int = Field(description="Total number of models that executed successfully.")
    agreement_percentage: float = Field(description="Percentage of executed models that agree with the final label.")
    agreement_level: AgreementLevel = Field(description="Qualitative agreement bucket: LOW, MEDIUM, or HIGH.")
    suggested_labels: list[str] = Field(
        description="Distinct labels predicted by executed models, ranked by vote count descending."
    )


class EnsemblePredictionResult(BaseModel):
    """Complete output of the Adaptive Ensemble Engine for a single image."""

    final_label: str = Field(description="Final ensemble-decided class label.")
    final_class_index: int = Field(description="Class index of the final ensemble-decided label.")
    confidence: ConfidenceMetrics = Field(description="Aggregate confidence statistics for this decision.")
    agreement: AgreementMetrics = Field(description="Model agreement statistics for this decision.")
    ensemble_strategy: EnsembleStrategyType = Field(
        description="Ensemble decision strategy used to produce this result."
    )
    executed_models: list[IndividualPrediction] = Field(
        description="Individual predictions from every model that executed successfully."
    )
    failed_models: list[FailedModelPrediction] = Field(
        description="Models that were attempted but failed to produce a prediction."
    )
    model_contributions: list[ModelContribution] = Field(
        description="Per-model contribution breakdown for the final ensemble decision."
    )
    prediction_timestamp: str = Field(description="ISO 8601 timestamp of when the ensemble decision was produced.")
