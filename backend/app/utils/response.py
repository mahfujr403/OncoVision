"""Helper functions for constructing the standard API response envelope."""

from typing import Any

import orjson
from fastapi import status
from fastapi.responses import ORJSONResponse

from app.utils.environment import generate_request_id, get_current_timestamp


def _default_serializer(obj: Any) -> str:
    """
    Fallback serializer for objects that ORJSON cannot serialize.

    Examples:
        - ValueError
        - UUID (if needed)
        - Decimal
        - Any custom object
    """
    return str(obj)


class CustomORJSONResponse(ORJSONResponse):
    """Custom ORJSON response with fallback serialization."""

    def render(self, content: Any) -> bytes:
        return orjson.dumps(
            content,
            default=_default_serializer,
        )


def success_response(
    data: Any | None = None,
    message: str = "Request completed successfully.",
    status_code: int = status.HTTP_200_OK,
    request_id: str | None = None,
) -> CustomORJSONResponse:
    """
    Build a standardized success JSON response.
    """

    payload = {
        "success": True,
        "message": message,
        "data": data,
        "errors": None,
        "request_id": request_id or generate_request_id(),
        "timestamp": get_current_timestamp(),
    }

    return CustomORJSONResponse(
        content=payload,
        status_code=status_code,
    )


def error_response(
    message: str = "An error occurred.",
    status_code: int = status.HTTP_400_BAD_REQUEST,
    errors: Any | None = None,
    request_id: str | None = None,
) -> CustomORJSONResponse:
    """
    Build a standardized error JSON response.
    """

    payload = {
        "success": False,
        "message": message,
        "data": None,
        "errors": errors,
        "request_id": request_id or generate_request_id(),
        "timestamp": get_current_timestamp(),
    }

    return CustomORJSONResponse(
        content=payload,
        status_code=status_code,
    )