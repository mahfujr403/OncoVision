"""Prediction History CSV Export package (Phase 6.3, ADR-039).

`app.reports.csv` establishes the reusable CSV export layer that turns
already-computed Prediction History and Prediction Analytics into a
downloadable CSV document. It is the first concrete export format built
on top of the Reporting Foundation (Phase 6.1) and Prediction Analytics
Engine (Phase 6.2), and is designed so PDF Export (Phase 6.4) and the
future Reporting APIs (Phase 6.5) can add their own export layer without
this one changing shape.

Per ADR-039, CSV Export:

- Consumes `app.history.prediction_history.PredictionHistory` records
  (via the existing `PredictionHistoryRepository`) and
  `app.reports.analytics.analytics_result.PredictionAnalyticsResult`
  (via the existing `PredictionAnalyticsService`) only. No new
  repository, database table, or persistence mechanism is introduced.
- Never executes AI inference, loads AI models, or communicates with
  `AIRuntimeManager`, the Prediction Engine, or the Adaptive Ensemble
  Engine.
- Never modifies Prediction History or Prediction Analytics. CSV
  generation is strictly read-only.
- Generates a CSV document dynamically, on demand, in memory. Nothing
  produced by this package is persisted to disk, and no HTTP endpoint is
  exposed in this phase (reserved for Phase 6.5).

Mirrors the layering already established by `app.reports` (Phase 6.1)
and `app.reports.analytics` (Phase 6.2):

    `app.reports.csv.csv_result`         -- `CSVExportResult` domain model
    `app.reports.csv.csv_builder`        -- `CSVExportBuilder` (pure serialization)
    `app.reports.csv.csv_validator`      -- `CSVValidator` (request validation)
    `app.reports.csv.csv_export_service` -- `CSVExportService` (orchestration)
    `app.reports.csv.exceptions`         -- `CSVExportError` hierarchy

`CSVExportService` is the single orchestration point for CSV Export,
mirroring the role `ReportService` already plays for Reporting and
`PredictionAnalyticsService` plays for Analytics. It depends on the
existing `PredictionHistoryRepository` and `PredictionAnalyticsService`
-- never on `AIRuntimeManager`, `PredictionEngine`, or the database
directly.
"""
