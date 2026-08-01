"""Reusable runtime health reporting service.

Derives health, statistics, and per-model status views purely by reading
the `RuntimeState` and `MemoryManager` maintained by the
`AIRuntimeManager`. Performs no model loading itself.
"""

from typing import Any

from app.ml.runtime.memory_manager import MemoryManager
from app.ml.runtime.runtime_state import LoadingStrategy, ModelRuntimeInfo, ModelState, RuntimeState

_PENDING_STATES = frozenset(
    {
        ModelState.REGISTERED,
        ModelState.DOWNLOADING,
        ModelState.DOWNLOADED,
        ModelState.LOADING,
    }
)


class RuntimeHealthService:
    """Reports on the current health and status of the AI runtime."""

    def __init__(self, state: RuntimeState, memory_manager: MemoryManager) -> None:
        self._state = state
        self._memory_manager = memory_manager

    async def loaded_models(self) -> list[ModelRuntimeInfo]:
        """Return runtime info for every model currently in the READY state."""
        return await self._state.by_state(ModelState.READY)

    async def failed_models(self) -> list[ModelRuntimeInfo]:
        """Return runtime info for every model currently in the FAILED state."""
        return await self._state.by_state(ModelState.FAILED)

    async def pending_models(self) -> list[ModelRuntimeInfo]:
        """Return runtime info for models not yet READY, FAILED, or DISABLED."""
        all_models = await self._state.all()
        return [model for model in all_models if model.state in _PENDING_STATES]

    async def lazy_models(self) -> list[ModelRuntimeInfo]:
        """Return runtime info for every model registered with the LAZY loading strategy.

        Reflects manifest-driven loading configuration (ADR-007), not
        current lifecycle state -- a lazy model may still be pending its
        first request, or already READY if it has since been demanded.
        """
        return await self._state.by_loading_strategy(LoadingStrategy.LAZY)

    async def runtime_status(self) -> dict[str, Any]:
        """Return a complete runtime health snapshot."""
        all_models = await self._state.all()
        loaded = [model for model in all_models if model.state == ModelState.READY]
        failed = [model for model in all_models if model.state == ModelState.FAILED]
        pending = [model for model in all_models if model.state in _PENDING_STATES]
        disabled = [model for model in all_models if model.state == ModelState.DISABLED]
        sorted_models = sorted(all_models, key=lambda model: model.priority)

        return {
            "runtime_started": self._state.runtime_started_at is not None,
            "runtime_started_at": self._state.runtime_started_at,
            "startup_completed_at": self._state.startup_completed_at,
            "startup_duration_ms": self._state.startup_duration_ms,
            "is_operational": len(loaded) > 0,
            "total_model_count": len(all_models),
            "loaded_model_count": len(loaded),
            "failed_model_count": len(failed),
            "pending_model_count": len(pending),
            "disabled_model_count": len(disabled),
            "memory_status": self._memory_manager.get_memory_status(),
            "models": [model.model_dump() for model in sorted_models],
        }
