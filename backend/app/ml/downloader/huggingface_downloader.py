"""Hugging Face Hub download infrastructure.

Instantiating `HuggingFaceDownloader` never triggers a network request.
`download_model` / `resume_download` are only invoked explicitly by a
future Model Manager (Phase 3.2) or an admin-triggered action; nothing in
this phase calls them during application startup.
"""

import asyncio
import hashlib
from pathlib import Path

from huggingface_hub import hf_hub_download

from app.core.logging import get_logger
from app.ml.cache.cache_manager import ModelCacheManager
from app.ml.exceptions import ChecksumVerificationError, ModelDownloadError
from app.ml.schemas import ModelManifestEntry

logger = get_logger(__name__)

_CHECKSUM_CHUNK_SIZE = 1024 * 1024


class HuggingFaceDownloader:
    """Downloads model weight files from Hugging Face Hub into the local cache."""

    def __init__(self, cache_manager: ModelCacheManager) -> None:
        self._cache_manager = cache_manager

    async def download_model(self, entry: ModelManifestEntry) -> Path:
        """Download `entry`'s weight file from Hugging Face Hub.

        Raises:
            ModelDownloadError: If the download fails for any reason.
        """
        return await self._download(entry)

    async def resume_download(self, entry: ModelManifestEntry) -> Path:
        """Resume a previously interrupted download for `entry`.

        Hugging Face Hub transparently resumes partially downloaded files
        by default, so this delegates to the same download routine used by
        `download_model`.

        Raises:
            ModelDownloadError: If the download fails for any reason.
        """
        return await self._download(entry)

    def verify_checksum(self, file_path: Path, expected_sha256: str) -> bool:
        """Verify that the file at `file_path` matches `expected_sha256`.

        Raises:
            ChecksumVerificationError: If `file_path` does not exist.
        """
        if not file_path.is_file():
            raise ChecksumVerificationError(
                f"Cannot verify checksum: file '{file_path}' does not exist."
            )

        digest = hashlib.sha256()
        with file_path.open("rb") as model_file:
            for chunk in iter(lambda: model_file.read(_CHECKSUM_CHUNK_SIZE), b""):
                digest.update(chunk)

        return digest.hexdigest().lower() == expected_sha256.lower()

    async def _download(self, entry: ModelManifestEntry) -> Path:
        """Run the blocking Hugging Face Hub download in a worker thread."""
        target_directory = self._cache_manager.cache_path(entry).parent
        try:
            downloaded_path = await asyncio.to_thread(
                hf_hub_download,
                repo_id=entry.repository,
                filename=entry.filename,
                local_dir=str(target_directory),
            )
        except Exception as exc:
            logger.error(
                "Failed to download model '%s' from repository '%s'.",
                entry.id,
                entry.repository,
                exc_info=True,
            )
            raise ModelDownloadError(
                f"Failed to download model '{entry.id}' from '{entry.repository}': {exc}"
            ) from exc

        return Path(downloaded_path)
