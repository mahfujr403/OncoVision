"""Reusable confidence calculation utility.

Converts a raw model output vector into a structured, human-readable
confidence breakdown. Every model's prediction is interpreted through this
single utility so confidence interpretation logic is never duplicated
per model.
"""

import numpy as np

from app.ml.prediction.prediction_result import ConfidenceResult, TopClassPrediction

_DEFAULT_TOP_K = 3


class ConfidenceCalculator:
    """Computes confidence breakdowns from raw model output probabilities."""

    def compute(
        self,
        probabilities: np.ndarray,
        class_labels: list[str],
        top_k: int = _DEFAULT_TOP_K,
    ) -> ConfidenceResult:
        """Build a full confidence breakdown for a single model's output vector.

        Args:
            probabilities: 1-D array of per-class probabilities, in
                class-index order.
            class_labels: Ordered class labels matching `probabilities` by
                index, sourced from the Model Manifest.
            top_k: Number of top-ranked classes to include in the breakdown.

        Returns:
            A `ConfidenceResult` describing the top prediction and the
            top-k ranking.
        """
        flat = np.asarray(probabilities, dtype=float).flatten()
        top_class_index = int(np.argmax(flat))
        effective_k = min(top_k, flat.size)
        ranked_indices = np.argsort(flat)[::-1][:effective_k]

        top_k_predictions = [
            TopClassPrediction(
                label=class_labels[index],
                class_index=int(index),
                confidence_percentage=round(float(flat[index]) * 100, 4),
            )
            for index in ranked_indices
        ]

        return ConfidenceResult(
            raw_probabilities=[round(float(value), 6) for value in flat],
            confidence_percentage=round(float(flat[top_class_index]) * 100, 4),
            top_class=class_labels[top_class_index],
            top_class_index=top_class_index,
            top_k_predictions=top_k_predictions,
        )
