"""Prediction Runtime Adapter (Phase 4.5.1 - ADR-014).

`RuntimeAdapter` is the only communication boundary `PredictionService` is
allowed to use to reach the AI Runtime Manager (ADR-013, ADR-014).
`PredictionService` must never hold a direct reference to `AIRuntimeManager`
or `ModelRegistry` -- it depends on `RuntimeAdapter` instead, which hides
`AIRuntimeManager`'s and `ModelRegistry`'s implementation details behind a
small, stable, metadata-only surface.

This phase only wires the communication layer. No image preprocessing, no
model inference, and no TensorFlow execution happen here or are triggered
by any method on this class -- every method is a read-only projection of
runtime and manifest metadata already tracked by the AI Runtime Manager
(Phase 3.2) and Model Registry (Phase 3.1).

Every value returned by this adapter is a plain, serializable Pydantic
model or primitive. `AIRuntimeManager.get_model()` and
`AIRuntimeManager.get_loaded_models()` -- which return live TensorFlow
model instances -- are intentionally never called from this module.

Future runtime implementations (ONNX, PyTorch, TFLite) only ever need to
satisfy `AIRuntimeManager`'s existing surface; `RuntimeAdapter` itself
never has to change for that reason (ADR-007, ADR-014).
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.logging import get_logger
from app.ml.registry.model_registry import ModelRegistry
from app.ml.runtime.runtime_manager import AIRuntimeManager
from app.ml.runtime.runtime_state import ModelRuntimeInfo

logger = get_logger(__name__)


class RuntimeAvailability(str, Enum):
    """Qualitative AI Runtime availability bucket, owned by the service layer.

    Intentionally distinct from
    `app.api.v1.predictions.responses.RuntimeHealthStatus` -- the public API
    projection (ADR-012) -- so the service layer never depends on API-layer
    schema modules (see `app.services.prediction_result` for the same
    principle applied to prediction output).
    """

    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class MemoryStatusSnapshot(BaseModel):
    """Best-effort system memory snapshot, as reported by the runtime's `MemoryManager`."""

    model_config = ConfigDict(frozen=True)

    available_mb: float | None = Field(
        default=None, description="Currently available system memory, in megabytes."
    )
    total_mb: float | None = Field(
        default=None, description="Total system memory, in megabytes."
    )
    tracked_model_memory_mb: float = Field(
        description="Sum of estimated memory used by all currently loaded models, in megabytes."
    )


class RuntimeStatusSnapshot(BaseModel):
    """Complete AI Runtime status snapshot exposed to `PredictionService`.

    A metadata-only projection of `RuntimeHealthService.runtime_status()`.
    Never contains loaded model instances.
    """

    model_config = ConfigDict(frozen=True)

    runtime_started: bool = Field(
        description="Whether the runtime has begun its initialization sequence."
    )
    runtime_started_at: str | None = Field(
        default=None, description="ISO 8601 timestamp the runtime began initializing."
    )
    startup_completed_at: str | None = Field(
        default=None, description="ISO 8601 timestamp the startup loading phase finished."
    )
    startup_duration_ms: float | None = Field(
        default=None, description="How long the startup loading phase took, in milliseconds."
    )
    is_operational: bool = Field(
        description="Whether at least one production model is currently loaded and ready."
    )
    total_model_count: int = Field(description="Total number of registered models.")
    loaded_model_count: int = Field(description="Number of models currently in the READY state.")
    failed_model_count: int = Field(description="Number of models currently in the FAILED state.")
    pending_model_count: int = Field(
        description="Number of models still registering, downloading, or loading."
    )
    disabled_model_count: int = Field(
        description="Number of models disabled in the Model Manifest."
    )
    memory_status: MemoryStatusSnapshot = Field(
        description="Best-effort system and tracked-model memory snapshot."
    )
    models: list[ModelRuntimeInfo] = Field(
        description="Per-model runtime lifecycle status, sorted by loading priority."
    )


class RuntimeHealthSummary(BaseModel):
    """Lightweight AI Runtime health summary for fast pipeline pre-checks.

    Cheaper than `RuntimeStatusSnapshot` when `PredictionService` only needs
    to decide whether it is worth proceeding into the prediction pipeline,
    not the full per-model breakdown.
    """

    model_config = ConfigDict(frozen=True)

    availability: RuntimeAvailability = Field(
        description="Qualitative AI Runtime availability bucket."
    )
    is_initialized: bool = Field(
        description="Whether the runtime has completed its startup loading sequence."
    )
    loaded_model_count: int = Field(description="Number of models currently in the READY state.")
    failed_model_count: int = Field(description="Number of models currently in the FAILED state.")


class RuntimeAdapter:
    """Abstracts `AIRuntimeManager` and `ModelRegistry` behind a stable, metadata-only surface.

    `PredictionService` communicates only through this adapter (ADR-014).
    `RuntimeManager` and `ModelRegistry` are both injected explicitly --
    never accessed as module-level singletons -- so `RuntimeAdapter` remains
    easy to unit test with fakes or mocks.
    """

    def __init__(self, runtime_manager: AIRuntimeManager, registry: ModelRegistry) -> None:
        self._runtime_manager = runtime_manager
        self._registry = registry

    async def get_runtime_status(self) -> RuntimeStatusSnapshot:
        """Return the complete AI Runtime status snapshot.

        Delegates entirely to `AIRuntimeManager.health_service`, which reads
        runtime state without performing any model loading or inference.
        """
        snapshot: dict[str, Any] = await self._runtime_manager.health_service.runtime_status()
        return RuntimeStatusSnapshot.model_validate(snapshot)

    async def get_loaded_models(self) -> list[ModelRuntimeInfo]:
        """Return runtime metadata for every model currently in the READY state.

        Returns model metadata only -- never the underlying TensorFlow model
        instances held internally by `AIRuntimeManager`.
        """
        return await self._runtime_manager.health_service.loaded_models()

    async def get_failed_models(self) -> list[ModelRuntimeInfo]:
        """Return runtime metadata for every model currently in the FAILED state, with failure reasons."""
        return await self._runtime_manager.health_service.failed_models()

    async def get_lazy_models(self) -> list[ModelRuntimeInfo]:
        """Return runtime metadata for every model registered with the LAZY loading strategy.

        Reflects the Model Manifest's loading configuration (ADR-007), not
        current lifecycle state -- a lazy model may already be READY if it
        has been demanded at least once since startup.
        """
        return await self._runtime_manager.health_service.lazy_models()

    async def get_runtime_health(self) -> RuntimeHealthSummary:
        """Return a lightweight qualitative health summary of the AI Runtime.

        Availability buckets:
            - OPERATIONAL: every registered, enabled model is loaded and ready.
            - DEGRADED: at least one model is ready, but not every model is.
            - UNAVAILABLE: no model is currently ready (ADR-005, ADR-009).
        """
        loaded = await self._runtime_manager.health_service.loaded_models()
        failed = await self._runtime_manager.health_service.failed_models()

        loaded_count = len(loaded)
        failed_count = len(failed)

        if loaded_count == 0:
            availability = RuntimeAvailability.UNAVAILABLE
        elif failed_count > 0:
            availability = RuntimeAvailability.DEGRADED
        else:
            availability = RuntimeAvailability.OPERATIONAL

        return RuntimeHealthSummary(
            availability=availability,
            is_initialized=self._runtime_manager.is_initialized,
            loaded_model_count=loaded_count,
            failed_model_count=failed_count,
        )

    def get_manifest_version(self) -> str:
        """Return the version identifier of the currently loaded Model Manifest."""
        return self._registry.manifest_version

    def get_frameworks(self) -> list[str]:
        """Return the distinct ML frameworks used by every registered model.

        Sourced from the Model Manifest via `ModelRegistry` (ADR-006) --
        never hardcoded -- so a future ONNX, PyTorch, or TFLite model
        registered in the manifest is reflected here without any change to
        this adapter (ADR-007).
        """
        frameworks = {model.framework for model in self._registry.get_all_models()}
        return sorted(frameworks)
