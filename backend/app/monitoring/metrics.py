"""Monitoring domain metrics models (Phase 8.2, ADR-036).

Extends the Phase 8.1 health-only `app.monitoring` package with the
"Application Monitoring" data Phase 8.2 requires: HTTP request counts/
status codes/duration, and prediction request success/failure counts.

Both models here are immutable, monitoring-owned projections built
exclusively from an already-computed source -- `RequestMetricsSnapshot`
(`app.core.request_metrics.RequestMetricsCollector.snapshot()`) -- the
same "no field here is freshly calculated" convention already documented
on `app.monitoring.health`. No component in this module performs a
calculation beyond the trivial copy `MonitoringService` already does for
every other Monitoring field.
"""

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["RequestMetrics", "PredictionRequestMetrics"]


class RequestMetrics(BaseModel):
    """Immutable HTTP request-level metrics projection.

    Constructed by `MonitoringService` directly from a
    `RequestMetricsSnapshot`. Covers every request handled by this
    process since it started -- across every endpoint, not only
    Monitoring's own.
    """

    model_config = ConfigDict(frozen=True)

    total_requests: int = Field(
        description="Total number of HTTP requests handled by this process since startup."
    )
    status_2xx: int = Field(description="Number of requests that completed with a 2xx status code.")
    status_3xx: int = Field(description="Number of requests that completed with a 3xx status code.")
    status_4xx: int = Field(description="Number of requests that completed with a 4xx status code.")
    status_5xx: int = Field(description="Number of requests that completed with a 5xx status code.")
    average_duration_ms: float = Field(
        description="Mean request duration in milliseconds, averaged across every recorded request."
    )


class PredictionRequestMetrics(BaseModel):
    """Immutable prediction-endpoint request metrics projection.

    Constructed by `MonitoringService` directly from a
    `RequestMetricsSnapshot`. Scoped to `POST /api/v1/predictions` only,
    classified purely by the HTTP status code that endpoint already
    returned -- no prediction, ensemble, or model-level recalculation of
    any kind occurs here.
    """

    model_config = ConfigDict(frozen=True)

    total_requests: int = Field(
        description="Total number of requests received by the prediction endpoint since startup."
    )
    successful_requests: int = Field(
        description="Number of prediction requests that completed with a 2xx status code."
    )
    failed_requests: int = Field(
        description="Number of prediction requests that completed with a non-2xx status code."
    )
