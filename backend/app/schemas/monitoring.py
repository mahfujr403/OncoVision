"""Monitoring API response schemas (Phase 8.1-8.2, ADR-036).

Defines the public response contract for `GET /api/v1/monitoring`.
Every field here is copied directly from an already-built
`app.monitoring.monitoring_result.MonitoringResult` (and its nested
`app.monitoring.health` / `app.monitoring.metrics` projections) -- this
module performs no calculation of its own, mirroring the convention
already established by `app.schemas.admin.AdminSystemStatusSchema`.
"""

from pydantic import BaseModel, Field

from app.monitoring.enums import ComponentStatus

__all__ = [
    "ApplicationHealthSchema",
    "DatabaseHealthSchema",
    "ModelHealthSchema",
    "RuntimeHealthSchema",
    "RequestMetricsSchema",
    "PredictionRequestMetricsSchema",
    "MonitoringStatusSchema",
]


class ApplicationHealthSchema(BaseModel):
    """Application-level health, as exposed by `GET /api/v1/monitoring`."""

    status: ComponentStatus = Field(description="Health classification for the application itself.")
    name: str = Field(description="Application name.")
    version: str = Field(description="Application version.")
    environment: str = Field(description="Current runtime environment.")


class DatabaseHealthSchema(BaseModel):
    """Database connectivity health, as exposed by `GET /api/v1/monitoring`."""

    status: ComponentStatus = Field(description="Health classification for database connectivity.")
    connected: bool = Field(description="Whether the database was reachable at check time.")


class ModelHealthSchema(BaseModel):
    """Per-model runtime health, as exposed by `GET /api/v1/monitoring`."""

    model_id: str = Field(description="Unique identifier of the registered model.")
    display_name: str = Field(description="Human-readable model name.")
    state: str = Field(description="Current runtime lifecycle state (e.g. 'ready', 'failed').")
    is_available: bool = Field(
        description="Whether this model is currently READY and able to serve predictions."
    )
    error_message: str | None = Field(
        default=None, description="Failure reason, populated only when the model has failed."
    )


class RuntimeHealthSchema(BaseModel):
    """AI Runtime Manager health, as exposed by `GET /api/v1/monitoring`."""

    status: ComponentStatus = Field(description="Health classification for the AI runtime as a whole.")
    is_operational: bool = Field(description="Whether at least one registered model is READY.")
    total_model_count: int = Field(description="Total number of registered models.")
    loaded_model_count: int = Field(description="Number of models currently READY.")
    failed_model_count: int = Field(description="Number of models currently FAILED.")
    pending_model_count: int = Field(
        description="Number of models not yet READY, FAILED, or DISABLED."
    )
    disabled_model_count: int = Field(description="Number of models currently DISABLED.")
    models: list[ModelHealthSchema] = Field(
        default_factory=list, description="Per-model health, sorted by loading priority."
    )


class RequestMetricsSchema(BaseModel):
    """HTTP request-level metrics, as exposed by `GET /api/v1/monitoring` (Phase 8.2)."""

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


class PredictionRequestMetricsSchema(BaseModel):
    """Prediction-endpoint request metrics, as exposed by `GET /api/v1/monitoring` (Phase 8.2)."""

    total_requests: int = Field(
        description="Total number of requests received by the prediction endpoint since startup."
    )
    successful_requests: int = Field(
        description="Number of prediction requests that completed with a 2xx status code."
    )
    failed_requests: int = Field(
        description="Number of prediction requests that completed with a non-2xx status code."
    )


class MonitoringStatusSchema(BaseModel):
    """Response payload for `GET /api/v1/monitoring`.

    Aggregates only safe, already-computed operational metadata
    (`MonitoringService`) -- no secrets, credentials, environment
    variables, or other sensitive infrastructure information is ever
    included (ADR-036/ADR-047).
    """

    status: ComponentStatus = Field(
        description="Overall health classification derived from database and runtime status."
    )
    application: ApplicationHealthSchema = Field(description="Application-level health.")
    database: DatabaseHealthSchema = Field(description="Database connectivity health.")
    runtime: RuntimeHealthSchema = Field(description="AI Runtime Manager health.")
    request_metrics: RequestMetricsSchema = Field(
        description="Aggregated HTTP request metrics for this process since startup (Phase 8.2)."
    )
    prediction_metrics: PredictionRequestMetricsSchema = Field(
        description=(
            "Aggregated prediction endpoint request metrics for this process since startup (Phase 8.2)."
        )
    )
    generated_at: str = Field(description="ISO 8601 timestamp of when this snapshot was generated.")
