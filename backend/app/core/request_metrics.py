"""In-process HTTP request metrics collector (Phase 8.2, ADR-036).

Phase 8.1 introduced health-only monitoring (`app.monitoring.health`),
built entirely from *already-existing* sources (`SystemService`,
`check_database_connection`, `AIRuntimeManager`). No component in the
codebase, however, aggregates HTTP-level request counts, status codes,
durations, or prediction request outcomes over time -- `LoggingMiddleware`
and `ProcessTimeMiddleware` only log/report *per-request* values, they
never accumulate them.

`RequestMetricsCollector` is the single, minimal, in-memory source for
that previously-missing aggregate: a lightweight counter object, updated
once per request by `app.middleware.metrics.RequestMetricsMiddleware`,
and read by `app.services.monitoring_service.MonitoringService`. It is
intentionally NOT a database table, a Prometheus registry, or a
persisted store (ADR-036 Phase 8.2 scope explicitly excludes external
monitoring infrastructure) -- counters live only for the lifetime of the
running process, the same lifetime already assumed by
`AIRuntimeManager`'s in-memory runtime state.

This module performs no timing calculation of its own beyond simple
summation/averaging of values already measured by the caller (mirroring
`PredictionExecutionStats`, which is never recomputed here or anywhere
else in Monitoring) -- it never re-runs a request, never inspects
request/response bodies, and never records anything beyond method, path,
status code, and duration.
"""

import threading
from dataclasses import dataclass

from app.constants.app import API_V1_PREFIX

__all__ = ["RequestMetricsCollector", "RequestMetricsSnapshot", "default_request_metrics_collector"]

# The single endpoint Application Monitoring treats as "a prediction
# request" (ADR-010/ADR-012: `POST /api/v1/predictions`). Kept as a
# constant here rather than imported from `app.api.v1.predictions` to
# avoid a dependency from `app.core` (foundational) onto the API layer.
_PREDICTION_ENDPOINT_PATH = f"{API_V1_PREFIX}/predictions"
_PREDICTION_ENDPOINT_METHOD = "POST"


@dataclass(frozen=True)
class RequestMetricsSnapshot:
    """Immutable point-in-time copy of the collector's counters.

    Returned by `RequestMetricsCollector.snapshot()`. Never mutated after
    construction, and never itself performs a calculation beyond the one
    average expressed by `average_duration_ms`.
    """

    total_requests: int
    status_2xx: int
    status_3xx: int
    status_4xx: int
    status_5xx: int
    average_duration_ms: float
    prediction_requests_total: int
    prediction_successful_total: int
    prediction_failed_total: int


@dataclass
class _Counters:
    total_requests: int = 0
    status_2xx: int = 0
    status_3xx: int = 0
    status_4xx: int = 0
    status_5xx: int = 0
    total_duration_ms: float = 0.0
    prediction_requests_total: int = 0
    prediction_successful_total: int = 0
    prediction_failed_total: int = 0


class RequestMetricsCollector:
    """Thread-safe, in-memory accumulator of HTTP request/prediction outcomes.

    A single shared instance (`default_request_metrics_collector`) is
    updated by `RequestMetricsMiddleware` on every request and read by
    `MonitoringService`. All public methods are defensive: `record_request`
    never raises, so a metrics-recording problem can never surface as a
    request failure (Phase 8.2 Reliability requirement) -- the same
    "monitoring failure must never break core APIs" guarantee already
    established for `MonitoringService._build_database_health()`.
    """

    def __init__(self) -> None:
        self._counters = _Counters()
        self._lock = threading.Lock()

    def record_request(self, *, method: str, path: str, status_code: int, duration_ms: float) -> None:
        """Record the outcome of one completed HTTP request.

        Never raises. Any unexpected value (e.g. a status code outside
        100-599) is simply ignored rather than propagated, since a
        malformed metrics observation must never be allowed to affect
        the response already produced by the application.
        """
        try:
            with self._lock:
                counters = self._counters
                counters.total_requests += 1
                counters.total_duration_ms += max(duration_ms, 0.0)

                if 200 <= status_code < 300:
                    counters.status_2xx += 1
                elif 300 <= status_code < 400:
                    counters.status_3xx += 1
                elif 400 <= status_code < 500:
                    counters.status_4xx += 1
                elif 500 <= status_code < 600:
                    counters.status_5xx += 1

                if method.upper() == _PREDICTION_ENDPOINT_METHOD and path == _PREDICTION_ENDPOINT_PATH:
                    counters.prediction_requests_total += 1
                    if 200 <= status_code < 300:
                        counters.prediction_successful_total += 1
                    else:
                        counters.prediction_failed_total += 1
        except Exception:  # noqa: BLE001 - metrics recording must never raise.
            return

    def snapshot(self) -> RequestMetricsSnapshot:
        """Return an immutable copy of the current counters.

        `average_duration_ms` is `0.0` when no requests have been
        recorded yet -- never a division-by-zero.
        """
        with self._lock:
            counters = self._counters
            average_duration_ms = (
                round(counters.total_duration_ms / counters.total_requests, 2)
                if counters.total_requests > 0
                else 0.0
            )
            return RequestMetricsSnapshot(
                total_requests=counters.total_requests,
                status_2xx=counters.status_2xx,
                status_3xx=counters.status_3xx,
                status_4xx=counters.status_4xx,
                status_5xx=counters.status_5xx,
                average_duration_ms=average_duration_ms,
                prediction_requests_total=counters.prediction_requests_total,
                prediction_successful_total=counters.prediction_successful_total,
                prediction_failed_total=counters.prediction_failed_total,
            )

    def reset(self) -> None:
        """Reset all counters to zero. Intended for test isolation only."""
        with self._lock:
            self._counters = _Counters()


# Process-wide singleton shared between `RequestMetricsMiddleware` (writer)
# and `MonitoringService` (reader), mirroring the existing singleton
# `AIRuntimeManager` pattern (`app.dependencies.services.get_ai_runtime_manager`).
default_request_metrics_collector = RequestMetricsCollector()
