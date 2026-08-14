"""Middleware that feeds every completed request into the request metrics collector.

Phase 8.2 (ADR-036). Companion to `LoggingMiddleware` (which logs each
request) and `ProcessTimeMiddleware` (which reports each request's
duration via a response header): this middleware is the only one that
*accumulates* those same values, via `RequestMetricsCollector`, so
`MonitoringService` can expose them in aggregate.

Recording never affects the response: any failure while updating the
collector is caught and logged, never re-raised, so a monitoring problem
can never turn into a `500` for an otherwise-successful request (Phase
8.2 Reliability requirement).
"""

import time
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger
from app.core.request_metrics import RequestMetricsCollector, default_request_metrics_collector

logger = get_logger(__name__)


class RequestMetricsMiddleware(BaseHTTPMiddleware):
    """Record method, path, status code, and duration for every request."""

    def __init__(self, app, collector: RequestMetricsCollector | None = None) -> None:
        super().__init__(app)
        self._collector = collector or default_request_metrics_collector

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        start_time = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start_time) * 1000

        try:
            self._collector.record_request(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms,
            )
        except Exception:
            logger.error("Request metrics recording failed.", exc_info=True)

        return response
