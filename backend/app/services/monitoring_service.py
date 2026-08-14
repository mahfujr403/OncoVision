"""Monitoring Service (Phase 8.1-8.2, ADR-036).

`MonitoringService` is the single orchestration point for Monitoring &
Observability, mirroring the role `AdminSystemService` already plays for
Administration (Phase 7.5) and `PredictionAnalyticsService` plays for
Analytics (ADR-038). It introduces no second runtime manager, database
connection mechanism, or health check of its own: every value in the
`MonitoringResult` it produces is sourced from components that already
exist and are already exposed, in a similar shape, by the self-service
`/system/*` endpoints (`app.api.v1.system`) and the administrative
`GET /api/v1/admin/system` endpoint (`app.services.admin_system_service`):

- `SystemService.get_application_info()` for application metadata
  (Phase 1).
- `app.database.database.check_database_connection()` for database
  connectivity.
- `AIRuntimeManager.health_service.runtime_status()` for runtime health.
- `AIRuntimeManager.get_all_model_status()` for per-model status.

Unlike `AdminSystemService` (which re-packages these sources as plain
dictionaries for the Administration domain), `MonitoringService` maps
them onto the strongly-typed `app.monitoring` domain contracts and
derives one overall `ComponentStatus` -- the shape future Monitoring
sub-phases (Prometheus/OpenTelemetry export, alerting) can consume
without re-deriving that classification themselves.

Per ADR-036/ADR-047, nothing this service returns may include secrets,
credentials, environment variables, or other sensitive infrastructure
information, and it never performs inference, loads TensorFlow models,
recalculates predictions, or modifies Prediction History/Reports.

Phase 8.2 (ADR-036, Monitoring & Observability Hardening) adds one more
already-safe source: `app.core.request_metrics.RequestMetricsCollector`
(populated by `app.middleware.metrics.RequestMetricsMiddleware`), read
via `.snapshot()` and mapped onto `RequestMetrics`/`PredictionRequestMetrics`.
No timing or count is recalculated here -- the collector already
aggregates them; this service only copies the resulting snapshot onto
the public domain contracts, the same convention every other field on
`MonitoringResult` already follows.
"""

from app.core.logging import get_logger
from app.core.request_metrics import RequestMetricsCollector, default_request_metrics_collector
from app.database.database import check_database_connection
from app.ml.runtime.runtime_manager import AIRuntimeManager
from app.monitoring.enums import ComponentStatus
from app.monitoring.health import ApplicationHealth, DatabaseHealth, ModelHealth, RuntimeHealth
from app.monitoring.metrics import PredictionRequestMetrics, RequestMetrics
from app.monitoring.monitoring_result import MonitoringResult
from app.services.system_service import SystemService
from app.utils.environment import get_current_timestamp

logger = get_logger(__name__)


class MonitoringService:
    """Aggregates existing, already-safe operational metadata into a `MonitoringResult`."""

    def __init__(
        self,
        runtime_manager: AIRuntimeManager,
        system_service: SystemService,
        request_metrics_collector: RequestMetricsCollector | None = None,
    ) -> None:
        self._runtime_manager = runtime_manager
        self._system_service = system_service
        # Defaults to the process-wide singleton written to by
        # `RequestMetricsMiddleware` -- optional only so Phase 8.1 callers/
        # tests that construct `MonitoringService` without it keep working
        # unchanged (ADR-036: backward-compatible extension, not a rewrite).
        self._request_metrics_collector = request_metrics_collector or default_request_metrics_collector

    async def get_monitoring_status(self) -> MonitoringResult:
        """Return a combined application/database/runtime/metrics monitoring snapshot.

        Never raises: a failure in any single underlying source is
        reflected as an `UNHEALTHY`/`DEGRADED` `ComponentStatus` (or, for
        Phase 8.2 request metrics, an all-zero snapshot) on the returned
        `MonitoringResult` rather than propagated as an exception, so the
        monitoring endpoint itself always remains a reliable read (the
        same convention already established by
        `AdminSystemService._check_database_status()`).
        """
        application_health = self._build_application_health()
        database_health = await self._build_database_health()
        runtime_health = await self._build_runtime_health()
        overall_status = self._derive_overall_status(database_health, runtime_health)
        request_metrics, prediction_metrics = self._build_request_metrics()

        logger.info(
            "Monitoring status generated: overall=%s database_connected=%s runtime_operational=%s "
            "total_requests=%d prediction_requests_total=%d",
            overall_status.value,
            database_health.connected,
            runtime_health.is_operational,
            request_metrics.total_requests,
            prediction_metrics.total_requests,
        )

        return MonitoringResult(
            status=overall_status,
            application=application_health,
            database=database_health,
            runtime=runtime_health,
            request_metrics=request_metrics,
            prediction_metrics=prediction_metrics,
            generated_at=get_current_timestamp(),
        )

    def _build_application_health(self) -> ApplicationHealth:
        """Build `ApplicationHealth` from `SystemService.get_application_info()`.

        Always `HEALTHY`: reaching this code path already means the
        application process is running and able to answer, the same
        assumption `GET /api/v1/health` and `AdminSystemService` make.
        """
        application_info = self._system_service.get_application_info()
        return ApplicationHealth(
            status=ComponentStatus.HEALTHY,
            name=application_info.name,
            version=application_info.version,
            environment=application_info.environment,
        )

    @staticmethod
    async def _build_database_health() -> DatabaseHealth:
        """Build `DatabaseHealth` from `check_database_connection()`, never leaking the underlying error."""
        try:
            await check_database_connection()
            return DatabaseHealth(status=ComponentStatus.HEALTHY, connected=True)
        except Exception:
            logger.error("Monitoring status: database connectivity check failed.", exc_info=True)
            return DatabaseHealth(status=ComponentStatus.UNHEALTHY, connected=False)

    async def _build_runtime_health(self) -> RuntimeHealth:
        """Build `RuntimeHealth` from `AIRuntimeManager.health_service.runtime_status()` / `get_all_model_status()`."""
        runtime_status = await self._runtime_manager.health_service.runtime_status()
        model_statuses = await self._runtime_manager.get_all_model_status()

        models = [
            ModelHealth(
                model_id=model["model_id"],
                display_name=model["display_name"],
                state=model["state"],
                is_available=model["state"] == "ready",
                error_message=model.get("error_message"),
            )
            for model in model_statuses
        ]

        is_operational = bool(runtime_status.get("is_operational", False))
        failed_model_count = int(runtime_status.get("failed_model_count", 0))

        if not is_operational:
            runtime_status_value = ComponentStatus.UNHEALTHY
        elif failed_model_count > 0:
            runtime_status_value = ComponentStatus.DEGRADED
        else:
            runtime_status_value = ComponentStatus.HEALTHY

        return RuntimeHealth(
            status=runtime_status_value,
            is_operational=is_operational,
            total_model_count=int(runtime_status.get("total_model_count", 0)),
            loaded_model_count=int(runtime_status.get("loaded_model_count", 0)),
            failed_model_count=failed_model_count,
            pending_model_count=int(runtime_status.get("pending_model_count", 0)),
            disabled_model_count=int(runtime_status.get("disabled_model_count", 0)),
            models=models,
        )

    @staticmethod
    def _derive_overall_status(
        database_health: DatabaseHealth, runtime_health: RuntimeHealth
    ) -> ComponentStatus:
        """Derive one overall `ComponentStatus` from the database and runtime projections.

        `UNHEALTHY` if the database is unreachable or the runtime has no
        model loaded (the service cannot serve predictions either way),
        `DEGRADED` if the runtime is operational but reports a
        `DEGRADED`/`UNHEALTHY` sub-status of its own (e.g. one or more
        failed models), `HEALTHY` otherwise. Application health is not
        considered here: it is always `HEALTHY` by construction.
        """
        if not database_health.connected:
            return ComponentStatus.UNHEALTHY
        if runtime_health.status == ComponentStatus.UNHEALTHY:
            return ComponentStatus.UNHEALTHY
        if runtime_health.status == ComponentStatus.DEGRADED:
            return ComponentStatus.DEGRADED
        return ComponentStatus.HEALTHY

    def _build_request_metrics(self) -> tuple[RequestMetrics, PredictionRequestMetrics]:
        """Build `RequestMetrics`/`PredictionRequestMetrics` from the request metrics collector.

        Never raises: a failure while reading the collector is logged and
        reflected as an all-zero snapshot for both projections, the same
        "never break the read" convention `_build_database_health()`
        already follows for database connectivity.
        """
        try:
            snapshot = self._request_metrics_collector.snapshot()
        except Exception:
            logger.error("Monitoring status: request metrics snapshot failed.", exc_info=True)
            return (
                RequestMetrics(
                    total_requests=0,
                    status_2xx=0,
                    status_3xx=0,
                    status_4xx=0,
                    status_5xx=0,
                    average_duration_ms=0.0,
                ),
                PredictionRequestMetrics(total_requests=0, successful_requests=0, failed_requests=0),
            )

        request_metrics = RequestMetrics(
            total_requests=snapshot.total_requests,
            status_2xx=snapshot.status_2xx,
            status_3xx=snapshot.status_3xx,
            status_4xx=snapshot.status_4xx,
            status_5xx=snapshot.status_5xx,
            average_duration_ms=snapshot.average_duration_ms,
        )
        prediction_metrics = PredictionRequestMetrics(
            total_requests=snapshot.prediction_requests_total,
            successful_requests=snapshot.prediction_successful_total,
            failed_requests=snapshot.prediction_failed_total,
        )
        return request_metrics, prediction_metrics
