"""Tests for the Adaptive Ensemble Engine (Phase 3.4).

Covers: single-model prediction, two-model ensemble, three-model
ensemble, model disagreement, partial model failure, and the
no-available-models fault-tolerance boundary.
"""

import pytest

from app.ml.ensemble.ensemble_engine import AdaptiveEnsembleEngine
from app.ml.ensemble.exceptions import EnsembleConfigurationError, PredictionUnavailableError
from app.ml.ensemble.response import AgreementLevel, EnsembleStrategyType
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
def engine(registry: ModelRegistry) -> AdaptiveEnsembleEngine:
    return AdaptiveEnsembleEngine(registry=registry)


def _prediction(
    model_id: str,
    model_name: str,
    raw_probabilities: list[float],
    inference_time_ms: float = 12.5,
) -> IndividualPrediction:
    top_class_index = max(range(len(raw_probabilities)), key=lambda i: raw_probabilities[i])
    ranked_indices = sorted(range(len(raw_probabilities)), key=lambda i: raw_probabilities[i], reverse=True)
    confidence = ConfidenceResult(
        raw_probabilities=raw_probabilities,
        confidence_percentage=round(raw_probabilities[top_class_index] * 100, 4),
        top_class=CLASS_LABELS[top_class_index],
        top_class_index=top_class_index,
        top_k_predictions=[
            TopClassPrediction(
                label=CLASS_LABELS[i],
                class_index=i,
                confidence_percentage=round(raw_probabilities[i] * 100, 4),
            )
            for i in ranked_indices[:3]
        ],
    )
    return IndividualPrediction(
        model_id=model_id,
        model_name=model_name,
        model_version="1.0.0",
        predicted_label=confidence.top_class,
        predicted_class_index=confidence.top_class_index,
        confidence=confidence,
        inference_time_ms=inference_time_ms,
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


class TestSingleModelPrediction:
    def test_returns_the_single_prediction_unchanged(self, engine: AdaptiveEnsembleEngine) -> None:
        prediction = _prediction("mobilenet_v2", "MobileNetV2", [0.10, 0.80, 0.10])
        result = engine.generate_ensemble_prediction(_engine_result([prediction]))

        assert result.ensemble_strategy == EnsembleStrategyType.SINGLE_MODEL
        assert result.final_label == "lung_scc"
        assert result.final_class_index == 1
        assert result.confidence.final_confidence_percentage == pytest.approx(80.0)
        assert result.agreement.agreement_percentage == pytest.approx(100.0)
        assert result.agreement.agreement_level == AgreementLevel.HIGH
        assert len(result.model_contributions) == 1
        assert result.model_contributions[0].weight == pytest.approx(1.0)


class TestTwoModelEnsemble:
    def test_combines_two_agreeing_models(self, engine: AdaptiveEnsembleEngine) -> None:
        predictions = [
            _prediction("mobilenet_v2", "MobileNetV2", [0.05, 0.90, 0.05]),
            _prediction("densenet_121", "DenseNet121", [0.10, 0.80, 0.10]),
        ]
        result = engine.generate_ensemble_prediction(_engine_result(predictions))

        assert result.ensemble_strategy == EnsembleStrategyType.TWO_MODEL_WEIGHTED
        assert result.final_label == "lung_scc"
        assert result.agreement.agreeing_models == 2
        assert result.agreement.agreement_level == AgreementLevel.HIGH


class TestThreeModelEnsemble:
    def test_combines_three_models_adaptively(self, engine: AdaptiveEnsembleEngine) -> None:
        predictions = [
            _prediction("mobilenet_v2", "MobileNetV2", [0.05, 0.90, 0.05]),
            _prediction("densenet_121", "DenseNet121", [0.10, 0.80, 0.10]),
            _prediction("efficientnet_resnet_fusion", "EfficientNet+ResNet Fusion", [0.05, 0.85, 0.10]),
        ]
        result = engine.generate_ensemble_prediction(_engine_result(predictions))

        assert result.ensemble_strategy == EnsembleStrategyType.THREE_MODEL_ADAPTIVE
        assert result.final_label == "lung_scc"
        assert result.agreement.agreeing_models == 3
        assert result.agreement.agreement_level == AgreementLevel.HIGH
        assert sum(c.weight for c in result.model_contributions) == pytest.approx(1.0)


class TestModelDisagreement:
    def test_reports_low_or_medium_agreement_when_models_disagree(
        self, engine: AdaptiveEnsembleEngine
    ) -> None:
        predictions = [
            _prediction("mobilenet_v2", "MobileNetV2", [0.05, 0.90, 0.05]),
            _prediction("densenet_121", "DenseNet121", [0.85, 0.10, 0.05]),
            _prediction("efficientnet_resnet_fusion", "EfficientNet+ResNet Fusion", [0.10, 0.10, 0.80]),
        ]
        result = engine.generate_ensemble_prediction(_engine_result(predictions))

        assert result.agreement.agreement_level in {AgreementLevel.LOW, AgreementLevel.MEDIUM}
        assert result.agreement.agreeing_models < 3
        assert set(result.agreement.suggested_labels) == {"lung_scc", "lung_n", "lung_aca"}


class TestPartialModelFailure:
    def test_uses_only_successful_models_and_reports_failed_models(
        self, engine: AdaptiveEnsembleEngine
    ) -> None:
        predictions = [
            _prediction("mobilenet_v2", "MobileNetV2", [0.05, 0.90, 0.05]),
            _prediction("densenet_121", "DenseNet121", [0.10, 0.80, 0.10]),
        ]
        failed_models = [
            FailedModelPrediction(
                model_id="efficientnet_resnet_fusion",
                model_name="EfficientNet+ResNet Fusion",
                failure_reason="Model failed during inference.",
            )
        ]
        result = engine.generate_ensemble_prediction(_engine_result(predictions, failed_models))

        assert result.ensemble_strategy == EnsembleStrategyType.TWO_MODEL_WEIGHTED
        assert len(result.executed_models) == 2
        assert len(result.failed_models) == 1
        assert result.failed_models[0].model_id == "efficientnet_resnet_fusion"


class TestNoAvailableModels:
    def test_raises_prediction_unavailable_when_every_model_failed(
        self, engine: AdaptiveEnsembleEngine
    ) -> None:
        failed_models = [
            FailedModelPrediction(
                model_id="mobilenet_v2", model_name="MobileNetV2", failure_reason="Runtime failure."
            ),
            FailedModelPrediction(
                model_id="densenet_121", model_name="DenseNet121", failure_reason="Runtime failure."
            ),
        ]
        with pytest.raises(PredictionUnavailableError):
            engine.generate_ensemble_prediction(_engine_result([], failed_models))


class TestMismatchedClassLabelSpace:
    def test_raises_configuration_error_when_label_spaces_differ(self) -> None:
        manifest = ModelManifest(
            manifest_version="test",
            models=[
                _manifest_entry("mobilenet_v2", priority=1, ensemble_weight=0.5),
                ModelManifestEntry(
                    id="mismatched_model",
                    display_name="Mismatched Model",
                    version="1.0.0",
                    framework="tensorflow",
                    format="h5",
                    repository="oncovision-ai/models",
                    filename="mismatched_model.h5",
                    priority=2,
                    ensemble_weight=0.5,
                    input_size=224,
                    num_classes=2,
                    class_labels=["colon_n", "colon_aca"],
                    sha256="b" * 64,
                    enabled=True,
                    description="Model with an incompatible class label space.",
                ),
            ],
        )
        mismatched_engine = AdaptiveEnsembleEngine(registry=ModelRegistry(manifest))
        predictions = [
            _prediction("mobilenet_v2", "MobileNetV2", [0.10, 0.80, 0.10]),
            _prediction("mismatched_model", "Mismatched Model", [0.60, 0.40]),
        ]

        with pytest.raises(EnsembleConfigurationError):
            mismatched_engine.generate_ensemble_prediction(_engine_result(predictions))
