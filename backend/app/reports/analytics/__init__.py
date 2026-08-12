"""Prediction Analytics package (Phase 6.2, ADR-038).

`app.reports.analytics` establishes the reusable analytics layer that
computes aggregated prediction statistics from Prediction History. It
becomes the single source of truth for every statistical calculation
consumed by dashboards, CSV Export (Phase 6.3), PDF Export (Phase 6.4),
and Reporting APIs (Phase 6.5), so none of those consumers ever
recalculate the same metrics independently.

Per ADR-038, Analytics:

- Consumes `app.history.prediction_history.PredictionHistory` records
  only, retrieved through the existing `PredictionHistoryRepository`
  (`app.repositories.prediction_history_repository`). No new
  repository, database table, or persistence mechanism is introduced.
- Never executes AI inference, loads AI models, or communicates with
  `AIRuntimeManager`, the Prediction Engine, or the Adaptive Ensemble
  Engine.
- Never modifies Prediction History. Analytics is strictly read-only.
- Generates analytics dynamically and on demand. Nothing produced by
  this package is persisted.
- Exposes no HTTP endpoints in this phase (reserved for Phase 6.5).

Mirrors the layering already established by `app.reports` (Phase 6.1):

    `app.reports.analytics.analytics_result`    -- `PredictionAnalyticsResult` domain model
    `app.reports.analytics.analytics_builder`   -- `AnalyticsBuilder` (pure aggregation)
    `app.reports.analytics.analytics_validator` -- `AnalyticsValidator` (request validation)
    `app.reports.analytics.exceptions`          -- `AnalyticsError` hierarchy

`app.services.prediction_analytics_service.PredictionAnalyticsService`
is the orchestration layer that ties these together with
`PredictionHistoryRepository`, mirroring the role `ReportService`
already plays for Reporting.
"""
