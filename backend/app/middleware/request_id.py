"""Middleware that assigns a unique request ID to every incoming request."""

import re
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
        incoming_id = request.headers.get(REQUEST_ID_HEADER) or request.headers.get("X-Correlation-ID")
        if incoming_id and re.match(r"^[a-zA-Z0-9_\-]{1,64}$", incoming_id.strip()):
            request_id = incoming_id.strip()
        else:
            request_id = generate_request_id()

        request.state.request_id = request_id

        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response

