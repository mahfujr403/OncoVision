"""Prediction Report PDF Export package (Phase 6.4, ADR-040).

`app.reports.pdf` establishes the reusable PDF export layer that turns
already-computed Prediction History and Prediction Analytics into a
professionally formatted, downloadable PDF report. It mirrors the
structure of the CSV Export package (`app.reports.csv`, Phase 6.3,
ADR-039) exactly, so the two export formats stay interchangeable from a
future Reporting API's (Phase 6.5) point of view.

Per ADR-040, PDF Export:

- Consumes `app.history.prediction_history.PredictionHistory` records
  (via the existing `PredictionHistoryRepository`) and
  `app.reports.analytics.analytics_result.PredictionAnalyticsResult`
  (via the existing `PredictionAnalyticsService`) only. No new
  repository, database table, or persistence mechanism is introduced.
- Never executes AI inference, loads AI models, or communicates with
  `AIRuntimeManager`, the Prediction Engine, or the Adaptive Ensemble
  Engine.
- Never modifies Prediction History or Prediction Analytics. PDF
  generation is strictly read-only.
- Generates a PDF document dynamically, on demand, in memory. Nothing
  produced by this package is persisted to disk, and no HTTP endpoint,
  email delivery, or scheduling is introduced in this phase (reserved
  for later phases).

Mirrors the layering already established by `app.reports.csv`
(Phase 6.3):

    `app.reports.pdf.pdf_result`         -- `PDFExportResult` domain model
    `app.reports.pdf.enums`              -- `PDFPageSize`
    `app.reports.pdf.pdf_builder`        -- `PDFBuilder` (pure rendering)
    `app.reports.pdf.pdf_validator`      -- `PDFValidator` (request validation)
    `app.reports.pdf.pdf_export_service` -- `PDFExportService` (orchestration)
    `app.reports.pdf.exceptions`         -- `PDFExportError` hierarchy

`PDFExportService` is the single orchestration point for PDF Export,
mirroring the role `CSVExportService` already plays for CSV Export. It
depends on the existing `PredictionHistoryRepository` and
`PredictionAnalyticsService` -- never on `AIRuntimeManager`,
`PredictionEngine`, or the database directly.
"""
