"""Reusable memory-awareness utilities for the AI Runtime Manager.

Provides best-effort memory estimation and availability checks so the
Runtime Manager can make memory-aware loading decisions on
memory-constrained environments such as Render Free (see ADR-007). All
system memory checks are best-effort: if system memory information cannot
be determined, loading is never blocked on that basis, only reported as
unknown.
"""

from pathlib import Path

import psutil

from app.core.logging import get_logger
from app.utils.environment import bytes_to_mb

logger = get_logger(__name__)

# A loaded TensorFlow/Keras model typically consumes noticeably more
# resident memory than its serialized weight file size, due to computation
# graphs, layer activations, and framework overhead. This is a
# conservative, framework-agnostic heuristic used only when the model has
# not been loaded yet and no better estimate is available.
_MODEL_MEMORY_OVERHEAD_FACTOR = 1.5

# Fallback memory reserved for a model whose weight file is not yet cached
# locally, used only for the pre-download availability check.
_DEFAULT_UNCACHED_MODEL_MEMORY_MB = 200.0

# Memory kept in reserve, on top of a model's estimated footprint, so the
# rest of the application (web server, DB pool, OS) is never starved.
_DEFAULT_SAFETY_MARGIN_MB = 150.0


class MemoryManager:
    """Tracks estimated and actual memory usage of loaded AI models."""

    def __init__(self) -> None:
        self._loaded_model_memory_mb: dict[str, float] = {}

    def estimate_model_memory_mb(self, weight_file_path: Path) -> float:
        """Estimate the resident memory a model will use once loaded.

        Uses the on-disk weight file size with a fixed overhead factor.
        Returns the uncached default if `weight_file_path` does not exist.
        """
        if not weight_file_path.is_file():
            return _DEFAULT_UNCACHED_MODEL_MEMORY_MB
        file_size_mb = bytes_to_mb(weight_file_path.stat().st_size)
        return round(file_size_mb * _MODEL_MEMORY_OVERHEAD_FACTOR, 2)

    def get_available_memory_mb(self) -> float | None:
        """Return currently available system memory in MB, or None if unknown."""
        try:
            return bytes_to_mb(psutil.virtual_memory().available)
        except Exception:
            logger.warning("Unable to determine available system memory.", exc_info=True)
            return None

    def get_total_memory_mb(self) -> float | None:
        """Return total system memory in MB, or None if unknown."""
        try:
            return bytes_to_mb(psutil.virtual_memory().total)
        except Exception:
            logger.warning("Unable to determine total system memory.", exc_info=True)
            return None

    def has_sufficient_memory(
        self, required_mb: float, safety_margin_mb: float = _DEFAULT_SAFETY_MARGIN_MB
    ) -> bool:
        """Return whether enough memory is estimated to be available.

        Fails open (returns True) when available memory cannot be
        determined, since the loading failure policy already tolerates and
        recovers from individual model load failures.
        """
        available = self.get_available_memory_mb()
        if available is None:
            return True
        return available >= (required_mb + safety_margin_mb)

    def is_loaded(self, model_id: str) -> bool:
        """Return whether `model_id` is currently tracked as loaded.

        Used by the Runtime Manager to prevent duplicate concurrent loads.
        """
        return model_id in self._loaded_model_memory_mb

    def register_loaded(self, model_id: str, memory_mb: float) -> None:
        """Record the estimated memory footprint of a newly loaded model."""
        self._loaded_model_memory_mb[model_id] = memory_mb

    def release(self, model_id: str) -> None:
        """Remove memory tracking for a model that has been unloaded."""
        self._loaded_model_memory_mb.pop(model_id, None)

    def get_tracked_memory_mb(self) -> float:
        """Return the sum of estimated memory used by all tracked loaded models."""
        return round(sum(self._loaded_model_memory_mb.values()), 2)

    def get_memory_status(self) -> dict[str, float | None]:
        """Return a snapshot of memory status for runtime health reporting."""
        return {
            "available_mb": self.get_available_memory_mb(),
            "total_mb": self.get_total_memory_mb(),
            "tracked_model_memory_mb": self.get_tracked_memory_mb(),
        }
