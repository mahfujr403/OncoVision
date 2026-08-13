"""OpenAPI/Swagger documentation examples for the Admin API (Phase 7.6).

Plain dictionaries only -- no schema construction or validation happens
here. Mirrors `app.api.v1.predictions.examples`: each constant is wired
into a router's `responses={...}` mapping so Swagger renders a concrete
example for every documented status code.
"""

from typing import Any, Final

FORBIDDEN_ERROR_EXAMPLE: Final[dict[str, Any]] = {
    "success": False,
    "message": "You do not have permission to perform this action.",
    "data": None,
    "errors": None,
    "request_id": "6f7a8b9c-0d1e-4f2a-3b4c-5d6e7f809162",
    "timestamp": "2026-07-19T10:00:05Z",
}

ADMIN_USER_NOT_FOUND_EXAMPLE: Final[dict[str, Any]] = {
    "success": False,
    "message": "The requested user was not found.",
    "data": None,
    "errors": None,
    "request_id": "7a8b9c0d-1e2f-4a3b-4c5d-6e7f80916273",
    "timestamp": "2026-07-19T10:00:05Z",
}

LAST_ADMINISTRATOR_PROTECTION_EXAMPLE: Final[dict[str, Any]] = {
    "success": False,
    "message": (
        "This action would leave the system with no active administrator "
        "accounts and has been blocked."
    ),
    "data": None,
    "errors": None,
    "request_id": "8b9c0d1e-2f3a-4b4c-5d6e-7f8091627384",
    "timestamp": "2026-07-19T10:00:05Z",
}

SELF_STATUS_CHANGE_ERROR_EXAMPLE: Final[dict[str, Any]] = {
    "success": False,
    "message": "Administrators cannot deactivate their own account.",
    "data": None,
    "errors": None,
    "request_id": "9c0d1e2f-3a4b-4c5d-6e7f-809162738495",
    "timestamp": "2026-07-19T10:00:05Z",
}

ADMIN_HISTORY_NOT_FOUND_EXAMPLE: Final[dict[str, Any]] = {
    "success": False,
    "message": "The requested prediction history record was not found.",
    "data": None,
    "errors": None,
    "request_id": "0d1e2f3a-4b5c-4d6e-7f80-916273849506",
    "timestamp": "2026-07-19T10:00:05Z",
}
