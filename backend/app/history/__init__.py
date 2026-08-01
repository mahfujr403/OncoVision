"""Prediction History package (Phase 5.1 - Prediction History Foundation, ADR-032).

Introduces the architecture described by ADR-032: an immutable
`PredictionHistory` domain model, its supporting value objects
(`PredictionHistoryStatus`, `PredictionHistoryMetadata`,
`PredictionHistorySummary`), the `PredictionHistoryMapper` that builds a
`PredictionHistory` from an already-completed prediction pipeline run,
and the `PredictionHistoryError` exception hierarchy.

Per ADR-032, Prediction History is completely independent from the
Prediction Engine: this package never performs inference, never loads
AI models, and never recalculates a prediction. It only consumes the
already-computed `app.services.prediction_result.PredictionResult` and
`app.services.prediction_context.PredictionContext` produced by the
existing prediction pipeline.

This phase (5.1) introduces the domain model and mapping architecture
only. No database access, persistence, or retrieval exists in this
package yet:
    - Phase 5.1: Prediction History Foundation (this phase)
    - Phase 5.2: History Persistence (ADR-033)
    - Phase 5.3: History Retrieval
    - Phase 5.4: History Pagination & Filtering
    - Phase 5.5: History Detail API
"""
