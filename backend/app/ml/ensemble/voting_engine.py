"""Adaptive Weighted Voting Engine (Phase 4.7.2, ADR-025).

`AdaptiveWeightedVotingEngine` is the dedicated voting layer that
aggregates the individual model predictions produced by the Prediction
Engine (ADR-008) into a single weighted voting result, consumed by
Confidence Calibration (Phase 4.7.3) and Final Prediction (Phase 4.7.4).

Per ADR-025, `calculate_votes`:
    - Accepts `PredictionEngineResult`.
    - Reads each participating model's manifest-configured
      `ensemble_weight` (ADR-006) from the `ModelRegistry` via the
      existing `WeightedVotingCalculator` (never hardcoded).
    - Combines per-model probability vectors into a single weighted
      per-class score using `WeightedVotingCalculator.combine`.
    - Counts each candidate class's `received_votes` as the number of
      successfully executed models whose own top prediction selected
      that class.
    - Returns `VotingResult.empty()` only when zero models produced a
      successful prediction (nothing to vote on).

This stage performs NO confidence calibration and NO final prediction
selection -- those remain Phase 4.7.3/4.7.4's responsibility. It never
communicates with `AIRuntimeManager`, `PredictionEngine`,
`PredictionService`, or TensorFlow models -- consistent with
`EnsembleEngine` (ADR-024) and `AdaptiveEnsembleEngine` (ADR-009), it
consumes only prediction results and the `ModelRegistry`.
"""

import time
from collections import Counter

from app.core.logging import get_logger
from app.ml.ensemble.voting_result import VotingResult, WeightedVote
from app.ml.ensemble.weighted_voting import WeightedVotingCalculator
from app.ml.prediction.prediction_result import PredictionEngineResult
from app.ml.registry.model_registry import ModelRegistry

logger = get_logger(__name__)


class AdaptiveWeightedVotingEngine:
    """Aggregates individual model predictions into a weighted voting result.

    Reads each participating model's manifest-configured `ensemble_weight`
    from the `ModelRegistry` (ADR-006) rather than accepting it as a
    parameter or hardcoding it, mirroring the same convention already
    used by `WeightedVotingCalculator` and `AdaptiveEnsembleEngine`.

    Stateless and side-effect free beyond logging. Holds no per-request
    state between calls, so a single instance may be reused, or
    constructed, per request.

    Future phases extend this class without changing its public surface:
        - Phase 4.7.2: Adaptive Weighted Voting (this phase, complete)
        - Phase 4.7.3: Confidence Calibration
        - Phase 4.7.4: Final Prediction Builder
    """

    def __init__(self, registry: ModelRegistry) -> None:
        self._registry = registry
        self._calculator = WeightedVotingCalculator(registry)

    def calculate_votes(self, engine_result: PredictionEngineResult) -> VotingResult:
        """Calculate a weighted voting result from a Prediction Engine result.

        Args:
            engine_result: The complete output of the Prediction Engine for
                a single uploaded image, containing successful individual
                predictions and any failed models.

        Returns:
            The `VotingResult` for this request: one `WeightedVote` per
            candidate class label shared by every successfully executed
            model, carrying the manifest-weighted combined score
            (`WeightedVotingCalculator.combine`, ADR-006) and the number
            of models whose own prediction selected that class. Returns
            `VotingResult.empty()` when no model produced a successful
            prediction -- there is nothing to vote on.
        """
        predictions = engine_result.predictions
        successful_models = [prediction.model_id for prediction in predictions]
        failed_models = [failed.model_id for failed in engine_result.failed_models]

        if not predictions:
            logger.info(
                "Adaptive weighted voting skipped: no successful predictions to vote on "
                "(failed_models=%d).",
                len(failed_models),
            )
            return VotingResult.empty()

        started_at = time.perf_counter()

        combined_scores, class_labels = self._calculator.combine(predictions)
        received_votes_by_class = Counter(
            prediction.predicted_label for prediction in predictions
        )
        weighted_votes = [
            WeightedVote(
                class_name=class_label,
                weighted_score=score,
                received_votes=received_votes_by_class.get(class_label, 0),
            )
            for class_label, score in zip(class_labels, combined_scores)
        ]

        execution_time_ms = (time.perf_counter() - started_at) * 1000

        voting_result = VotingResult(
            weighted_votes=weighted_votes,
            successful_models=successful_models,
            failed_models=failed_models,
            total_models=len(successful_models) + len(failed_models),
            execution_time_ms=round(execution_time_ms, 4),
        )

        logger.info(
            "Adaptive weighted voting complete: successful_models=%d failed_models=%d "
            "candidate_classes=%d execution_time_ms=%.4f.",
            len(successful_models),
            len(failed_models),
            len(weighted_votes),
            execution_time_ms,
        )

        return voting_result
