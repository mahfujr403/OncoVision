"""Middleware that assigns a unique request ID to every incoming request."""

from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.constants.app import REQUEST_ID_HEADER
from app.utils.environment import generate_request_id


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a unique `request_id` to each request's state and response."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = generate_request_id()
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response
