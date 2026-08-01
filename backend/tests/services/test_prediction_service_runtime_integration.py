"""Verification tests for Phase 4.5.4 Prediction Service Integration (ADR-013/014/015/016).

Uses lightweight fake `RuntimeValidator`/`RuntimeMetadataService` stand-ins
so these tests exercise only `PredictionService`'s own RUNTIME-stage wiring,
independent of `AIRuntimeManager` or `ModelRegistry` (already covered by
`tests/services/test_runtime_adapter.py`, `test_runtime_validator.py`, and
`test_runtime_metadata.py`), following the same fake-based pattern used
throughout `tests/services/`.

Not wired into a CI runner in this phase; run standalone with:
    PYTHONPATH=. python3 tests/services/test_prediction_service_runtime_integration.py
"""

import asyncio
import io
import uuid

from PIL import Image
from starlette.datastructures import Headers, UploadFile

from app.core.upload import UploadValidator
from app.models.enums import UserRole
from app.models.user import User
from app.services.prediction_context import PredictionOptions
from app.services.prediction_exceptions import (
    NoLoadedModelsError,
    RuntimeMetadataCollectionFailedError,
    RuntimeNotInitializedError,
)
from app.services.prediction_result import PipelineStageName, PipelineStageStatus
from app.services.prediction_service import PredictionService
from app.services.runtime_metadata import RuntimeMetadata
from app.services.runtime_validator import RuntimeValidationResult


class FakeRuntimeValidator:
    """Duck-typed stand-in for `RuntimeValidator`.

    Exposes only `validate_or_raise()`, the sole method `PredictionService`
    is allowed to call on it, so an accidental call to any other method
    fails the test loudly.
    """

    def __init__(
        self,
        result: RuntimeValidationResult | None = None,
        raise_error: Exception | None = None,
    ) -> None:
        self._result = result
        self._raise_error = raise_error

    async def validate_or_raise(self) -> RuntimeValidationResult:
        if self._raise_error is not None:
            raise self._raise_error
        assert self._result is not None
        return self._result


class FakeRuntimeMetadataService:
    """Duck-typed stand-in for `RuntimeMetadataService`.

    Exposes only `collect()`, the sole method `PredictionService` is
    allowed to call on it.
    """

    def __init__(
        self,
        metadata: RuntimeMetadata | None = None,
        raise_error: Exception | None = None,
    ) -> None:
        self._metadata = metadata
        self._raise_error = raise_error

    async def collect(self) -> RuntimeMetadata:
        if self._raise_error is not None:
            raise self._raise_error
        assert self._metadata is not None
        return self._metadata


def make_upload_file(filename: str, content: bytes, content_type: str) -> UploadFile:
    headers = Headers({"content-type": content_type})
    return UploadFile(filename=filename, file=io.BytesIO(content), headers=headers)


def make_valid_image_bytes(fmt: str, size: tuple[int, int] = (64, 64)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, color=(10, 90, 140)).save(buffer, format=fmt)
    return buffer.getvalue()


def make_test_user() -> User:
    return User(
        id=uuid.uuid4(),
        full_name="Test Pathologist",
        email="pathologist@example.com",
        password_hash="hashed",
        role=UserRole.USER,
        is_active=True,
    )


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


def check(name: str, condition: bool) -> bool:
    print(f"[{'PASS' if condition else 'FAIL'}] {name}")
    return condition


async def run_case(name, coro_factory, expect_exception=None) -> bool:
    try:
        result = await coro_factory()
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


async def main() -> None:
    results: list[bool] = []

    user = make_test_user()
    options = PredictionOptions.from_request(
        type(
            "Req",
            (),
            {
                "confidence_threshold": 0.5,
                "include_individual_predictions": True,
                "include_runtime_statistics": True,
                "save_history": True,
                "generate_report": False,
            },
        )()
    )

    # 1. Backward compatibility: no runtime collaborators injected -> RUNTIME skipped.
    service_without_runtime = PredictionService(upload_validator=UploadValidator())
    upload_1 = make_upload_file("slide.jpg", make_valid_image_bytes("JPEG"), "image/jpeg")
    result_1 = await service_without_runtime.predict(
        image=upload_1, current_user=user, options=options
    )
    runtime_stage_1 = next(s for s in result_1.stages if s.name == PipelineStageName.RUNTIME)
    results.append(check(
        "RUNTIME stage is SKIPPED when collaborators are not injected",
        runtime_stage_1.status == PipelineStageStatus.SKIPPED
        and result_1.runtime_statistics is None
        and result_1.runtime_validation is None,
    ))

    # 2. Real integration: healthy runtime -> RUNTIME completes, metadata attached.
    service_with_runtime = PredictionService(
        upload_validator=UploadValidator(),
        runtime_validator=FakeRuntimeValidator(result=make_validation_result(loaded=2, failed=0)),
        runtime_metadata_service=FakeRuntimeMetadataService(metadata=make_metadata(loaded=2, failed=0)),
    )
    upload_2 = make_upload_file("slide.png", make_valid_image_bytes("PNG"), "image/png")
    result_2 = await service_with_runtime.predict(
        image=upload_2, current_user=user, options=options
    )
    runtime_stage_2 = next(s for s in result_2.stages if s.name == PipelineStageName.RUNTIME)
    results.append(check(
        "RUNTIME stage COMPLETES and metadata is attached when runtime is healthy",
        runtime_stage_2.status == PipelineStageStatus.COMPLETED
        and isinstance(result_2.runtime_statistics, RuntimeMetadata)
        and result_2.runtime_statistics.manifest_version == "oncovision-manifest-v3"
        and isinstance(result_2.runtime_validation, RuntimeValidationResult)
        and result_2.runtime_validation.loaded_model_count == 2,
    ))
    results.append(check(
        "Every other stage remains a skipped placeholder (no inference performed)",
        {
            s.name for s in result_2.stages
            if s.status == PipelineStageStatus.SKIPPED
        }
        == {
            PipelineStageName.PREPROCESSING,
            PipelineStageName.REQUEST_BUILDING,
            PipelineStageName.PREDICTION_ENGINE,
            PipelineStageName.ENSEMBLE,
            PipelineStageName.RESPONSE,
            PipelineStageName.HISTORY,
            PipelineStageName.REPORT,
        }
        and result_2.prediction is None
        and result_2.confidence is None
        and result_2.prediction_request is None
        and result_2.individual_model_results is None
        and result_2.ensemble_result is None,
    ))

    # 3. Runtime not initialized -> prediction halts with RuntimeNotInitializedError.
    async def not_initialized():
        service = PredictionService(
            upload_validator=UploadValidator(),
            runtime_validator=FakeRuntimeValidator(raise_error=RuntimeNotInitializedError()),
            runtime_metadata_service=FakeRuntimeMetadataService(metadata=make_metadata()),
        )
        upload = make_upload_file("slide.png", make_valid_image_bytes("PNG"), "image/png")
        return await service.predict(image=upload, current_user=user, options=options)

    results.append(await run_case(
        "Prediction halts gracefully when runtime is not initialized",
        not_initialized,
        expect_exception=RuntimeNotInitializedError,
    ))

    # 4. Zero loaded models -> prediction halts with NoLoadedModelsError.
    async def zero_loaded_models():
        service = PredictionService(
            upload_validator=UploadValidator(),
            runtime_validator=FakeRuntimeValidator(raise_error=NoLoadedModelsError()),
            runtime_metadata_service=FakeRuntimeMetadataService(metadata=make_metadata()),
        )
        upload = make_upload_file("slide.png", make_valid_image_bytes("PNG"), "image/png")
        return await service.predict(image=upload, current_user=user, options=options)

    results.append(await run_case(
        "Prediction halts gracefully when zero models are loaded",
        zero_loaded_models,
        expect_exception=NoLoadedModelsError,
    ))

    # 5. Metadata collection failure after passing validation still propagates.
    async def metadata_failure():
        service = PredictionService(
            upload_validator=UploadValidator(),
            runtime_validator=FakeRuntimeValidator(result=make_validation_result()),
            runtime_metadata_service=FakeRuntimeMetadataService(
                raise_error=RuntimeMetadataCollectionFailedError()
            ),
        )
        upload = make_upload_file("slide.png", make_valid_image_bytes("PNG"), "image/png")
        return await service.predict(image=upload, current_user=user, options=options)

    results.append(await run_case(
        "Metadata collection failure propagates after validation passes",
        metadata_failure,
        expect_exception=RuntimeMetadataCollectionFailedError,
    ))

    # 6. Degraded runtime (some models failed) still allows prediction to proceed.
    service_degraded = PredictionService(
        upload_validator=UploadValidator(),
        runtime_validator=FakeRuntimeValidator(result=make_validation_result(loaded=1, failed=1)),
        runtime_metadata_service=FakeRuntimeMetadataService(metadata=make_metadata(loaded=1, failed=1)),
    )
    upload_6 = make_upload_file("slide.jpg", make_valid_image_bytes("JPEG"), "image/jpeg")
    result_6 = await service_degraded.predict(image=upload_6, current_user=user, options=options)
    runtime_stage_6 = next(s for s in result_6.stages if s.name == PipelineStageName.RUNTIME)
    results.append(check(
        "Degraded runtime (partial model availability) still completes the RUNTIME stage",
        runtime_stage_6.status == PipelineStageStatus.COMPLETED
        and result_6.runtime_validation.failed_model_count == 1
        and result_6.runtime_validation.loaded_model_count == 1,
    ))

    print()
    if all(results):
        print(f"ALL {len(results)} CASES PASSED")
    else:
        failed = len(results) - sum(results)
        print(f"{failed} / {len(results)} CASES FAILED")
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
