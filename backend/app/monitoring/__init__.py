"""Monitoring & Observability domain package (Phase 8.1, ADR-036).

`app.monitoring` holds the framework-agnostic monitoring domain
contracts, mirroring the layering already established by `app.history`
and `app.reports`:

    `app.monitoring.enums`             -- `ComponentStatus`
    `app.monitoring.health`            -- `ApplicationHealth`,
                                           `DatabaseHealth`, `ModelHealth`,
                                           `RuntimeHealth`
    `app.monitoring.monitoring_result` -- `MonitoringResult` (the
                                           aggregate root)

Per ADR-036, Monitoring:

- Reuses existing operational metadata sources only --
  `app.services.system_service.SystemService`,
  `app.database.database.check_database_connection`, and the singleton
  `app.ml.runtime.runtime_manager.AIRuntimeManager`
  (`health_service.runtime_status()` / `get_all_model_status()`).
  No second runtime manager, database connection mechanism, or health
  check is introduced.
- Never performs inference, loads TensorFlow models, recalculates
  predictions, or modifies Prediction History/Reports.
- Is strictly read-only: `app.services.monitoring_service.MonitoringService`
  is the orchestration layer that ties these domain contracts together,
  mirroring the role `AdminSystemService` already plays for the
  Administration domain -- the two intentionally consume the same
  underlying sources but expose them through independently owned,
  strongly-typed contracts rather than sharing one.

Phase 8.1 (this phase) introduces the Monitoring Foundation: the domain
contracts above, `MonitoringService`, and the `GET /api/v1/monitoring`
endpoint. Later Phase 8 sub-phases (8.2 Prediction & Model Metrics, 8.3
System Health & Operational Metrics, 8.4/8.5) extend this same package
without redesigning it.
"""
