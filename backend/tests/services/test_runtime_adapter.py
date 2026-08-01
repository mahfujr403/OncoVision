"""Verification tests for the Phase 4.5.1 Runtime Adapter (ADR-014).

Uses lightweight fakes for the AI Runtime Manager collaborator rather than
a real `AIRuntimeManager` (which requires a download manager, cache
manager, and TensorFlow model loading) -- this phase only verifies the
adapter's own communication and mapping logic, not the runtime manager
itself (already covered by future runtime-focused test modules).

The fakes deliberately do NOT implement `get_model()` or
`get_loaded_models()` (the methods that return live TensorFlow instances
on the real `AIRuntimeManager`) so that any accidental call to them from
`RuntimeAdapter` fails loudly instead of silently leaking model objects.

Not wired into a CI runner in this phase; run standalone with:
    PYTHONPATH=. python3 tests/services/test_runtime_adapter.py
"""

import asyncio

from app.ml.registry.model_registry import ModelRegistry
from app.ml.runtime.runtime_state import LoadingStrategy, ModelRuntimeInfo, ModelState
from app.ml.schemas import ModelManifest, ModelManifestEntry
from app.services.runtime_adapter import (
    RuntimeAdapter,
    RuntimeAvailability,
    RuntimeHealthSummary,
    RuntimeStatusSnapshot,
)

CLASS_LABELS = ["lung_n", "lung_scc", "lung_aca"]


def _manifest_entry(model_id: str, priority: int) -> ModelManifestEntry:
    return ModelManifestEntry(
        id=model_id,
        display_name=model_id.replace("_", " ").title(),
        version="1.0.0",
        framework="tensorflow",
        format="h5",
        repository="oncovision-ai/models",
        filename=f"{model_id}.h5",
        priority=priority,
        ensemble_weight=0.5,
        input_size=224,
        num_classes=len(CLASS_LABELS),
        class_labels=CLASS_LABELS,
        sha256="a" * 64,
        enabled=True,
        description=f"Test manifest entry for {model_id}.",
    )


def make_registry(version: str = "test-manifest-v1") -> ModelRegistry:
    manifest = ModelManifest(
        manifest_version=version,
        models=[
            _manifest_entry("mobilenet_v2", priority=1),
            _manifest_entry("densenet_121", priority=2),
        ],
    )
    return ModelRegistry(manifest)


def make_runtime_info(model_id: str, state: ModelState, **overrides) -> ModelRuntimeInfo:
    return ModelRuntimeInfo(
        model_id=model_id,
        display_name=model_id.replace("_", " ").title(),
        priority=1,
        loading_strategy=LoadingStrategy.STARTUP,
        state=state,
        **overrides,
    )


class FakeHealthService:
    """Duck-typed stand-in for `RuntimeHealthService`.

    Intentionally exposes only the read-only, metadata-returning methods
    `RuntimeAdapter` is allowed to call.
    """

    def __init__(
        self,
        loaded: list[ModelRuntimeInfo],
        failed: list[ModelRuntimeInfo],
        status: dict,
    ) -> None:
        self._loaded = loaded
        self._failed = failed
        self._status = status

    async def loaded_models(self) -> list[ModelRuntimeInfo]:
        return self._loaded

    async def failed_models(self) -> list[ModelRuntimeInfo]:
        return self._failed

    async def runtime_status(self) -> dict:
        return self._status


class FakeRuntimeManager:
    """Duck-typed stand-in for `AIRuntimeManager`.

    Deliberately omits `get_model()` and `get_loaded_models()` -- the
    methods on the real manager that return live TensorFlow instances --
    so `RuntimeAdapter` calling either by mistake fails the test instead
    of silently succeeding.
    """

    def __init__(self, health_service: FakeHealthService, is_initialized: bool) -> None:
        self.health_service = health_service
        self.is_initialized = is_initialized


def check(name: str, condition: bool) -> bool:
    print(f"[{'PASS' if condition else 'FAIL'}] {name}")
    return condition


async def main() -> None:
    results: list[bool] = []
    registry = make_registry()

    # 1. Runtime reachable, fully operational: every loaded model is ready,
    #    nothing failed.
    loaded = [
        make_runtime_info("mobilenet_v2", ModelState.READY),
        make_runtime_info("densenet_121", ModelState.READY),
    ]
    operational_status = {
        "runtime_started": True,
        "runtime_started_at": "2026-07-20T00:00:00Z",
        "startup_completed_at": "2026-07-20T00:00:05Z",
        "startup_duration_ms": 5000.0,
        "is_operational": True,
        "total_model_count": 2,
        "loaded_model_count": 2,
        "failed_model_count": 0,
        "pending_model_count": 0,
        "disabled_model_count": 0,
        "memory_status": {
            "available_mb": 512.0,
            "total_mb": 2048.0,
            "tracked_model_memory_mb": 300.0,
        },
        "models": [m.model_dump() for m in loaded],
    }
    operational_adapter = RuntimeAdapter(
        runtime_manager=FakeRuntimeManager(
            FakeHealthService(loaded=loaded, failed=[], status=operational_status),
            is_initialized=True,
        ),
        registry=registry,
    )

    health = await operational_adapter.get_runtime_health()
    results.append(check(
        "Runtime reachable and fully operational -> RuntimeAvailability.OPERATIONAL",
        isinstance(health, RuntimeHealthSummary)
        and health.availability == RuntimeAvailability.OPERATIONAL
        and health.is_initialized is True
        and health.loaded_model_count == 2
        and health.failed_model_count == 0,
    ))

    status_snapshot = await operational_adapter.get_runtime_status()
    results.append(check(
        "get_runtime_status() maps the health-service snapshot into RuntimeStatusSnapshot",
        isinstance(status_snapshot, RuntimeStatusSnapshot)
        and status_snapshot.loaded_model_count == 2
        and status_snapshot.is_operational is True
        and status_snapshot.memory_status.available_mb == 512.0
        and len(status_snapshot.models) == 2,
    ))

    loaded_models = await operational_adapter.get_loaded_models()
    results.append(check(
        "get_loaded_models() returns metadata-only ModelRuntimeInfo entries",
        len(loaded_models) == 2
        and all(isinstance(m, ModelRuntimeInfo) for m in loaded_models)
        and not any(hasattr(m, "predict") for m in loaded_models),
    ))

    # 2. Degraded: at least one model ready, at least one failed.
    degraded_loaded = [make_runtime_info("mobilenet_v2", ModelState.READY)]
    degraded_failed = [
        make_runtime_info(
            "densenet_121", ModelState.FAILED, error_message="Insufficient memory."
        )
    ]
    degraded_adapter = RuntimeAdapter(
        runtime_manager=FakeRuntimeManager(
            FakeHealthService(
                loaded=degraded_loaded,
                failed=degraded_failed,
                status={**operational_status, "loaded_model_count": 1, "failed_model_count": 1},
            ),
            is_initialized=True,
        ),
        registry=registry,
    )
    degraded_health = await degraded_adapter.get_runtime_health()
    results.append(check(
        "One ready + one failed model -> RuntimeAvailability.DEGRADED",
        degraded_health.availability == RuntimeAvailability.DEGRADED,
    ))

    failed_models = await degraded_adapter.get_failed_models()
    results.append(check(
        "get_failed_models() surfaces the failure reason",
        len(failed_models) == 1
        and failed_models[0].error_message == "Insufficient memory.",
    ))

    # 3. Runtime unavailable: not initialized, nothing loaded.
    unavailable_adapter = RuntimeAdapter(
        runtime_manager=FakeRuntimeManager(
            FakeHealthService(loaded=[], failed=[], status={**operational_status, "models": []}),
            is_initialized=False,
        ),
        registry=registry,
    )
    unavailable_health = await unavailable_adapter.get_runtime_health()
    results.append(check(
        "No loaded models and uninitialized runtime -> RuntimeAvailability.UNAVAILABLE",
        unavailable_health.availability == RuntimeAvailability.UNAVAILABLE
        and unavailable_health.is_initialized is False,
    ))

    # 4. Metadata retrieval: manifest version comes from the injected
    #    ModelRegistry, independent of runtime state.
    results.append(check(
        "get_manifest_version() reflects the injected ModelRegistry",
        operational_adapter.get_manifest_version() == "test-manifest-v1"
        and unavailable_adapter.get_manifest_version() == "test-manifest-v1",
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
