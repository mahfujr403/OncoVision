"""Verification tests for Phase 4.6.2 Prediction Request Builder (ADR-019).

Uses lightweight, duck-typed stand-ins for the RUNTIME stage's
`RuntimeValidationResult`/`RuntimeMetadata` (real service-layer classes)
so these tests exercise `PredictionRequestBuilder` in isolation, without
importing `app.services` -- consistent with the project's rule that
`app/ml` never imports `app/services` (see
`app.ml.prediction.request_metadata`).

Not wired into a CI runner in this phase; run standalone with:
    PYTHONPATH=. python3 tests/ml/prediction/test_request_builder.py
"""

import uuid
from types import SimpleNamespace

import numpy as np

from app.ml.prediction.exceptions import (
    MissingPreprocessingResultError,
    MissingProcessedTensorError,
    MissingRuntimeMetadataError,
    MissingRuntimeValidationError,
    NoLoadedModelsForRequestError,
    PreprocessingNotSuccessfulError,
    RuntimeValidationNotPassedError,
)
from app.ml.prediction.prediction_request import PredictionRequest
from app.ml.prediction.request_builder import PredictionRequestBuilder
from app.ml.preprocessing.preprocessing_result import (
    DEFAULT_SOURCE,
    PreprocessingResult,
)


def make_preprocessing_result(
    success: bool = True, with_tensor: bool = True
) -> PreprocessingResult:
    return PreprocessingResult(
        original_width=512,
        original_height=512,
        processed_width=224,
        processed_height=224,
        image_format="JPEG",
        preprocessing_time_ms=12.5,
        preprocessing_success=success,
        processed_tensor=np.zeros((1, 224, 224, 3), dtype=np.float32) if with_tensor else None,
        input_size=224,
        preprocessing_source=DEFAULT_SOURCE,
    )


def make_runtime_validation(is_valid: bool = True, loaded_model_count: int = 2) -> SimpleNamespace:
    return SimpleNamespace(
        is_valid=is_valid,
        runtime_initialized=True,
        runtime_healthy=True,
        loaded_model_count=loaded_model_count,
        failed_model_count=0,
        validation_message="Runtime is fully operational.",
    )


def make_runtime_metadata() -> SimpleNamespace:
    return SimpleNamespace(
        manifest_version="oncovision-manifest-v3",
        runtime_version="1.0.0",
        frameworks=["tensorflow"],
        loaded_model_count=2,
        failed_model_count=0,
        lazy_model_count=1,
        collected_at="2026-07-20T00:00:05Z",
    )


def make_request_options() -> SimpleNamespace:
    return SimpleNamespace(
        confidence_threshold=0.5,
        include_individual_predictions=True,
        include_runtime_statistics=True,
        save_history=True,
        generate_report=False,
    )


def make_user() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        email="pathologist@example.com",
        role=SimpleNamespace(value="user"),
        is_active=True,
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
    builder = PredictionRequestBuilder()

    # 1. Successful PredictionRequest creation.
    request = builder.build(
        request_id="test-request-id",
        preprocessing_result=make_preprocessing_result(),
        runtime_validation=make_runtime_validation(),
        runtime_metadata=make_runtime_metadata(),
        request_options=make_request_options(),
        current_user=make_user(),
    )
    results.append(check(
        "PredictionRequest is created with the expected shape",
        isinstance(request, PredictionRequest)
        and request.request_id == "test-request-id"
        and request.processed_tensor is not None
        and request.prediction_configuration.loaded_model_count == 2
        and request.prediction_configuration.manifest_version == "oncovision-manifest-v3"
        and request.request_options.confidence_threshold == 0.5
        and request.user_context.user_email == "pathologist@example.com"
        and request.user_context.user_role == "user",
    ))

    # 2. Serialization excludes the non-serializable tensor, keeps everything else.
    serialized = request.to_serializable_dict()
    results.append(check(
        "to_serializable_dict() is JSON-compatible and omits processed_tensor",
        isinstance(serialized, dict)
        and "processed_tensor" not in serialized
        and "processed_tensor" not in serialized["preprocessing_result"]
        and serialized["request_id"] == "test-request-id"
        and serialized["prediction_configuration"]["loaded_model_count"] == 2,
    ))

    # 3. Missing preprocessing result.
    results.append(run_case(
        "Missing preprocessing result raises MissingPreprocessingResultError",
        lambda: builder.build(
            request_id="req-2",
            preprocessing_result=None,
            runtime_validation=make_runtime_validation(),
            runtime_metadata=make_runtime_metadata(),
            request_options=make_request_options(),
            current_user=make_user(),
        ),
        expect_exception=MissingPreprocessingResultError,
    ))

    # 4. Preprocessing did not succeed.
    results.append(run_case(
        "Unsuccessful preprocessing raises PreprocessingNotSuccessfulError",
        lambda: builder.build(
            request_id="req-3",
            preprocessing_result=make_preprocessing_result(success=False),
            runtime_validation=make_runtime_validation(),
            runtime_metadata=make_runtime_metadata(),
            request_options=make_request_options(),
            current_user=make_user(),
        ),
        expect_exception=PreprocessingNotSuccessfulError,
    ))

    # 5. Missing processed tensor.
    results.append(run_case(
        "Missing processed tensor raises MissingProcessedTensorError",
        lambda: builder.build(
            request_id="req-4",
            preprocessing_result=make_preprocessing_result(with_tensor=False),
            runtime_validation=make_runtime_validation(),
            runtime_metadata=make_runtime_metadata(),
            request_options=make_request_options(),
            current_user=make_user(),
        ),
        expect_exception=MissingProcessedTensorError,
    ))

    # 6. Missing runtime metadata.
    results.append(run_case(
        "Missing runtime metadata raises MissingRuntimeMetadataError",
        lambda: builder.build(
            request_id="req-5",
            preprocessing_result=make_preprocessing_result(),
            runtime_validation=make_runtime_validation(),
            runtime_metadata=None,
            request_options=make_request_options(),
            current_user=make_user(),
        ),
        expect_exception=MissingRuntimeMetadataError,
    ))

    # 7. Missing runtime validation.
    results.append(run_case(
        "Missing runtime validation raises MissingRuntimeValidationError",
        lambda: builder.build(
            request_id="req-6",
            preprocessing_result=make_preprocessing_result(),
            runtime_validation=None,
            runtime_metadata=make_runtime_metadata(),
            request_options=make_request_options(),
            current_user=make_user(),
        ),
        expect_exception=MissingRuntimeValidationError,
    ))

    # 8. Runtime validation did not pass.
    results.append(run_case(
        "Failed runtime validation raises RuntimeValidationNotPassedError",
        lambda: builder.build(
            request_id="req-7",
            preprocessing_result=make_preprocessing_result(),
            runtime_validation=make_runtime_validation(is_valid=False),
            runtime_metadata=make_runtime_metadata(),
            request_options=make_request_options(),
            current_user=make_user(),
        ),
        expect_exception=RuntimeValidationNotPassedError,
    ))

    # 9. Zero loaded models.
    results.append(run_case(
        "Zero loaded models raises NoLoadedModelsForRequestError",
        lambda: builder.build(
            request_id="req-8",
            preprocessing_result=make_preprocessing_result(),
            runtime_validation=make_runtime_validation(loaded_model_count=0),
            runtime_metadata=make_runtime_metadata(),
            request_options=make_request_options(),
            current_user=make_user(),
        ),
        expect_exception=NoLoadedModelsForRequestError,
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
