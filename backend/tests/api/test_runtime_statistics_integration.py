"""Verification tests for Phase 4.8.3 Runtime Statistics Integration (ADR-029).

Exercises only `app.api.v1.predictions.router._build_runtime_statistics`,
independent of the full HTTP stack, following the same lightweight,
duck-typed pattern already used throughout `tests/services/`.

Not wired into a CI runner in this phase; run standalone with:
    PYTHONPATH=. python3 tests/api/test_runtime_statistics_integration.py
"""

from app.api.v1.predictions.responses import RuntimeHealthStatus
from app.api.v1.predictions.router import _build_runtime_statistics
from app.ml.prediction.prediction_result import PredictionExecutionStats
from app.services.runtime_metadata import RuntimeMetadata
from app.services.runtime_validator import RuntimeValidationResult


def make_validation_result(
    loaded: int = 2, failed: int = 0, is_valid: bool = True
) -> RuntimeValidationResult:
    return RuntimeValidationResult(
        is_valid=is_valid,
        runtime_initialized=True,
        runtime_healthy=True,
        loaded_model_count=loaded,
        failed_model_count=failed,
        validation_message=f"Runtime is operational with {loaded} model(s) loaded.",
    )


def make_metadata(loaded: int = 2, failed: int = 0) -> RuntimeMetadata:
    return RuntimeMetadata(
        manifest_version="oncovision-manifest-v3",
        runtime_version="1.0.0",
        frameworks=["tensorflow"],
        startup_timestamp="2026-07-20T00:00:00Z",
        loaded_models=[],
        failed_models=[],
        lazy_models=[],
        loaded_model_count=loaded,
        failed_model_count=failed,
        lazy_model_count=0,
        collected_at="2026-07-20T00:00:05Z",
    )


def make_execution_stats(
    total_models_attempted: int = 2,
    successful_predictions: int = 2,
    failed_predictions: int = 0,
    preprocessing_time_ms: float = 18.4,
    total_inference_time_ms: float = 131.0,
    total_execution_time_ms: float = 134.6,
) -> PredictionExecutionStats:
    return PredictionExecutionStats(
        total_models_attempted=total_models_attempted,
        successful_predictions=successful_predictions,
        failed_predictions=failed_predictions,
        preprocessing_time_ms=preprocessing_time_ms,
        total_inference_time_ms=total_inference_time_ms,
        total_execution_time_ms=total_execution_time_ms,
    )


def check(name: str, condition: bool) -> bool:
    print(f"[{'PASS' if condition else 'FAIL'}] {name}")
    return condition


def main() -> None:
    results: list[bool] = []

    # 1. Fully populated request: every ADR-029 field is projected without
    #    recalculation, alongside the pre-existing AI Runtime health fields.
    runtime_statistics = _build_runtime_statistics(
        request_id="req-1",
        runtime_metadata=make_metadata(loaded=2, failed=0),
        runtime_validation=make_validation_result(loaded=2, failed=0),
        execution_stats=make_execution_stats(),
        overall_processing_time_ms=158.9,
    )
    results.append(check(
        "runtime_statistics is populated for a completed pipeline",
        runtime_statistics is not None,
    ))
    results.append(check(
        "runtime_status reflects OPERATIONAL when every loaded model is healthy",
        runtime_statistics.runtime_status == RuntimeHealthStatus.OPERATIONAL,
    ))
    results.append(check(
        "loaded_model_count is copied from RuntimeValidationResult",
        runtime_statistics.loaded_model_count == 2,
    ))
    results.append(check(
        "successful_predictions is copied from PredictionExecutionStats",
        runtime_statistics.successful_predictions == 2,
    ))
    results.append(check(
        "failed_predictions is copied from PredictionExecutionStats",
        runtime_statistics.failed_predictions == 0,
    ))
    results.append(check(
        "participating_models is copied from PredictionExecutionStats.total_models_attempted",
        runtime_statistics.participating_models == 2,
    ))
    results.append(check(
        "preprocessing_time_ms is copied from PredictionExecutionStats",
        runtime_statistics.preprocessing_time_ms == 18.4,
    ))
    results.append(check(
        "total_inference_time_ms is copied from PredictionExecutionStats",
        runtime_statistics.total_inference_time_ms == 131.0,
    ))
    results.append(check(
        "total_execution_time_ms is copied from PredictionExecutionStats",
        runtime_statistics.total_execution_time_ms == 134.6,
    ))
    results.append(check(
        "overall_processing_time_ms is copied from the request's measured wall-clock time",
        runtime_statistics.overall_processing_time_ms == 158.9,
    ))

    # 2. Degraded runtime: one or more loaded models have failed.
    degraded_statistics = _build_runtime_statistics(
        request_id="req-2",
        runtime_metadata=make_metadata(loaded=1, failed=1),
        runtime_validation=make_validation_result(loaded=1, failed=1),
        execution_stats=make_execution_stats(
            total_models_attempted=1, successful_predictions=1, failed_predictions=0
        ),
        overall_processing_time_ms=99.1,
    )
    results.append(check(
        "runtime_status reflects DEGRADED when a loaded model has failed",
        degraded_statistics is not None
        and degraded_statistics.runtime_status == RuntimeHealthStatus.DEGRADED,
    ))

    # 3. Unavailable runtime: zero loaded models.
    unavailable_statistics = _build_runtime_statistics(
        request_id="req-3",
        runtime_metadata=make_metadata(loaded=0, failed=0),
        runtime_validation=make_validation_result(loaded=0, failed=0),
        execution_stats=None,
        overall_processing_time_ms=12.3,
    )
    results.append(check(
        "runtime_status reflects UNAVAILABLE when zero models are loaded",
        unavailable_statistics is not None
        and unavailable_statistics.runtime_status == RuntimeHealthStatus.UNAVAILABLE,
    ))

    # 4. PREDICTION_ENGINE stage not reached: execution_stats is None, so
    #    the new per-request fields stay None rather than raising or
    #    fabricating values -- pre-existing runtime health fields still
    #    populate normally.
    results.append(check(
        "Per-request execution fields are None when execution_stats is unavailable",
        unavailable_statistics.successful_predictions is None
        and unavailable_statistics.failed_predictions is None
        and unavailable_statistics.participating_models is None
        and unavailable_statistics.preprocessing_time_ms is None
        and unavailable_statistics.total_inference_time_ms is None
        and unavailable_statistics.total_execution_time_ms is None,
    ))
    results.append(check(
        "overall_processing_time_ms still populates even without execution_stats",
        unavailable_statistics.overall_processing_time_ms == 12.3,
    ))
    results.append(check(
        "loaded_model_count still populates even without execution_stats",
        unavailable_statistics.loaded_model_count == 0,
    ))

    # 5. RUNTIME stage itself never completed: the whole projection is None,
    #    matching pre-4.8.3 behavior (backward compatibility).
    results.append(check(
        "Returns None (unchanged pre-4.8.3 behavior) when the RUNTIME stage was skipped",
        _build_runtime_statistics(
            request_id="req-4",
            runtime_metadata=None,
            runtime_validation=None,
            execution_stats=make_execution_stats(),
            overall_processing_time_ms=5.0,
        ) is None,
    ))

    # 6. Backward compatibility: pre-existing fields are untouched.
    results.append(check(
        "Pre-existing loaded_models/failed_models/total_models fields remain populated",
        runtime_statistics.total_models == 2
        and runtime_statistics.loaded_models == []
        and runtime_statistics.failed_models == [],
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
