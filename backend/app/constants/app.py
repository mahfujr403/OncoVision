"""Application-wide constant values.

These constants are static and do not change based on environment
configuration. Environment-driven values belong in `app.core.settings`.
"""

from typing import Final

API_V1_PREFIX: Final[str] = "/api/v1"

TAG_HEALTH: Final[str] = "Health"
TAG_SYSTEM: Final[str] = "System"
TAG_AUTH: Final[str] = "Authentication"
TAG_PREDICTIONS: Final[str] = "Predictions"
TAG_PREDICTION_HISTORY: Final[str] = "Prediction History"

REQUEST_ID_HEADER: Final[str] = "X-Request-ID"
PROCESS_TIME_HEADER: Final[str] = "X-Process-Time"

DEFAULT_STORAGE_DIRECTORIES: Final[tuple[str, ...]] = (
    "storage/uploads",
    "storage/reports",
    "storage/models",
)

BYTES_IN_MEGABYTE: Final[int] = 1024 * 1024

# Image formats accepted by the Prediction Engine's image validator. Pillow
# normalizes both ".jpg" and ".jpeg" uploads to the single "JPEG" format
# string, so no separate "JPG" entry is required.
SUPPORTED_IMAGE_FORMATS: Final[frozenset[str]] = frozenset({"JPEG", "PNG", "TIFF"})
