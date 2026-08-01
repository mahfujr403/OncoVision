"""Reusable ensemble confidence aggregation utility.

Every ensemble decision is interpreted through this single utility so
confidence aggregation logic is never duplicated per strategy.
"""

import numpy as np

from app.ml.ensemble.response import ConfidenceMetrics
from app.ml.prediction.prediction_result import IndividualPrediction


class EnsembleConfidenceCalculator:
    """Computes aggregate confidence statistics across executed models."""

    def compute(
        self,
        predictions: list[IndividualPrediction],
        final_confidence_percentage: float,
    ) -> ConfidenceMetrics:
        """Build a full confidence breakdown for a resolved ensemble decision.

        Args:
            predictions: Individual predictions from every model that
                executed successfully.
            final_confidence_percentage: Ensemble-weighted confidence
                percentage of the final predicted label, as resolved by
                the selected voting strategy.

        Returns:
            A `ConfidenceMetrics` describing the final, average, maximum,
            minimum, and spread of confidence across executed models.
        """
        confidences = np.array(
            [prediction.confidence.confidence_percentage for prediction in predictions],
            dtype=float,
        )
        maximum = float(np.max(confidences))
        minimum = float(np.min(confidences))

        return ConfidenceMetrics(
            final_confidence_percentage=round(float(final_confidence_percentage), 4),
            average_confidence_percentage=round(float(np.mean(confidences)), 4),
            maximum_confidence_percentage=round(maximum, 4),
            minimum_confidence_percentage=round(minimum, 4),
            confidence_spread_percentage=round(maximum - minimum, 4),
        )
