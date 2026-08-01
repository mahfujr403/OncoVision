"""Global API response envelope schema.

Every API response in the application follows this consistent structure to
simplify client-side handling and error processing.
"""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

DataT = TypeVar("DataT")


class APIResponse(BaseModel, Generic[DataT]):
    """Standard API response envelope used across the entire application."""

    success: bool = Field(description="Whether the request completed successfully.")
    message: str = Field(default="", description="Human-readable response message.")
    data: DataT | None = Field(default=None, description="Response payload.")
    errors: Any | None = Field(default=None, description="Structured error details, if any.")
    request_id: str = Field(default="", description="Unique identifier for this request.")
    timestamp: str = Field(description="ISO 8601 timestamp of the response.")
