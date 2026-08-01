"""Weighted voting utilities.

Combines the per-model probability vectors produced by the Prediction
Engine into a single ensemble probability vector, weighted by each
model's manifest-configured `ensemble_weight` (ADR-006) unless an
explicit weight override is supplied by the calling strategy.

Model metadata is always read from the `ModelRegistry`; weights and class
label spaces are never hardcoded here (per project ML rules).
"""

import numpy as np

from app.ml.ensemble.exceptions import EnsembleConfigurationError
from app.ml.prediction.prediction_result import IndividualPrediction
from app.ml.registry.model_registry import ModelRegistry


class WeightedVotingCalculator:
    """Combines individual model probability vectors into a single ensemble vector."""

    def __init__(self, registry: ModelRegistry) -> None:
        self._registry = registry

    def resolve_shared_class_labels(self, predictions: list[IndividualPrediction]) -> list[str]:
        """Return the class label space shared by every participating model.

        Raises:
            EnsembleConfigurationError: If participating models do not
                share an identical, ordered class label space. Every
                OncoVision production model classifies the same
                histopathology taxonomy (Project Context, Section 8), so a
                mismatch indicates a manifest misconfiguration rather than
                a valid ensemble input.
        """
        label_sets = {
            tuple(self._registry.get_model_by_id(prediction.model_id).class_labels)
            for prediction in predictions
        }
        if len(label_sets) != 1:
            raise EnsembleConfigurationError(
                "Participating models do not share an identical class label space; "
                "their predictions cannot be combined into a single ensemble."
            )
        return list(next(iter(label_sets)))

    def default_weight(self, model_id: str) -> float:
        """Return the manifest-configured `ensemble_weight` for a model (ADR-006)."""
        return self._registry.get_model_by_id(model_id).ensemble_weight

    def combine(
        self,
        predictions: list[IndividualPrediction],
        weights: dict[str, float] | None = None,
    ) -> tuple[list[float], list[str]]:
        """Combine per-model probability vectors into a single weighted ensemble vector.

        Args:
            predictions: Successful individual model predictions to combine.
            weights: Optional per-model weight overrides, keyed by model
                ID. Falls back to each model's manifest-configured
                `ensemble_weight` for any model not present in the mapping.

        Returns:
            A tuple of (combined probability vector, shared class labels).
            The combined vector is normalized to sum to 1.0.

        Raises:
            EnsembleConfigurationError: If total resolved weight is not
                greater than zero, or participating models do not share a
                class label space.
        """
        class_labels = self.resolve_shared_class_labels(predictions)
        combined = np.zeros(len(class_labels), dtype=float)
        total_weight = 0.0

        for prediction in predictions:
            weight = (weights or {}).get(prediction.model_id)
            if weight is None:
                weight = self.default_weight(prediction.model_id)
            probabilities = np.asarray(prediction.confidence.raw_probabilities, dtype=float)
            combined += weight * probabilities
            total_weight += weight

        if total_weight <= 0:
            raise EnsembleConfigurationError(
                "Total resolved ensemble weight must be greater than zero."
            )

        combined /= total_weight
        return [round(float(value), 6) for value in combined], class_labels
