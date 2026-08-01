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

Phase 5.1 introduced the domain model and mapping architecture. Later
phases extend the same package without redesigning it:
    - Phase 5.1: Prediction History Foundation
    - Phase 5.2: History Persistence (ADR-033)
    - Phase 5.3: History Retrieval (ADR-034)
    - Phase 5.4: History Pagination & Filtering (ADR-035, this phase) --
      adds `PredictionHistoryFilter` (`filters.py`) and
      `PredictionHistoryPageRequest` / `PredictionHistoryPageMetadata` /
      `PredictionHistoryPage` (`pagination.py`) as the domain value
      objects consumed by the now-implemented
      `PredictionHistoryRepository.list_by_user()` /
      `.count_by_user()` filter parameters and
      `PredictionHistoryService.list_history_page()`.
    - Phase 5.5: History Detail API
"""
