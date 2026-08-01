"""Centralized exception types and FastAPI exception handlers.

All exception handlers return the application's standard JSON response
envelope and never leak internal stack traces to the client.
"""

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger
from app.utils.response import error_response

logger = get_logger(__name__)


class OncoVisionError(Exception):
    """Base exception for all application-specific errors.

    Attributes:
        message: Human-readable error message.
        status_code: HTTP status code to return.
        errors: Optional structured error details.
    """

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        errors: Any | None = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.errors = errors
        super().__init__(message)


class DuplicateEmailError(OncoVisionError):
    """Raised when attempting to register an email that already exists."""

    def __init__(self, message: str = "An account with this email already exists.") -> None:
        super().__init__(message=message, status_code=status.HTTP_409_CONFLICT)


class InvalidCredentialsError(OncoVisionError):
    """Raised when login credentials do not match a known account."""

    def __init__(self, message: str = "Invalid email or password.") -> None:
        super().__init__(message=message, status_code=status.HTTP_401_UNAUTHORIZED)


class InactiveUserError(OncoVisionError):
    """Raised when an authenticated action is attempted by a deactivated user."""

    def __init__(self, message: str = "This account has been deactivated.") -> None:
        super().__init__(message=message, status_code=status.HTTP_403_FORBIDDEN)


class InvalidTokenError(OncoVisionError):
    """Raised when a JWT is malformed, has an unexpected type, or is unknown."""

    def __init__(self, message: str = "The provided token is invalid.") -> None:
        super().__init__(message=message, status_code=status.HTTP_401_UNAUTHORIZED)


class TokenExpiredError(OncoVisionError):
    """Raised when a JWT has expired."""

    def __init__(self, message: str = "The provided token has expired.") -> None:
        super().__init__(message=message, status_code=status.HTTP_401_UNAUTHORIZED)


class UnauthorizedError(OncoVisionError):
    """Raised when a request is missing required authentication credentials."""

    def __init__(
        self, message: str = "Authentication is required to access this resource."
    ) -> None:
        super().__init__(message=message, status_code=status.HTTP_401_UNAUTHORIZED)


class ForbiddenError(OncoVisionError):
    """Raised when an authenticated user lacks permission to access a resource."""

    def __init__(
        self, message: str = "You do not have permission to perform this action."
    ) -> None:
        super().__init__(message=message, status_code=status.HTTP_403_FORBIDDEN)


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle `HTTPException` instances raised anywhere in the application.

    Registered against Starlette's base `HTTPException` (rather than
    FastAPI's subclass) so that routing-level errors such as 404s, which
    are raised as the base type, are also caught.
    """
    request_id = getattr(request.state, "request_id", None)
    logger.warning(
        "HTTPException on %s %s: %s", request.method, request.url.path, exc.detail
    )
    return error_response(
        message=str(exc.detail),
        status_code=exc.status_code,
        request_id=request_id,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError | ValidationError
):
    request_id = getattr(request.state, "request_id", None)

    errors = [
        {
            "field": ".".join(map(str, err["loc"])),
            "message": err["msg"],
        }
        for err in exc.errors()
    ]

    return error_response(
        message="Request validation failed.",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        errors=errors,
        request_id=request_id,
    )

async def oncovision_exception_handler(request: Request, exc: OncoVisionError):
    """Handle application-specific `OncoVisionError` exceptions."""
    request_id = getattr(request.state, "request_id", None)
    logger.warning(
        "Application error on %s %s: %s", request.method, request.url.path, exc.message
    )
    return error_response(
        message=exc.message,
        status_code=exc.status_code,
        errors=exc.errors,
        request_id=request_id,
    )


async def unhandled_exception_handler(request: Request, exc: Exception):
    """Handle any exception not caught by a more specific handler.

    Logs the full exception internally but never exposes internal details
    (such as stack traces) in the response payload.
    """
    request_id = getattr(request.state, "request_id", None)
    logger.error(
        "Unhandled exception on %s %s", request.method, request.url.path, exc_info=exc
    )
    return error_response(
        message="An unexpected internal server error occurred.",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        request_id=request_id,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach all centralized exception handlers to the FastAPI app."""
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)
    app.add_exception_handler(OncoVisionError, oncovision_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
