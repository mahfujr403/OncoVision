"""Ensemble voting strategies.

Implements Cases 1-3 of the Ensemble Decision Strategy (Project Context,
Section 19 / ADR-009):

    Three models available -> Adaptive weighted ensemble
    Two models available   -> Weighted ensemble using available models
    One model available    -> Return the single prediction

Case 4 (no models available) is a Prediction Engine / Ensemble Engine
boundary condition handled by `AdaptiveEnsembleEngine` before a strategy
is ever selected; no strategy in this module is responsible for it.
"""

from abc import ABC, abstractmethod

from app.ml.ensemble.exceptions import InvalidEnsembleInputError
from app.ml.ensemble.response import EnsembleStrategyType
from app.ml.ensemble.weighted_voting import WeightedVotingCalculator
from app.ml.prediction.prediction_result import IndividualPrediction


class StrategyOutcome:
    """Result of applying an ensemble voting strategy to a set of predictions."""

    __slots__ = ("combined_probabilities", "class_labels", "resolved_weights", "strategy_type")

    def __init__(
        self,
        combined_probabilities: list[float],
        class_labels: list[str],
        resolved_weights: dict[str, float],
        strategy_type: EnsembleStrategyType,
    ) -> None:
        self.combined_probabilities = combined_probabilities
        self.class_labels = class_labels
        self.resolved_weights = resolved_weights
        self.strategy_type = strategy_type


class EnsembleVotingStrategy(ABC):
    """Base class for ensemble voting strategies.

    Strategies are independent from TensorFlow and communicate only with
    prediction results and the `WeightedVotingCalculator` (ADR-009).
    """

    strategy_type: EnsembleStrategyType

    @abstractmethod
    def apply(
        self,
        predictions: list[IndividualPrediction],
        calculator: WeightedVotingCalculator,
    ) -> StrategyOutcome:
        """Combine `predictions` into a single ensemble outcome."""
        raise NotImplementedError


class SingleModelStrategy(EnsembleVotingStrategy):
    """Case 1: exactly one model succeeded. Its prediction is returned as-is."""

    strategy_type = EnsembleStrategyType.SINGLE_MODEL

    def apply(
        self,
        predictions: list[IndividualPrediction],
        calculator: WeightedVotingCalculator,
    ) -> StrategyOutcome:
        prediction = predictions[0]
        class_labels = calculator.resolve_shared_class_labels(predictions)
        probabilities = [round(float(value), 6) for value in prediction.confidence.raw_probabilities]
        return StrategyOutcome(
            combined_probabilities=probabilities,
            class_labels=class_labels,
            resolved_weights={prediction.model_id: 1.0},
            strategy_type=self.strategy_type,
        )


class TwoModelWeightedStrategy(EnsembleVotingStrategy):
    """Case 2: two models succeeded. Static, manifest-configured weighted ensemble."""

    strategy_type = EnsembleStrategyType.TWO_MODEL_WEIGHTED

    def apply(
        self,
        predictions: list[IndividualPrediction],
        calculator: WeightedVotingCalculator,
    ) -> StrategyOutcome:
        weights = {prediction.model_id: calculator.default_weight(prediction.model_id) for prediction in predictions}
        combined_probabilities, class_labels = calculator.combine(predictions, weights)
        return StrategyOutcome(combined_probabilities, class_labels, weights, self.strategy_type)


class ThreeModelAdaptiveStrategy(EnsembleVotingStrategy):
    """Case 3: three (or more) models succeeded. Adaptive weighted ensemble.

    Each model's manifest-configured base weight (ADR-006) is scaled by
    its own prediction confidence before normalization, so confident
    models contribute proportionally more to the final decision than a
    static weighted vote would allow. This keeps the door open for future
    adaptive signals (stacking, Bayesian averaging, meta-learning) without
    changing the strategy interface (ADR-009).
    """

    strategy_type = EnsembleStrategyType.THREE_MODEL_ADAPTIVE

    def apply(
        self,
        predictions: list[IndividualPrediction],
        calculator: WeightedVotingCalculator,
    ) -> StrategyOutcome:
        weights = {
            prediction.model_id: (
                calculator.default_weight(prediction.model_id)
                * (prediction.confidence.confidence_percentage / 100.0)
            )
            for prediction in predictions
        }
        combined_probabilities, class_labels = calculator.combine(predictions, weights)
        return StrategyOutcome(combined_probabilities, class_labels, weights, self.strategy_type)


class EnsembleStrategySelector:
    """Selects the ensemble voting strategy matching the number of executed models."""

    def select(self, successful_model_count: int) -> EnsembleVotingStrategy:
        """Return the strategy for `successful_model_count` executed models.

        Any count of three or more executed models is treated as the
        adaptive strategy (Case 3), so registering additional production
        models in the manifest never requires new strategy logic.

        Raises:
            InvalidEnsembleInputError: If `successful_model_count` is not
                a positive integer. A count of zero is expected to have
                already been handled upstream as `PredictionUnavailableError`.
        """
        if successful_model_count == 1:
            return SingleModelStrategy()
        if successful_model_count == 2:
            return TwoModelWeightedStrategy()
        if successful_model_count >= 3:
            return ThreeModelAdaptiveStrategy()
        raise InvalidEnsembleInputError(
            "The Ensemble Engine requires at least one successful prediction to select a strategy."
        )
