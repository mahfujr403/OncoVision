import type { PredictionStatus } from './prediction';

// ⚠️ VERIFICATION STATUS: LOWEST CONFIDENCE OF THE THREE DOMAIN TYPE FILES.
//
// The project's documented backend contract only says the analytics endpoint
// exists (GET /api/v1/reports/analytics) and lists what the frontend should
// eventually show — "Prediction statistics, Class distribution, Confidence
// distribution" — but does NOT document the actual response field names,
// unlike the prediction and (partially) history contracts. Nothing below is
// a verified backend contract. It is a reasonable placeholder shape built to
// exercise the UI, and MUST be replaced by types read directly from
// app/api/v1/reports/{router,schemas}.py before any real integration.
// The "Do not invent accuracy/precision/recall/F1/ROC metrics" rule is
// followed: nothing below is a model-quality metric, only descriptive counts
// over the user's own prediction history.

export interface AnalyticsSummary {
  total_predictions: number;
  status_counts: Record<PredictionStatus, number>;
  average_confidence: number; // 0-100, over non-failed predictions
  average_processing_time_ms: number;
  class_distribution: { predicted_class: string; count: number }[];
  confidence_distribution: { bucket_label: string; count: number }[];
}
