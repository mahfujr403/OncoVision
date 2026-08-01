"""Orchestrates the model registry, local cache, and Hugging Face downloader.

This is coordination-only infrastructure for future phases. No method here
is invoked during application startup; Phase 3.2's Model Manager will call
`ensure_model_available` when a model actually needs to be loaded.
"""

from pathlib import Path
from typing import Any

from app.core.logging import get_logger
from app.ml.cache.cache_manager import ModelCacheManager
from app.ml.downloader.huggingface_downloader import HuggingFaceDownloader
from app.ml.exceptions import ChecksumVerificationError
from app.ml.registry.model_registry import ModelRegistry

logger = get_logger(__name__)


class ModelDownloadManager:
    """Coordinates availability checks, downloads, and checksum verification."""

    def __init__(
        self,
        registry: ModelRegistry,
        cache_manager: ModelCacheManager,
        downloader: HuggingFaceDownloader,
    ) -> None:
        self._registry = registry
        self._cache_manager = cache_manager
        self._downloader = downloader

    async def ensure_model_available(self, model_id: str) -> Path:
        """Ensure a valid, checksum-verified copy of `model_id` exists locally.

        Returns the cached copy if present and valid; otherwise downloads it,
        verifies its checksum, and returns the resulting path.

        Raises:
            ModelNotFoundError: If `model_id` is not registered.
            ModelDownloadError: If the download fails.
            ChecksumVerificationError: If the file fails checksum verification.
        """
        entry = self._registry.get_model_by_id(model_id)

        if self._cache_manager.is_cached(entry):
            cached_path = self._cache_manager.cache_path(entry)
            if self._downloader.verify_checksum(cached_path, entry.sha256):
                return cached_path
            logger.warning(
                "Cached model '%s' failed checksum verification; re-downloading.", model_id
            )
            self._cache_manager.remove_cache(entry)

        downloaded_path = await self._downloader.download_model(entry)
        if not self._downloader.verify_checksum(downloaded_path, entry.sha256):
            self._cache_manager.remove_cache(entry)
            raise ChecksumVerificationError(
                f"Downloaded model '{model_id}' failed checksum verification."
            )
        return downloaded_path

    def get_download_status(self, model_id: str) -> dict[str, Any]:
        """Return the current cache status for `model_id` without downloading it.

        Raises:
            ModelNotFoundError: If `model_id` is not registered.
        """
        entry = self._registry.get_model_by_id(model_id)
        return {
            "model_id": entry.id,
            "is_cached": self._cache_manager.is_cached(entry),
            "cache_path": str(self._cache_manager.cache_path(entry)),
        }
