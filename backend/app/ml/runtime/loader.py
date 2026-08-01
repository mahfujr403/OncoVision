"""TensorFlow model loading infrastructure.

Per ADR-007, only the AI Runtime Manager may create TensorFlow model
instances, and it does so exclusively through this module. `ModelLoader`
never performs inference; it only turns a validated, locally cached
weight file into a loaded Keras model instance ready for future
prediction services to use.
"""

import asyncio
import time
from pathlib import Path
from typing import Any

from app.core.logging import get_logger
from app.ml.downloader.download_manager import ModelDownloadManager
from app.ml.exceptions import ChecksumVerificationError, ModelDownloadError
from app.ml.runtime.exceptions import ModelLoadError
from app.ml.schemas import ModelManifestEntry

logger = get_logger(__name__)


class ModelLoader:
    """Ensures a model's weight file is available, then loads it into memory."""

    def __init__(self, download_manager: ModelDownloadManager) -> None:
        self._download_manager = download_manager

    async def load(self, entry: ModelManifestEntry) -> tuple[Any, Path, float]:
        """Ensure `entry` is downloaded and verified, then load it into memory.

        Returns:
            A tuple of `(model_instance, weight_file_path, load_duration_ms)`.

        Raises:
            ModelLoadError: If the download, checksum verification, or the
                TensorFlow load itself fails.
        """
        started_at = time.perf_counter()

        try:
            weight_path = await self._download_manager.ensure_model_available(entry.id)
        except (ModelDownloadError, ChecksumVerificationError) as exc:
            raise ModelLoadError(
                f"Model '{entry.id}' could not be prepared for loading: {exc.message}"
            ) from exc

        model = await self._load_into_memory(entry, weight_path)

        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        return model, weight_path, duration_ms

    async def _load_into_memory(self, entry: ModelManifestEntry, weight_path: Path) -> Any:
        """Run the blocking TensorFlow model load in a worker thread."""
        try:
            return await asyncio.to_thread(self._load_model_sync, weight_path)
        except ModelLoadError:
            raise
        except Exception as exc:
            logger.error("Failed to load model '%s' into memory.", entry.id, exc_info=True)
            raise ModelLoadError(f"Model '{entry.id}' failed to load: {exc}") from exc

    @staticmethod
    def _load_model_sync(weight_path: Path) -> Any:
        """Synchronously load a Keras `.h5` model file.

        The `tensorflow` import is deferred to call time so the rest of the
        application can start and serve non-ML endpoints even in
        environments where the (heavyweight) TensorFlow dependency is
        temporarily unavailable; such a failure surfaces as a `FAILED`
        model state rather than a startup crash.
        """
        try:
            import tensorflow as tf
        except ImportError as exc:
            raise ModelLoadError(
                "TensorFlow is not installed; cannot load model weight files."
            ) from exc

        return tf.keras.models.load_model(str(weight_path), compile=False)
