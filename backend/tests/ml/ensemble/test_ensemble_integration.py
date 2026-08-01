"""Verification tests for Phase 4.7.1 Adaptive Ensemble Integration (ADR-024).

Covers `EnsembleRequest`, `EnsembleEngine`, and `EnsembleResult`:
single-model execution, two-model execution, three-model execution,
partial execution (one or more models failed), the no-successful
-predictions fault-tolerance boundary, and serialization. Explicitly does
NOT cover voting, confidence calculation, or final prediction selection
-- those begin in Phase 4.7.2 onward.

Uses the real `PredictionResultCollector` (Phase 4.6.5, ADR-022) to build
`PredictionExecutionResult` fixtures, so these tests exercise the exact
input contract `EnsembleEngine` receives in production, following the
same fixture-construction convention already used in
`tests/services/test_prediction_service.py`.

Not wired into a CI runner in this phase; run standalone with:
    PYTHONPATH=. python3 tests/ml/ensemble/test_ensemble_integration.py
"""

import json

from app.ml.ensemble.ensemble_engine import EnsembleEngine
from app.ml.ensemble.ensemble_request import EnsembleRequest
from app.ml.ensemble.ensemble_result import EnsembleStatus
from app.ml.ensemble.exceptions import InvalidEnsembleInputError, PredictionUnavailableError
from app.ml.prediction.prediction_execution_result import PredictionResultCollector
from app.ml.prediction.prediction_result import (
    ConfidenceResult,
    FailedModelPrediction,
    IndividualPrediction,
    PredictionEngineResult,
    PredictionExecutionStats,
    TopClassPrediction,
)

CLASS_LABELS = ["lung_n", "lung_scc", "lung_aca"]


def make_prediction(
    model_id: str,
    model_name: str,
    raw_probabilities: list[float],
    inference_time_ms: float = 12.5,
) -> IndividualPrediction:
    top_class_index = max(range(len(raw_probabilities)), key=lambda i: raw_probabilities[i])
    confidence = ConfidenceResult(
        raw_probabilities=raw_probabilities,
        confidence_percentage=round(raw_probabilities[top_class_index] * 100, 4),
        top_class=CLASS_LABELS[top_class_index],
        top_class_index=top_class_index,
        top_k_predictions=[
            TopClassPrediction(
                label=CLASS_LABELS[top_class_index],
                class_index=top_class_index,
                confidence_percentage=round(raw_probabilities[top_class_index] * 100, 4),
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
        inference_time_ms=inference_time_ms,
    )


def make_execution_result(
    request_id: str,
    predictions: list[IndividualPrediction],
    failed_models: list[FailedModelPrediction] | None = None,
    runtime_metadata: object | None = "runtime-metadata-snapshot",
):
    failed_models = failed_models or []
    engine_result = PredictionEngineResult(
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
    collector = PredictionResultCollector()
    return collector.collect(
        request_id=request_id,
        runtime_metadata=runtime_metadata,
        engine_result=engine_result,
    )


def check(name: str, condition: bool) -> bool:
    print(f"[{'PASS' if condition else 'FAIL'}] {name}")
    return condition


def run_case(name, fn, expect_exception=None) -> bool:
    try:
        result = fn()
        if expect_exception is not None:
            print(f"[FAIL] {name}: expected {expect_exception.__name__}, got result {result}")
            return False
        print(f"[PASS] {name}: {result}")
        return True
    except Exception as exc:  # noqa: BLE001
        if expect_exception is not None and isinstance(exc, expect_exception):
            print(f"[PASS] {name}: raised {type(exc).__name__} -> {exc}")
            return True
        print(f"[FAIL] {name}: raised unexpected {type(exc).__name__} -> {exc}")
        return False


def main() -> None:
    results: list[bool] = []
    engine = EnsembleEngine()

    # 1. Single-model execution: one successful model.
    single_execution_result = make_execution_result(
        "req-single",
        [make_prediction("mobilenet_v2", "MobileNetV2", [0.10, 0.80, 0.10])],
    )
    single_request = EnsembleRequest.from_execution_result(single_execution_result)
    single_result = engine.process(single_request)
    results.append(check(
        "Single-model execution: one accepted, zero rejected, READY_FOR_VOTING",
        len(single_result.accepted_predictions) == 1
        and len(single_result.rejected_predictions) == 0
        and single_result.successful_models == ["mobilenet_v2"]
        and single_result.failed_models == []
        and single_result.ensemble_status == EnsembleStatus.READY_FOR_VOTING
        and single_result.validation_summary.has_successful_prediction is True,
    ))

    # 2. Two-model execution: two successful models.
    two_execution_result = make_execution_result(
        "req-two",
        [
            make_prediction("mobilenet_v2", "MobileNetV2", [0.05, 0.90, 0.05]),
            make_prediction("densenet_121", "DenseNet121", [0.10, 0.80, 0.10]),
        ],
    )
    two_result = engine.process(EnsembleRequest.from_execution_result(two_execution_result))
    results.append(check(
        "Two-model execution: two accepted, READY_FOR_VOTING",
        len(two_result.accepted_predictions) == 2
        and len(two_result.rejected_predictions) == 0
        and set(two_result.successful_models) == {"mobilenet_v2", "densenet_121"}
        and two_result.ensemble_status == EnsembleStatus.READY_FOR_VOTING,
    ))

    # 3. Three-model execution: three successful models.
    three_execution_result = make_execution_result(
        "req-three",
        [
            make_prediction("mobilenet_v2", "MobileNetV2", [0.05, 0.90, 0.05]),
            make_prediction("densenet_121", "DenseNet121", [0.10, 0.80, 0.10]),
            make_prediction(
                "efficientnet_resnet_fusion", "EfficientNet+ResNet Fusion", [0.05, 0.85, 0.10]
            ),
        ],
    )
    three_result = engine.process(EnsembleRequest.from_execution_result(three_execution_result))
    results.append(check(
        "Three-model execution: three accepted, READY_FOR_VOTING",
        len(three_result.accepted_predictions) == 3
        and len(three_result.rejected_predictions) == 0
        and three_result.ensemble_status == EnsembleStatus.READY_FOR_VOTING,
    ))

    # 4. Partial execution: two succeeded, one failed.
    partial_execution_result = make_execution_result(
        "req-partial",
        [
            make_prediction("mobilenet_v2", "MobileNetV2", [0.05, 0.90, 0.05]),
            make_prediction("densenet_121", "DenseNet121", [0.10, 0.80, 0.10]),
        ],
        failed_models=[
            FailedModelPrediction(
                model_id="efficientnet_resnet_fusion",
                model_name="EfficientNet+ResNet Fusion",
                failure_reason="Model failed during inference.",
            )
        ],
    )
    partial_result = engine.process(EnsembleRequest.from_execution_result(partial_execution_result))
    results.append(check(
        "Partial execution: 2 accepted, 1 rejected, DEGRADED",
        len(partial_result.accepted_predictions) == 2
        and len(partial_result.rejected_predictions) == 1
        and partial_result.rejected_predictions[0].model_id == "efficientnet_resnet_fusion"
        and partial_result.failed_models == ["efficientnet_resnet_fusion"]
        and partial_result.ensemble_status == EnsembleStatus.DEGRADED,
    ))

    # 5. No successful predictions: every model failed.
    no_success_execution_result = make_execution_result(
        "req-no-success",
        [],
        failed_models=[
            FailedModelPrediction(
                model_id="mobilenet_v2", model_name="MobileNetV2", failure_reason="Runtime failure."
            ),
            FailedModelPrediction(
                model_id="densenet_121", model_name="DenseNet121", failure_reason="Runtime failure."
            ),
        ],
    )
    results.append(run_case(
        "No successful predictions raises PredictionUnavailableError",
        lambda: engine.process(EnsembleRequest.from_execution_result(no_success_execution_result)),
        expect_exception=PredictionUnavailableError,
    ))

    # 6. Missing runtime metadata is a structural validation failure.
    missing_metadata_execution_result = make_execution_result(
        "req-missing-metadata",
        [make_prediction("mobilenet_v2", "MobileNetV2", [0.10, 0.80, 0.10])],
        runtime_metadata=None,
    )
    results.append(run_case(
        "Missing runtime metadata raises InvalidEnsembleInputError",
        lambda: engine.process(
            EnsembleRequest.from_execution_result(missing_metadata_execution_result)
        ),
        expect_exception=InvalidEnsembleInputError,
    ))

    # 7. Serialization: EnsembleRequest and EnsembleResult are fully JSON-serializable.
    serialized_request = json.loads(single_request.model_dump_json())
    serialized_result = json.loads(single_result.model_dump_json())
    results.append(check(
        "EnsembleRequest and EnsembleResult serialize to JSON",
        isinstance(serialized_request, dict)
        and serialized_request["request_id"] == "req-single"
        and serialized_request["execution_result"]["request_id"] == "req-single"
        and isinstance(serialized_result, dict)
        and serialized_result["request_id"] == "req-single"
        and serialized_result["ensemble_status"] == "ready_for_voting"
        and len(serialized_result["accepted_predictions"]) == 1,
    ))

    # 8. EnsembleEngine performs no voting, confidence, or final-prediction fields.
    results.append(check(
        "EnsembleResult carries no final prediction, confidence, or agreement fields",
        not hasattr(single_result, "final_label")
        and not hasattr(single_result, "confidence")
        and not hasattr(single_result, "agreement"),
    ))

    print()
    if all(results):
        print(f"ALL {len(results)} CASES PASSED")
    else:
        failed = len(results) - sum(results)
        print(f"{failed} / {len(results)} CASES FAILED")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
