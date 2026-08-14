"""Monitoring Result aggregate (Phase 8.1-8.2, ADR-036).

`MonitoringResult` is the immutable aggregate root produced exactly once
per `MonitoringService.get_monitoring_status()` call. It carries no
calculation of its own beyond combining the already-built
`ApplicationHealth`, `DatabaseHealth`, and `RuntimeHealth` projections
(deriving one overall `ComponentStatus` from them) and the Phase 8.2
`RequestMetrics`/`PredictionRequestMetrics` projections, mirroring the
role `app.reports.report.Report` plays as the aggregate root for
Reporting.
"""

from pydantic import BaseModel, ConfigDict, Field

from app.monitoring.enums import ComponentStatus
from app.monitoring.health import ApplicationHealth, DatabaseHealth, RuntimeHealth
from app.monitoring.metrics import PredictionRequestMetrics, RequestMetrics


class MonitoringResult(BaseModel):
    """Immutable, aggregated operational monitoring snapshot.

    Constructed exactly once per computation by `MonitoringService`.
    Never constructed, mutated, or recalculated by any other component.
    """

    model_config = ConfigDict(frozen=True)

    status: ComponentStatus = Field(
        description=(
            "Overall health classification, derived from `database` and "
            "`runtime`: `UNHEALTHY` if the database is unreachable or no "
            "model is loaded, `DEGRADED` if the runtime is operational but "
            "at least one registered model has failed, `HEALTHY` otherwise."
        )
    )
    application: ApplicationHealth = Field(description="Application-level health projection.")
    database: DatabaseHealth = Field(description="Database connectivity health projection.")
    runtime: RuntimeHealth = Field(description="AI Runtime Manager health projection.")
    request_metrics: RequestMetrics = Field(
        description="Aggregated HTTP request metrics for this process since startup (Phase 8.2)."
    )
    prediction_metrics: PredictionRequestMetrics = Field(
        description="Aggregated prediction endpoint request metrics for this process since startup (Phase 8.2)."
    )
    generated_at: str = Field(description="ISO 8601 timestamp of when this snapshot was generated.")
