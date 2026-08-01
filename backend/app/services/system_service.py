"""System service providing application and environment information.

This service is intentionally free of any ML/business logic in Phase 1. It
exposes reusable methods that future services (e.g. model management) can
follow as a pattern.
"""

from app.constants.app import API_V1_PREFIX
from app.core.settings import Settings, get_settings
from app.schemas.common import ApplicationInfo, StoragePaths, SystemInfo
from app.utils.environment import (
    get_current_timestamp,
    get_platform_descriptor,
    get_python_version,
)


class SystemService:
    """Provides read-only information about the application and its environment."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def get_application_info(self) -> ApplicationInfo:
        """Return core application metadata."""
        return ApplicationInfo(
            name=self._settings.APP_NAME,
            version=self._settings.APP_VERSION,
            environment=self._settings.APP_ENV,
            health_endpoint=f"{API_V1_PREFIX}/health",
        )

    def get_storage_status(self) -> StoragePaths:
        """Return the configured storage directory paths."""
        return StoragePaths(
            upload_path=self._settings.UPLOAD_PATH,
            report_path=self._settings.REPORT_PATH,
            model_storage_path=self._settings.MODEL_STORAGE_PATH,
        )

    def get_system_info(self) -> SystemInfo:
        """Return combined application, runtime, and storage information."""
        return SystemInfo(
            application_name=self._settings.APP_NAME,
            version=self._settings.APP_VERSION,
            environment=self._settings.APP_ENV,
            python_version=get_python_version(),
            platform=get_platform_descriptor(),
            current_time=get_current_timestamp(),
            storage=self.get_storage_status(),
        )
