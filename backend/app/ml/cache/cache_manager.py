"""Manages the local on-disk cache of downloaded model weight files.

Render Free has an ephemeral filesystem (see ADR-003), so this cache is
best-effort within a single running instance; models are re-downloaded on
cold starts if missing.
"""

from pathlib import Path

from app.core.settings import get_settings
from app.ml.schemas import ModelManifestEntry


class ModelCacheManager:
    """Encapsulates all local filesystem access for cached model weight files."""

    def __init__(self, cache_directory: str | Path | None = None) -> None:
        self._cache_directory = Path(cache_directory or get_settings().MODEL_STORAGE_PATH)
        self._cache_directory.mkdir(parents=True, exist_ok=True)

    def cache_path(self, entry: ModelManifestEntry) -> Path:
        """Return the local filesystem path where `entry`'s weight file is cached."""
        return self._cache_directory / entry.filename

    def is_cached(self, entry: ModelManifestEntry) -> bool:
        """Return whether `entry`'s weight file is present and non-empty in the cache."""
        path = self.cache_path(entry)
        return path.is_file() and path.stat().st_size > 0

    def remove_cache(self, entry: ModelManifestEntry) -> bool:
        """Remove `entry`'s cached weight file, if present.

        Returns:
            True if a file was removed, False if nothing was cached.
        """
        path = self.cache_path(entry)
        if not path.is_file():
            return False
        path.unlink()
        return True

    def list_cached_models(self) -> list[str]:
        """Return the filenames of all files currently present in the cache directory."""
        if not self._cache_directory.exists():
            return []
        return sorted(item.name for item in self._cache_directory.iterdir() if item.is_file())
