"""Centralized AI Runtime Manager (ADR-007).

`AIRuntimeManager` is the single source of truth for model lifecycle
management. It is the only component that instantiates `ModelLoader`
calls (and, transitively, TensorFlow model objects); every other part of
the application — prediction services included, in future phases — must
go through this manager rather than touching TensorFlow directly.

Loading strategy is a manifest/priority concern, never a hardcoded model
identity: the top `STARTUP_MODEL_LOAD_LIMIT` enabled models (by ascending
priority) load eagerly at application startup, and every other enabled
model is registered but loaded lazily on first request. Adding, removing,
or reordering models only requires editing the manifest.
"""

import asyncio
import time
from typing import Any

from app.core.logging import get_logger
from app.core.settings import get_settings
from app.ml.cache.cache_manager import ModelCacheManager
from app.ml.downloader.download_manager import ModelDownloadManager
from app.ml.registry.model_registry import ModelRegistry
from app.ml.runtime.exceptions import (
    ModelLoadError,
    ModelUnavailableError,
    RuntimeNotInitializedError,
)
from app.ml.runtime.health import RuntimeHealthService
from app.ml.runtime.loader import ModelLoader
from app.ml.runtime.memory_manager import MemoryManager
from app.ml.runtime.runtime_state import LoadingStrategy, ModelState, RuntimeState
from app.ml.runtime.warmup import ModelWarmupRegistry
from app.ml.schemas import ModelManifestEntry
from app.utils.environment import get_current_timestamp

logger = get_logger(__name__)


class AIRuntimeManager:
    """Singleton responsible for the full lifecycle of registered AI models.

    Exactly one instance exists per process, enforced via `__new__`. The
    first construction wires the manager's collaborators; subsequent
    constructions return the same instance untouched.
    """

    _instance: "AIRuntimeManager | None" = None

    def __new__(cls, *args: object, **kwargs: object) -> "AIRuntimeManager":
        if cls._instance is None:
            instance = super().__new__(cls)
            instance._initialized = False
            cls._instance = instance
        return cls._instance

    def __init__(
        self,
        registry: ModelRegistry,
        download_manager: ModelDownloadManager,
        cache_manager: ModelCacheManager,
    ) -> None:
        if self._initialized:
            return

        self._registry = registry
        self._cache_manager = cache_manager
        self._loader = ModelLoader(download_manager)
        self._state = RuntimeState()
        self._memory_manager = MemoryManager()
        self._warmup_registry = ModelWarmupRegistry()
        self._health_service = RuntimeHealthService(self._state, self._memory_manager)

        self._loaded_instances: dict[str, Any] = {}
        self._load_locks: dict[str, asyncio.Lock] = {}
        self._runtime_initialized = False
        self._initialized = True

    @property
    def health_service(self) -> RuntimeHealthService:
        """Return the reusable runtime health reporting service."""
        return self._health_service

    @property
    def is_initialized(self) -> bool:
        """Return whether the hybrid loading sequence has completed."""
        return self._runtime_initialized

    async def initialize(self) -> None:
        """Run the hybrid model loading sequence.

        Registers every manifest entry, eagerly loads the top
        `STARTUP_MODEL_LOAD_LIMIT` enabled models by priority (sequentially,
        so a slower model never blocks a faster one from being attempted
        first), and registers the remainder for lazy loading. Idempotent:
        subsequent calls are a no-op. Never raises — an individual model
        failure is recorded in its runtime state, not propagated, so the
        application always finishes starting up.
        """
        if self._runtime_initialized:
            return

        started_at = time.perf_counter()
        await self._state.mark_runtime_started()

        all_models = self._registry.get_all_models()
        enabled_models = sorted(
            (model for model in all_models if model.enabled), key=lambda model: model.priority
        )
        disabled_models = [model for model in all_models if not model.enabled]

        startup_limit = get_settings().STARTUP_MODEL_LOAD_LIMIT
        startup_entries = enabled_models[:startup_limit]
        lazy_entries = enabled_models[startup_limit:]
        startup_ids = {model.id for model in startup_entries}

        for model in enabled_models:
            strategy = LoadingStrategy.STARTUP if model.id in startup_ids else LoadingStrategy.LAZY
            await self._state.register(model.id, model.display_name, model.priority, strategy)

        for model in disabled_models:
            await self._state.register(model.id, model.display_name, model.priority, LoadingStrategy.LAZY)
            await self._state.update(model.id, state=ModelState.DISABLED)

        for entry in startup_entries:
            await self._load_entry(entry)

        for entry in lazy_entries:
            logger.info("Model '%s' registered for lazy loading.", entry.id)

        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        await self._state.mark_startup_completed(duration_ms)
        self._runtime_initialized = True

        loaded_count = len(await self._state.by_state(ModelState.READY))
        logger.info(
            "AI Runtime Manager startup sequence completed in %.2fms (%d/%d startup models loaded).",
            duration_ms,
            loaded_count,
            len(startup_entries),
        )

    async def get_model(self, model_id: str) -> Any:
        """Return the loaded model instance for `model_id`, loading it lazily if needed.

        Raises:
            RuntimeNotInitializedError: If called before `initialize()`.
            ModelNotFoundError: If `model_id` is not registered in the manifest.
            ModelUnavailableError: If the model is disabled or fails to load.
        """
        if not self._runtime_initialized:
            raise RuntimeNotInitializedError()

        entry = self._registry.get_model_by_id(model_id)
        info = await self._state.get(model_id)

        if info is not None and info.state == ModelState.READY:
            return self._loaded_instances[model_id]

        if info is not None and info.state == ModelState.DISABLED:
            raise ModelUnavailableError(f"Model '{model_id}' is disabled.")

        await self._load_entry(entry)

        updated = await self._state.get(model_id)
        if updated is None or updated.state != ModelState.READY:
            error_detail = updated.error_message if updated else "unknown error"
            raise ModelUnavailableError(f"Model '{model_id}' could not be loaded: {error_detail}")

        return self._loaded_instances[model_id]

    async def get_loaded_models(self) -> dict[str, Any]:
        """Return a mapping of model ID to loaded instance for every READY model."""
        ready_models = await self._state.by_state(ModelState.READY)
        return {
            model.model_id: self._loaded_instances[model.model_id]
            for model in ready_models
            if model.model_id in self._loaded_instances
        }

    async def get_all_model_status(self) -> list[dict[str, Any]]:
        """Return the runtime status of every registered model, sorted by priority."""
        all_models = await self._state.all()
        return [model.model_dump() for model in sorted(all_models, key=lambda model: model.priority)]

    async def unload_model(self, model_id: str) -> bool:
        """Unload `model_id` from memory, releasing it for garbage collection.

        Returns:
            True if a loaded instance was released, False if the model was
            not currently loaded.
        """
        if model_id not in self._loaded_instances:
            return False

        del self._loaded_instances[model_id]
        self._memory_manager.release(model_id)
        await self._state.update(model_id, state=ModelState.REGISTERED, loaded_at=None)
        logger.info("Model '%s' unloaded from runtime memory.", model_id)
        return True

    async def _load_entry(self, entry: ModelManifestEntry) -> None:
        """Load a single manifest entry, recording every state transition.

        Never raises: all download, checksum, and TensorFlow load failures
        are caught and recorded as a `FAILED` state so the caller (startup
        sequence or lazy `get_model`) always continues cleanly.
        """
        lock = self._get_load_lock(entry.id)
        async with lock:
            current = await self._state.get(entry.id)
            if current is not None and current.state == ModelState.READY:
                return

            attempts = (current.attempts if current else 0) + 1
            await self._state.update(entry.id, state=ModelState.DOWNLOADING, attempts=attempts)

            estimated_mb = self._estimate_memory_mb(entry)
            if not self._memory_manager.has_sufficient_memory(estimated_mb):
                message = (
                    f"Insufficient available memory to load model '{entry.id}' "
                    f"(estimated {estimated_mb} MB required)."
                )
                logger.warning(message)
                await self._state.update(entry.id, state=ModelState.FAILED, error_message=message)
                return

            await self._state.update(entry.id, state=ModelState.DOWNLOADED)
            await self._state.update(entry.id, state=ModelState.LOADING)

            try:
                model, weight_path, duration_ms = await self._loader.load(entry)
            except ModelLoadError as exc:
                logger.error("Model '%s' failed to load: %s", entry.id, exc.message)
                await self._state.update(entry.id, state=ModelState.FAILED, error_message=exc.message)
                return
            except Exception:
                logger.error("Unexpected error loading model '%s'.", entry.id, exc_info=True)
                await self._state.update(
                    entry.id,
                    state=ModelState.FAILED,
                    error_message="An unexpected error occurred while loading the model.",
                )
                return

            memory_mb = self._memory_manager.estimate_model_memory_mb(weight_path)
            self._memory_manager.register_loaded(entry.id, memory_mb)
            self._loaded_instances[entry.id] = model

            await self._state.update(
                entry.id,
                state=ModelState.READY,
                load_duration_ms=duration_ms,
                memory_estimate_mb=memory_mb,
                loaded_at=get_current_timestamp(),
                error_message=None,
            )

            try:
                await self._warmup_registry.run(entry, model)
            except Exception:
                # Warmup is a best-effort optimization; a warmup failure must
                # never invalidate an otherwise successfully loaded model.
                logger.warning("Warmup hook failed for model '%s'.", entry.id, exc_info=True)

            logger.info("Model '%s' loaded successfully in %.2fms.", entry.id, duration_ms)

    def _estimate_memory_mb(self, entry: ModelManifestEntry) -> float:
        """Estimate memory required to load `entry`, using the cache if available."""
        cache_path = self._cache_manager.cache_path(entry)
        return self._memory_manager.estimate_model_memory_mb(cache_path)

    def _get_load_lock(self, model_id: str) -> asyncio.Lock:
        """Return the per-model lock, creating it on first access.

        Prevents duplicate concurrent loads of the same model when
        multiple lazy-load requests race each other.
        """
        lock = self._load_locks.get(model_id)
        if lock is None:
            lock = asyncio.Lock()
            self._load_locks[model_id] = lock
        return lock
