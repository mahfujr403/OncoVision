"""Application configuration entry point.

Exposes the resolved `settings` singleton and configuration-related helper
functions used during application startup (e.g. storage directory
validation). Business logic should import `settings` from this module.
"""

from pathlib import Path

from app.core.settings import Settings, get_settings

settings: Settings = get_settings()


def get_storage_directories(current_settings: Settings | None = None) -> list[Path]:
    """Return the list of storage directories that must exist at runtime.

    Args:
        current_settings: Optional settings override, primarily for testing.

    Returns:
        A list of `Path` objects for upload, report, and model storage.
    """
    active_settings = current_settings or settings
    return [
        Path(active_settings.UPLOAD_PATH),
        Path(active_settings.REPORT_PATH),
        Path(active_settings.MODEL_STORAGE_PATH),
    ]


def ensure_storage_directories(current_settings: Settings | None = None) -> None:
    """Create configured storage directories if they do not already exist."""
    for directory in get_storage_directories(current_settings):
        directory.mkdir(parents=True, exist_ok=True)
