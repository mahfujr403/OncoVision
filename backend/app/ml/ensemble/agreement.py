"""Reusable agreement scoring utility.

Measures how strongly the executed models agree with the final ensemble
decision. Every ensemble decision is scored through this single utility
so agreement interpretation logic is never duplicated per strategy.
"""

from collections import Counter

from app.ml.ensemble.response import AgreementLevel, AgreementMetrics
from app.ml.prediction.prediction_result import IndividualPrediction

_HIGH_AGREEMENT_THRESHOLD_PERCENT = 80.0
_MEDIUM_AGREEMENT_THRESHOLD_PERCENT = 50.0


class AgreementCalculator:
    """Computes agreement statistics between executed models and the final label."""

    def compute(
        self,
        predictions: list[IndividualPrediction],
        final_label: str,
    ) -> AgreementMetrics:
        """Build an agreement breakdown for a resolved ensemble decision.

        Args:
            predictions: Individual predictions from every model that
                executed successfully.
            final_label: The final ensemble-decided class label.

        Returns:
            An `AgreementMetrics` describing how many executed models
            agree with `final_label`, and the resulting agreement level.
        """
        total_executed_models = len(predictions)
        label_votes = Counter(prediction.predicted_label for prediction in predictions)
        agreeing_models = label_votes.get(final_label, 0)

        agreement_percentage = (
            round((agreeing_models / total_executed_models) * 100, 4)
            if total_executed_models
            else 0.0
        )

        return AgreementMetrics(
            agreeing_models=agreeing_models,
            total_executed_models=total_executed_models,
            agreement_percentage=agreement_percentage,
            agreement_level=self._resolve_level(agreement_percentage),
            suggested_labels=[label for label, _ in label_votes.most_common()],
        )

    @staticmethod
    def _resolve_level(agreement_percentage: float) -> AgreementLevel:
        """Map a numeric agreement percentage to a qualitative agreement level."""
        if agreement_percentage >= _HIGH_AGREEMENT_THRESHOLD_PERCENT:
            return AgreementLevel.HIGH
        if agreement_percentage >= _MEDIUM_AGREEMENT_THRESHOLD_PERCENT:
            return AgreementLevel.MEDIUM
        return AgreementLevel.LOW
