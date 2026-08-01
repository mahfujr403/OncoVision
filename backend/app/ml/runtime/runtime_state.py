"""In-memory runtime state tracking for the AI Runtime Manager.

Tracks the lifecycle state of every registered model, plus aggregate
runtime timing, in a single async-safe store. No module outside
`app.ml.runtime` should mutate this state directly; the `AIRuntimeManager`
is the sole writer, while `RuntimeHealthService` and API layers only read
from it.
"""

import asyncio
from enum import Enum

from pydantic import BaseModel, Field

from app.utils.environment import get_current_timestamp


class ModelState(str, Enum):
    """Lifecycle states a registered model can occupy within the runtime."""

    REGISTERED = "registered"
    DOWNLOADING = "downloading"
    DOWNLOADED = "downloaded"
    LOADING = "loading"
    READY = "ready"
    FAILED = "failed"
    DISABLED = "disabled"


class LoadingStrategy(str, Enum):
    """When a registered model is loaded relative to application startup."""

    STARTUP = "startup"
    LAZY = "lazy"


class ModelRuntimeInfo(BaseModel):
    """Runtime lifecycle snapshot for a single registered model."""

    model_id: str = Field(description="Unique identifier for the model.")
    display_name: str = Field(description="Human-readable model name.")
    priority: int = Field(description="Loading priority; lower values load first.")
    loading_strategy: LoadingStrategy = Field(
        description="Whether this model is loaded at startup or lazily on demand."
    )
    state: ModelState = Field(
        default=ModelState.REGISTERED, description="Current runtime lifecycle state."
    )
    error_message: str | None = Field(
        default=None, description="Failure reason, populated only when state is FAILED."
    )
    load_duration_ms: float | None = Field(
        default=None, description="How long the most recent load attempt took, in milliseconds."
    )
    memory_estimate_mb: float | None = Field(
        default=None, description="Estimated resident memory footprint once loaded, in megabytes."
    )
    loaded_at: str | None = Field(
        default=None, description="ISO 8601 timestamp of the most recent successful load."
    )
    attempts: int = Field(default=0, description="Number of load attempts made for this model.")


class RuntimeState:
    """Async-safe in-memory store of model runtime information."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._models: dict[str, ModelRuntimeInfo] = {}
        self._runtime_started_at: str | None = None
        self._startup_completed_at: str | None = None
        self._startup_duration_ms: float | None = None

    async def register(
        self,
        model_id: str,
        display_name: str,
        priority: int,
        loading_strategy: LoadingStrategy,
    ) -> None:
        """Register a model with the runtime in its initial `REGISTERED` state."""
        async with self._lock:
            self._models[model_id] = ModelRuntimeInfo(
                model_id=model_id,
                display_name=display_name,
                priority=priority,
                loading_strategy=loading_strategy,
            )

    async def update(self, model_id: str, **fields: object) -> None:
        """Apply a partial update to a registered model's runtime info.

        No-op if `model_id` has not been registered.
        """
        async with self._lock:
            info = self._models.get(model_id)
            if info is None:
                return
            self._models[model_id] = info.model_copy(update=fields)

    async def mark_runtime_started(self) -> None:
        """Record the timestamp the runtime began its initialization sequence."""
        async with self._lock:
            self._runtime_started_at = get_current_timestamp()

    async def mark_startup_completed(self, duration_ms: float) -> None:
        """Record that the startup loading phase has finished."""
        async with self._lock:
            self._startup_completed_at = get_current_timestamp()
            self._startup_duration_ms = duration_ms

    async def get(self, model_id: str) -> ModelRuntimeInfo | None:
        """Return a copy of `model_id`'s runtime info, or None if unregistered."""
        async with self._lock:
            info = self._models.get(model_id)
            return info.model_copy() if info else None

    async def all(self) -> list[ModelRuntimeInfo]:
        """Return copies of every registered model's runtime info."""
        async with self._lock:
            return [info.model_copy() for info in self._models.values()]

    async def by_state(self, state: ModelState) -> list[ModelRuntimeInfo]:
        """Return runtime info for every model currently in `state`."""
        return [info for info in await self.all() if info.state == state]

    async def by_loading_strategy(self, strategy: LoadingStrategy) -> list[ModelRuntimeInfo]:
        """Return runtime info for every model registered with `strategy`.

        Reflects the manifest-driven loading strategy assigned during
        `AIRuntimeManager.initialize()`, independent of a model's current
        lifecycle `state` (e.g. a `LAZY` model may still be `REGISTERED`,
        or already `READY` after being loaded on first request).
        """
        return [info for info in await self.all() if info.loading_strategy == strategy]

    @property
    def runtime_started_at(self) -> str | None:
        """ISO 8601 timestamp the runtime began initializing, or None if not yet started."""
        return self._runtime_started_at

    @property
    def startup_completed_at(self) -> str | None:
        """ISO 8601 timestamp startup loading finished, or None if not yet complete."""
        return self._startup_completed_at

    @property
    def startup_duration_ms(self) -> float | None:
        """How long the startup loading phase took, in milliseconds."""
        return self._startup_duration_ms
