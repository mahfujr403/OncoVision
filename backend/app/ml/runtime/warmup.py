"""Model warmup infrastructure.

Prepares, but never executes, per-model warmup routines. Real
inference-based warmup (e.g. a single dummy forward pass to pre-build the
TensorFlow computation graph) belongs to a future phase once prediction
logic exists; this module only defines the extension point so the Runtime
Manager can invoke warmup uniformly once such hooks are registered.
"""

from typing import Any, Awaitable, Callable

from app.ml.schemas import ModelManifestEntry

WarmupHook = Callable[[ModelManifestEntry, Any], Awaitable[None]]


class ModelWarmupRegistry:
    """Registers and runs per-model warmup hooks without performing inference.

    No hooks are registered by this phase. Future phases can register a
    real warmup callable per model ID via `register`; until then, `run` is
    a no-op for every model.
    """

    def __init__(self) -> None:
        self._hooks: dict[str, WarmupHook] = {}

    def register(self, model_id: str, hook: WarmupHook) -> None:
        """Register a warmup hook to run immediately after `model_id` loads."""
        self._hooks[model_id] = hook

    def is_registered(self, model_id: str) -> bool:
        """Return whether a warmup hook is registered for `model_id`."""
        return model_id in self._hooks

    async def run(self, entry: ModelManifestEntry, model: Any) -> None:
        """Run the registered warmup hook for `entry`, if any.

        No-op when no hook is registered for `entry.id`.
        """
        hook = self._hooks.get(entry.id)
        if hook is None:
            return
        await hook(entry, model)
