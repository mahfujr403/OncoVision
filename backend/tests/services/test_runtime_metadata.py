"""Verification tests for the Phase 4.5.3 Runtime Metadata Service (ADR-016).

Uses a lightweight fake `RuntimeAdapter` so these tests exercise only
`RuntimeMetadataService`'s own assembly and error-mapping logic,
independent of `AIRuntimeManager` or `ModelRegistry` (already covered by
`tests/services/test_runtime_adapter.py`), following the same fake-based
pattern as `tests/services/test_runtime_validator.py`.

Not wired into a CI runner in this phase; run standalone with:
    PYTHONPATH=. python3 tests/services/test_runtime_metadata.py
"""

import asyncio

from app.core.settings import Settings
from app.ml.runtime.runtime_state import LoadingStrategy, ModelRuntimeInfo, ModelState
from app.services.prediction_exceptions import RuntimeMetadataCollectionFailedError
from app.services.runtime_adapter import RuntimeStatusSnapshot
from app.services.runtime_metadata import RuntimeMetadata, RuntimeMetadataService


class FakeRuntimeAdapter:
    """Duck-typed stand-in for `RuntimeAdapter`.

    Exposes only the read-only, metadata-returning methods
    `RuntimeMetadataService` is allowed to call. Deliberately omits any
    method that could return a live TensorFlow instance, so an accidental
    call to one fails the test loudly.
    """

    def __init__(
        self,
        status: RuntimeStatusSnapshot | None = None,
        loaded: list[ModelRuntimeInfo] | None = None,
        failed: list[ModelRuntimeInfo] | None = None,
        lazy: list[ModelRuntimeInfo] | None = None,
        manifest_version: str = "test-manifest-v1",
        frameworks: list[str] | None = None,
        raise_error: bool = False,
    ) -> None:
        self._status = status
        self._loaded = loaded or []
        self._failed = failed or []
        self._lazy = lazy or []
        self._manifest_version = manifest_version
        self._frameworks = frameworks or ["tensorflow"]
        self._raise_error = raise_error

    async def get_runtime_status(self) -> RuntimeStatusSnapshot:
        if self._raise_error:
            raise ConnectionError("Simulated collaborator failure.")
        assert self._status is not None
        return self._status

    async def get_loaded_models(self) -> list[ModelRuntimeInfo]:
        return self._loaded

    async def get_failed_models(self) -> list[ModelRuntimeInfo]:
        return self._failed

    async def get_lazy_models(self) -> list[ModelRuntimeInfo]:
        return self._lazy

    def get_manifest_version(self) -> str:
        return self._manifest_version

    def get_frameworks(self) -> list[str]:
        return self._frameworks


def make_runtime_info(
    model_id: str,
    state: ModelState,
    loading_strategy: LoadingStrategy = LoadingStrategy.STARTUP,
    **overrides,
) -> ModelRuntimeInfo:
    return ModelRuntimeInfo(
        model_id=model_id,
        display_name=model_id.replace("_", " ").title(),
        priority=1,
        loading_strategy=loading_strategy,
        state=state,
        **overrides,
    )


def make_status(**overrides) -> RuntimeStatusSnapshot:
    base = {
        "runtime_started": True,
        "runtime_started_at": "2026-07-20T00:00:00Z",
        "startup_completed_at": "2026-07-20T00:00:05Z",
        "startup_duration_ms": 5000.0,
        "is_operational": True,
        "total_model_count": 3,
        "loaded_model_count": 2,
        "failed_model_count": 0,
        "pending_model_count": 0,
        "disabled_model_count": 0,
        "memory_status": {
            "available_mb": 512.0,
            "total_mb": 2048.0,
            "tracked_model_memory_mb": 300.0,
        },
        "models": [],
    }
    base.update(overrides)
    return RuntimeStatusSnapshot.model_validate(base)


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

    # 1. Fully operational runtime: two loaded, zero failed, one lazy.
    loaded = [
        make_runtime_info("mobilenet_v2", ModelState.READY, LoadingStrategy.STARTUP),
        make_runtime_info("densenet_121", ModelState.READY, LoadingStrategy.STARTUP),
    ]
    lazy = [
        make_runtime_info(
            "efficientnet_resnet_fusion", ModelState.REGISTERED, LoadingStrategy.LAZY
        )
    ]
    service = RuntimeMetadataService(
        runtime_adapter=FakeRuntimeAdapter(
            status=make_status(),
            loaded=loaded,
            failed=[],
            lazy=lazy,
            manifest_version="oncovision-manifest-v3",
            frameworks=["tensorflow"],
        ),
        settings=Settings(APP_VERSION="1.4.0"),
    )
    metadata = await service.collect()

    results.append(check(
        "collect() returns a RuntimeMetadata instance",
        isinstance(metadata, RuntimeMetadata),
    ))
    results.append(check(
        "Loaded models accuracy: count and entries match RuntimeAdapter",
        metadata.loaded_model_count == 2
        and metadata.loaded_models == loaded,
    ))
    results.append(check(
        "Failed models accuracy: empty when RuntimeAdapter reports none",
        metadata.failed_model_count == 0
        and metadata.failed_models == [],
    ))
    results.append(check(
        "Lazy models accuracy: count and entries match RuntimeAdapter",
        metadata.lazy_model_count == 1
        and metadata.lazy_models == lazy
        and metadata.lazy_models[0].loading_strategy == LoadingStrategy.LAZY,
    ))
    results.append(check(
        "Manifest version reflects RuntimeAdapter.get_manifest_version()",
        metadata.manifest_version == "oncovision-manifest-v3",
    ))
    results.append(check(
        "Runtime version reflects injected Settings.APP_VERSION",
        metadata.runtime_version == "1.4.0",
    ))
    results.append(check(
        "Frameworks reflect RuntimeAdapter.get_frameworks()",
        metadata.frameworks == ["tensorflow"],
    ))
    results.append(check(
        "Startup timestamp reflects RuntimeStatusSnapshot.runtime_started_at",
        metadata.startup_timestamp == "2026-07-20T00:00:00Z",
    ))
    results.append(check(
        "collected_at is populated with an ISO 8601 timestamp",
        isinstance(metadata.collected_at, str) and len(metadata.collected_at) > 0,
    ))
    results.append(check(
        "No TensorFlow objects leak: no loaded/failed/lazy entry exposes predict()",
        not any(hasattr(m, "predict") for m in metadata.loaded_models + metadata.failed_models + metadata.lazy_models),
    ))

    # 2. Degraded runtime: one loaded, one failed, one lazy, multiple frameworks.
    degraded_loaded = [make_runtime_info("mobilenet_v2", ModelState.READY)]
    degraded_failed = [
        make_runtime_info(
            "densenet_121", ModelState.FAILED, error_message="Insufficient memory."
        )
    ]
    degraded_lazy = [
        make_runtime_info(
            "efficientnet_resnet_fusion", ModelState.REGISTERED, LoadingStrategy.LAZY
        )
    ]
    degraded_service = RuntimeMetadataService(
        runtime_adapter=FakeRuntimeAdapter(
            status=make_status(loaded_model_count=1, failed_model_count=1),
            loaded=degraded_loaded,
            failed=degraded_failed,
            lazy=degraded_lazy,
            frameworks=["tensorflow", "onnx"],
        ),
    )
    degraded_metadata = await degraded_service.collect()
    results.append(check(
        "Degraded runtime: loaded/failed/lazy counts and failure reason preserved",
        degraded_metadata.loaded_model_count == 1
        and degraded_metadata.failed_model_count == 1
        and degraded_metadata.failed_models[0].error_message == "Insufficient memory."
        and degraded_metadata.lazy_model_count == 1,
    ))
    results.append(check(
        "Multiple frameworks in use are all reported",
        degraded_metadata.frameworks == ["tensorflow", "onnx"],
    ))

    # 3. Startup not yet begun: startup_timestamp is None, zero of everything.
    not_started_service = RuntimeMetadataService(
        runtime_adapter=FakeRuntimeAdapter(
            status=make_status(
                runtime_started=False,
                runtime_started_at=None,
                startup_completed_at=None,
                startup_duration_ms=None,
                is_operational=False,
                loaded_model_count=0,
            ),
            loaded=[],
            failed=[],
            lazy=[],
        ),
    )
    not_started_metadata = await not_started_service.collect()
    results.append(check(
        "Runtime not yet started -> startup_timestamp is None, all counts zero",
        not_started_metadata.startup_timestamp is None
        and not_started_metadata.loaded_model_count == 0
        and not_started_metadata.failed_model_count == 0
        and not_started_metadata.lazy_model_count == 0,
    ))

    # 4. Unexpected adapter failure -> RuntimeMetadataCollectionFailedError, never leaks internals.
    broken_service = RuntimeMetadataService(
        runtime_adapter=FakeRuntimeAdapter(raise_error=True)
    )
    results.append(await run_case(
        "Unexpected RuntimeAdapter failure -> RuntimeMetadataCollectionFailedError",
        broken_service.collect,
        expect_exception=RuntimeMetadataCollectionFailedError,
    ))

    # 5. RuntimeMetadata serialization round-trip (no TensorFlow objects, plain data only).
    dumped = metadata.model_dump()
    rebuilt = RuntimeMetadata.model_validate(dumped)
    results.append(check(
        "RuntimeMetadata serializes to a plain dict and back losslessly",
        rebuilt == metadata
        and dumped["manifest_version"] == "oncovision-manifest-v3"
        and dumped["runtime_version"] == "1.4.0"
        and dumped["loaded_model_count"] == 2,
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
