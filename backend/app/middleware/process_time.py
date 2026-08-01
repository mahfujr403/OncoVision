"""Middleware that measures and reports request processing time."""

import time
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.constants.app import PROCESS_TIME_HEADER


class ProcessTimeMiddleware(BaseHTTPMiddleware):
    """Measure request handling duration and expose it via a response header."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        start_time = time.perf_counter()
        response = await call_next(request)
        duration_seconds = time.perf_counter() - start_time

        response.headers[PROCESS_TIME_HEADER] = f"{duration_seconds:.4f}"
        return response
