"""Reporting Foundation package (Phase 6.1, ADR-037).

`app.reports` establishes the reporting architecture that all future
reporting capabilities -- PDF Export (Phase 6.4), CSV Export (Phase 6.3),
Analytics (Phase 6.2), and dashboards -- will build on top of.

Per ADR-037, Reporting:

- Consumes `app.history.prediction_history.PredictionHistory` records
  only, retrieved through the existing `PredictionHistoryRepository`
  (`app.repositories.prediction_history_repository`). No new repository,
  database table, or persistence mechanism is introduced.
- Never executes AI inference, loads AI models, or communicates with
  `AIRuntimeManager`, the Prediction Engine, or the Adaptive Ensemble
  Engine.
- Never modifies Prediction History. Reporting is strictly read-only.
- Generates report objects dynamically, on demand. Nothing produced by
  this package is persisted, and no report file (PDF, CSV, or otherwise)
  is generated in this phase.

Mirrors the layering already established by `app.history`:

    `app.reports.enums`       -- independently-owned enumerations
    `app.reports.summary`     -- `ReportSummary` domain model
    `app.reports.statistics`  -- `ReportStatistics` domain model
    `app.reports.report`      -- `Report` domain model (the aggregate root)
    `app.reports.builder`     -- `ReportBuilder` (pure aggregation)
    `app.reports.validator`   -- `ReportValidator` (request validation)
    `app.reports.exceptions`  -- `ReportError` hierarchy

`app.services.report_service.ReportService` is the orchestration layer
that ties these together with `PredictionHistoryRepository`, mirroring
the role `PredictionHistoryService` already plays for Prediction History
itself.
"""
