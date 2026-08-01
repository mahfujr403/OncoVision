"""General-purpose utility helpers used across the application."""

import platform
import uuid
from datetime import datetime, timezone


def get_current_timestamp() -> str:
    """Return the current UTC timestamp formatted as an ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def generate_request_id() -> str:
    """Generate a unique request identifier."""
    return str(uuid.uuid4())


def bytes_to_mb(size_in_bytes: int) -> float:
    """Convert a byte count to megabytes, rounded to two decimal places.

    Args:
        size_in_bytes: Size in bytes.

    Returns:
        The equivalent size in megabytes.
    """
    return round(size_in_bytes / (1024 * 1024), 2)


def get_python_version() -> str:
    """Return the currently running Python interpreter version."""
    return platform.python_version()


def get_platform_descriptor() -> str:
    """Return a human-readable operating system platform descriptor."""
    return f"{platform.system()} {platform.release()} ({platform.machine()})"
