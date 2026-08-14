"""Monitoring & Observability enumerations (Phase 8.1, ADR-036).

`ComponentStatus` is Monitoring's own, independently owned status
projection. It intentionally mirrors the shape of
`app.history.enums.PredictionHistoryStatus` without importing that
(unrelated) module -- each domain package under `app/` owns its status
vocabulary rather than sharing one across domains, the same reasoning
already documented on `app.history.enums.PredictionHistoryStatus`.
"""

from enum import Enum


class ComponentStatus(str, Enum):
    """Health classification for a single monitored component, or the overall snapshot.

    Derived entirely by `app.services.monitoring_service.MonitoringService`
    from already-computed operational metadata -- never itself the
    result of a new health check or calculation.
    """

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
