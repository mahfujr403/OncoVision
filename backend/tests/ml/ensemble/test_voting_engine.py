"""Tests for the Adaptive Weighted Voting Engine (Phase 4.7.2, ADR-025).

Covers the real weighted-voting behavior `calculate_votes` now performs:
weighted-score calculation via `WeightedVotingCalculator`, manifest-driven
`ensemble_weight` resolution (ADR-006), vote aggregation across candidate
classes, winning-class identification, and empty-prediction handling.
Confidence calibration and final prediction selection remain out of
scope -- those are Phase 4.7.3/4.7.4's responsibility.
"""

import pytest

from app.ml.ensemble.voting_engine import AdaptiveWeightedVotingEngine
from app.ml.ensemble.voting_result import VoteScore, VotingResult, WeightedVote
from app.ml.prediction.prediction_result import (
    ConfidenceResult,
    FailedModelPrediction,
    IndividualPrediction,
    PredictionEngineResult,
    PredictionExecutionStats,
    TopClassPrediction,
)
from app.ml.registry.model_registry import ModelRegistry
from app.ml.schemas import ModelManifest, ModelManifestEntry

CLASS_LABELS = ["lung_n", "lung_scc", "lung_aca"]


def _manifest_entry(model_id: str, priority: int, ensemble_weight: float) -> ModelManifestEntry:
    return ModelManifestEntry(
        id=model_id,
        display_name=model_id.replace("_", " ").title(),
        version="1.0.0",
        framework="tensorflow",
        format="h5",
        repository="oncovision-ai/models",
        filename=f"{model_id}.h5",
        priority=priority,
        ensemble_weight=ensemble_weight,
        input_size=224,
        num_classes=len(CLASS_LABELS),
        class_labels=CLASS_LABELS,
        sha256="a" * 64,
        enabled=True,
        description=f"Test manifest entry for {model_id}.",
    )


@pytest.fixture
def registry() -> ModelRegistry:
    manifest = ModelManifest(
        manifest_version="test",
        models=[
            _manifest_entry("mobilenet_v2", priority=1, ensemble_weight=0.30),
            _manifest_entry("densenet_121", priority=2, ensemble_weight=0.30),
            _manifest_entry("efficientnet_resnet_fusion", priority=3, ensemble_weight=0.40),
        ],
    )
    return ModelRegistry(manifest)


@pytest.fixture
def engine(registry: ModelRegistry) -> AdaptiveWeightedVotingEngine:
    return AdaptiveWeightedVotingEngine(registry)


def _registry_with_weights(**weights_by_model_id: float) -> ModelRegistry:
    """Build a `ModelRegistry` with caller-supplied `ensemble_weight`s.

    Used only by the manifest-weight-resolution test, to prove
    `calculate_votes` reads each model's weight from the `ModelRegistry`
    (ADR-006) rather than hardcoding it.
    """
    manifest = ModelManifest(
        manifest_version="test",
        models=[
            _manifest_entry(model_id, priority=index + 1, ensemble_weight=weight)
            for index, (model_id, weight) in enumerate(weights_by_model_id.items())
        ],
    )
    return ModelRegistry(manifest)


def _prediction(model_id: str, model_name: str, raw_probabilities: list[float]) -> IndividualPrediction:
    top_index = max(range(len(raw_probabilities)), key=lambda i: raw_probabilities[i])
    confidence = ConfidenceResult(
        raw_probabilities=raw_probabilities,
        confidence_percentage=round(raw_probabilities[top_index] * 100, 4),
        top_class=CLASS_LABELS[top_index],
        top_class_index=top_index,
        top_k_predictions=[
            TopClassPrediction(
                label=CLASS_LABELS[top_index],
                class_index=top_index,
                confidence_percentage=round(raw_probabilities[top_index] * 100, 4),
            )
        ],
    )
    return IndividualPrediction(
        model_id=model_id,
        model_name=model_name,
        model_version="1.0.0",
        predicted_label=confidence.top_class,
        predicted_class_index=confidence.top_class_index,
        confidence=confidence,
        probability_vector=raw_probabilities,
        inference_time_ms=12.5,
    )


def _engine_result(
    predictions: list[IndividualPrediction],
    failed_models: list[FailedModelPrediction] | None = None,
) -> PredictionEngineResult:
    failed_models = failed_models or []
    return PredictionEngineResult(
        predictions=predictions,
        failed_models=failed_models,
        execution_stats=PredictionExecutionStats(
            total_models_attempted=len(predictions) + len(failed_models),
            successful_predictions=len(predictions),
            failed_predictions=len(failed_models),
            preprocessing_time_ms=5.0,
            total_inference_time_ms=sum(p.inference_time_ms for p in predictions),
            total_execution_time_ms=50.0,
        ),
    )


class TestAdaptiveWeightedVotingEngine:
    """Verifies the real weighted-voting behavior of `calculate_votes` (ADR-025)."""

    def test_calculate_votes_accepts_prediction_engine_result(
        self, engine: AdaptiveWeightedVotingEngine
    ) -> None:
        engine_result = _engine_result(
            predictions=[
                _prediction("mobilenet_v2", "MobileNetV2", [0.7, 0.2, 0.1]),
                _prediction("densenet_121", "DenseNet121", [0.6, 0.3, 0.1]),
            ]
        )

        result = engine.calculate_votes(engine_result)

        assert isinstance(result, VotingResult)

    def test_calculate_votes_computes_weighted_scores_per_class(
        self, engine: AdaptiveWeightedVotingEngine
    ) -> None:
        """Weighted vote calculation: each class's score is the manifest-weighted,
        weight-normalized combination of every model's own probability for
        that class (registry weights: mobilenet_v2=0.30, densenet_121=0.30,
        efficientnet_resnet_fusion=0.40)."""
        engine_result = _engine_result(
            predictions=[
                _prediction("mobilenet_v2", "MobileNetV2", [0.7, 0.2, 0.1]),
                _prediction("densenet_121", "DenseNet121", [0.6, 0.3, 0.1]),
                _prediction(
                    "efficientnet_resnet_fusion",
                    "EfficientNetV2B0 + ResNet50 Fusion",
                    [0.5, 0.4, 0.1],
                ),
            ]
        )

        result = engine.calculate_votes(engine_result)

        scores_by_class = {vote.class_name: vote.weighted_score for vote in result.weighted_votes}
        assert scores_by_class["lung_n"] == pytest.approx(0.59, abs=1e-6)
        assert scores_by_class["lung_scc"] == pytest.approx(0.31, abs=1e-6)
        assert scores_by_class["lung_aca"] == pytest.approx(0.10, abs=1e-6)

    def test_calculate_votes_reads_ensemble_weight_from_model_manifest(self) -> None:
        """Ensemble weights come from the Model Manifest (ADR-006), not a
        hardcoded split -- flipping which model the manifest favors flips
        which class wins."""
        predictions = [
            _prediction("model_a", "Model A", [0.9, 0.05, 0.05]),
            _prediction("model_b", "Model B", [0.05, 0.9, 0.05]),
        ]

        registry_favoring_a = _registry_with_weights(model_a=0.8, model_b=0.2)
        engine_favoring_a = AdaptiveWeightedVotingEngine(registry_favoring_a)
        result_favoring_a = engine_favoring_a.calculate_votes(_engine_result(predictions))
        scores_favoring_a = {
            vote.class_name: vote.weighted_score for vote in result_favoring_a.weighted_votes
        }
        assert scores_favoring_a["lung_n"] > scores_favoring_a["lung_scc"]

        registry_favoring_b = _registry_with_weights(model_a=0.2, model_b=0.8)
        engine_favoring_b = AdaptiveWeightedVotingEngine(registry_favoring_b)
        result_favoring_b = engine_favoring_b.calculate_votes(_engine_result(predictions))
        scores_favoring_b = {
            vote.class_name: vote.weighted_score for vote in result_favoring_b.weighted_votes
        }
        assert scores_favoring_b["lung_scc"] > scores_favoring_b["lung_n"]

    def test_calculate_votes_aggregates_received_votes_across_classes(
        self, engine: AdaptiveWeightedVotingEngine
    ) -> None:
        """Vote aggregation: `received_votes` per class equals the count of
        successfully executed models whose own top prediction selected that
        class, and always sums back to the total successful model count."""
        engine_result = _engine_result(
            predictions=[
                _prediction("mobilenet_v2", "MobileNetV2", [0.6, 0.3, 0.1]),
                _prediction("densenet_121", "DenseNet121", [0.2, 0.7, 0.1]),
                _prediction(
                    "efficientnet_resnet_fusion",
                    "EfficientNetV2B0 + ResNet50 Fusion",
                    [0.1, 0.6, 0.3],
                ),
            ]
        )

        result = engine.calculate_votes(engine_result)

        votes_by_class = {vote.class_name: vote.received_votes for vote in result.weighted_votes}
        assert votes_by_class["lung_n"] == 1
        assert votes_by_class["lung_scc"] == 2
        assert votes_by_class["lung_aca"] == 0
        assert sum(votes_by_class.values()) == len(engine_result.predictions)
        assert result.successful_models == ["mobilenet_v2", "densenet_121", "efficientnet_resnet_fusion"]
        assert result.total_models == len(engine_result.predictions)

    def test_calculate_votes_identifies_winning_class_by_highest_weighted_score(
        self, engine: AdaptiveWeightedVotingEngine
    ) -> None:
        """Winning class selection: the class with the highest aggregated
        weighted score is identifiable directly from `weighted_votes`, even
        when it did not receive a majority of individual model votes."""
        engine_result = _engine_result(
            predictions=[
                # Two low-confidence votes for lung_n vs. one high-confidence,
                # heavily weighted vote for lung_scc.
                _prediction("mobilenet_v2", "MobileNetV2", [0.55, 0.40, 0.05]),
                _prediction("densenet_121", "DenseNet121", [0.55, 0.40, 0.05]),
                _prediction(
                    "efficientnet_resnet_fusion",
                    "EfficientNetV2B0 + ResNet50 Fusion",
                    [0.05, 0.90, 0.05],
                ),
            ]
        )

        result = engine.calculate_votes(engine_result)

        winning_vote = max(result.weighted_votes, key=lambda vote: vote.weighted_score)
        assert winning_vote.class_name == "lung_scc"

    def test_calculate_votes_returns_empty_result_with_zero_successful_predictions(
        self, engine: AdaptiveWeightedVotingEngine
    ) -> None:
        """Empty prediction handling: with no successful predictions there is
        nothing to vote on, so the engine returns `VotingResult.empty()`
        rather than raising or dividing by zero."""
        engine_result = _engine_result(
            predictions=[],
            failed_models=[
                FailedModelPrediction(
                    model_id="mobilenet_v2",
                    model_name="MobileNetV2",
                    failure_reason="Model failed to load.",
                )
            ],
        )

        result = engine.calculate_votes(engine_result)

        assert result == VotingResult.empty()
        assert result.weighted_votes == []
        assert result.successful_models == []
        assert result.failed_models == []
        assert result.total_models == 0

    def test_voting_result_empty_is_frozen_and_reusable(self) -> None:
        first = VotingResult.empty()
        second = VotingResult.empty()

        assert first == second
        with pytest.raises(Exception):
            first.total_models = 5  # type: ignore[misc]

    def test_vote_score_schema_holds_expected_fields(self) -> None:
        vote_score = VoteScore(
            model_id="mobilenet_v2",
            model_name="MobileNetV2",
            ensemble_weight=0.30,
            predicted_label="lung_n",
            confidence=87.5,
        )

        assert vote_score.model_id == "mobilenet_v2"
        assert vote_score.model_name == "MobileNetV2"
        assert vote_score.ensemble_weight == 0.30
        assert vote_score.predicted_label == "lung_n"
        assert vote_score.confidence == 87.5

    def test_weighted_vote_schema_holds_expected_fields(self) -> None:
        weighted_vote = WeightedVote(class_name="lung_n", weighted_score=0.65, received_votes=2)

        assert weighted_vote.class_name == "lung_n"
        assert weighted_vote.weighted_score == 0.65
        assert weighted_vote.received_votes == 2
