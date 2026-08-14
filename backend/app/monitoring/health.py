"""Monitoring domain health models (Phase 8.1, ADR-036).

Every model in this module is an immutable, monitoring-owned projection
built exclusively from an already-computed source -- no field here is
freshly calculated:

- `ApplicationHealth` is copied from
  `app.services.system_service.SystemService.get_application_info()`
  (Phase 1).
- `DatabaseHealth` is derived from the outcome of
  `app.database.database.check_database_connection()` (already used by
  `app.lifecycle.startup.run_startup` and
  `app.services.admin_system_service.AdminSystemService`).
- `ModelHealth` is a simplified, monitoring-owned per-model projection
  of `app.ml.runtime.runtime_state.ModelRuntimeInfo`, mirroring how
  `app.history.summary.PredictionHistoryModelEntry` is a simplified,
  history-owned projection of
  `app.ml.prediction.prediction_result.IndividualPrediction` -- it
  intentionally omits internal-only fields (memory estimates, load
  duration, attempt counts) that already have a home on the existing
  `GET /api/v1/system/models/status` / `GET /api/v1/admin/system`
  responses.
- `RuntimeHealth` is derived from
  `AIRuntimeManager.health_service.runtime_status()` (already used by
  `GET /api/v1/system/runtime`) plus `AIRuntimeManager.get_all_model_status()`
  (already used by `GET /api/v1/system/models/status`).

No component in this module performs a health check, database query, or
TensorFlow call of its own.
"""

from pydantic import BaseModel, ConfigDict, Field

from app.monitoring.enums import ComponentStatus


class ApplicationHealth(BaseModel):
    """Immutable application-level health projection.

    Constructed by `MonitoringService` directly from
    `SystemService.get_application_info()`. The application is always
    considered `HEALTHY` here: reaching this code path already means the
    FastAPI process is running and able to answer, the same assumption
    `AdminSystemService` and `GET /api/v1/health` already make.
    """

    model_config = ConfigDict(frozen=True)

    status: ComponentStatus = Field(description="Health classification for the application itself.")
    name: str = Field(description="Application name, copied from `ApplicationInfo.name`.")
    version: str = Field(description="Application version, copied from `ApplicationInfo.version`.")
    environment: str = Field(
        description="Current runtime environment, copied from `ApplicationInfo.environment`."
    )


class DatabaseHealth(BaseModel):
    """Immutable database connectivity health projection.

    Constructed by `MonitoringService` from the outcome of
    `check_database_connection()` -- `connected=True` and `HEALTHY` if
    the call completed without raising, `connected=False` and
    `UNHEALTHY` otherwise. Never includes the underlying exception
    message (ADR-046/ADR-047: no internal stack traces or driver errors
    may reach a client).
    """

    model_config = ConfigDict(frozen=True)

    status: ComponentStatus = Field(description="Health classification for database connectivity.")
    connected: bool = Field(description="Whether the database was reachable at check time.")


class ModelHealth(BaseModel):
    """Immutable, simplified per-model runtime projection.

    A monitoring-owned simplification of
    `app.ml.runtime.runtime_state.ModelRuntimeInfo` -- carries only what
    operational monitoring needs to answer "is this model available",
    never the full runtime lifecycle record.
    """

    model_config = ConfigDict(frozen=True)

    model_id: str = Field(description="Unique identifier of the registered model.")
    display_name: str = Field(description="Human-readable model name.")
    state: str = Field(
        description=(
            "Current runtime lifecycle state (e.g. 'ready', 'failed', "
            "'loading'), copied from `ModelRuntimeInfo.state`."
        )
    )
    is_available: bool = Field(
        description="Whether this model is currently READY and able to serve predictions."
    )
    error_message: str | None = Field(
        default=None,
        description="Failure reason, copied from `ModelRuntimeInfo.error_message` when the model has failed.",
    )


class RuntimeHealth(BaseModel):
    """Immutable AI Runtime Manager health projection.

    Constructed by `MonitoringService` from
    `AIRuntimeManager.health_service.runtime_status()` and
    `AIRuntimeManager.get_all_model_status()` -- introduces no new
    runtime introspection and never accesses TensorFlow model instances
    directly (ADR-007/ADR-036).
    """

    model_config = ConfigDict(frozen=True)

    status: ComponentStatus = Field(description="Health classification for the AI runtime as a whole.")
    is_operational: bool = Field(
        description="Whether at least one model is READY, copied from `runtime_status()['is_operational']`."
    )
    total_model_count: int = Field(description="Total number of registered models.")
    loaded_model_count: int = Field(description="Number of models currently READY.")
    failed_model_count: int = Field(description="Number of models currently FAILED.")
    pending_model_count: int = Field(
        description="Number of models not yet READY, FAILED, or DISABLED."
    )
    disabled_model_count: int = Field(description="Number of models currently DISABLED.")
    models: list[ModelHealth] = Field(
        default_factory=list, description="Per-model health projection, sorted by loading priority."
    )
