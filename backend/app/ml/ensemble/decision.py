"""Final ensemble decision orchestration.

Ties together strategy selection, weighted voting, confidence
aggregation, and agreement scoring into a single resolved decision.
Response formatting (timestamps, failed-model records) is intentionally
left to `AdaptiveEnsembleEngine`; this module only resolves the decision
itself.
"""

from dataclasses import dataclass

from app.ml.ensemble.agreement import AgreementCalculator
from app.ml.ensemble.confidence import EnsembleConfidenceCalculator
from app.ml.ensemble.response import (
    AgreementMetrics,
    ConfidenceMetrics,
    EnsembleStrategyType,
    ModelContribution,
)
from app.ml.ensemble.strategy import EnsembleStrategySelector, StrategyOutcome
from app.ml.ensemble.weighted_voting import WeightedVotingCalculator
from app.ml.prediction.prediction_result import IndividualPrediction
from app.ml.registry.model_registry import ModelRegistry


@dataclass(frozen=True)
class EnsembleDecision:
    """Fully-resolved ensemble decision, prior to response envelope formatting."""

    final_label: str
    final_class_index: int
    confidence: ConfidenceMetrics
    agreement: AgreementMetrics
    ensemble_strategy: EnsembleStrategyType
    model_contributions: list[ModelContribution]


class EnsembleDecisionMaker:
    """Orchestrates strategy selection, voting, confidence, and agreement scoring."""

    def __init__(self, registry: ModelRegistry) -> None:
        self._calculator = WeightedVotingCalculator(registry)
        self._selector = EnsembleStrategySelector()
        self._confidence_calculator = EnsembleConfidenceCalculator()
        self._agreement_calculator = AgreementCalculator()

    def decide(self, predictions: list[IndividualPrediction]) -> EnsembleDecision:
        """Resolve a single ensemble decision from a list of successful predictions.

        Args:
            predictions: Individual predictions from every model that
                executed successfully. Must be non-empty; callers are
                responsible for raising `PredictionUnavailableError`
                beforehand when no model succeeded.
        """
        strategy = self._selector.select(len(predictions))
        outcome = strategy.apply(predictions, self._calculator)

        final_class_index = max(
            range(len(outcome.combined_probabilities)),
            key=lambda index: outcome.combined_probabilities[index],
        )
        final_label = outcome.class_labels[final_class_index]
        final_confidence_percentage = outcome.combined_probabilities[final_class_index] * 100

        confidence = self._confidence_calculator.compute(predictions, final_confidence_percentage)
        agreement = self._agreement_calculator.compute(predictions, final_label)
        model_contributions = self._build_contributions(predictions, outcome, final_label)

        return EnsembleDecision(
            final_label=final_label,
            final_class_index=final_class_index,
            confidence=confidence,
            agreement=agreement,
            ensemble_strategy=outcome.strategy_type,
            model_contributions=model_contributions,
        )

    @staticmethod
    def _build_contributions(
        predictions: list[IndividualPrediction],
        outcome: StrategyOutcome,
        final_label: str,
    ) -> list[ModelContribution]:
        """Build a per-model contribution breakdown, normalized to sum to 1.0."""
        total_weight = sum(outcome.resolved_weights.values()) or 1.0
        return [
            ModelContribution(
                model_id=prediction.model_id,
                model_name=prediction.model_name,
                predicted_label=prediction.predicted_label,
                confidence_percentage=prediction.confidence.confidence_percentage,
                weight=round(outcome.resolved_weights.get(prediction.model_id, 0.0) / total_weight, 6),
                agreed_with_final_prediction=prediction.predicted_label == final_label,
            )
            for prediction in predictions
        ]
