// Types mirror POST /api/v1/predictions exactly, as verified against
// app/api/v1/predictions/{router,schemas,responses,examples}.py and
// app/core/upload.py / app/core/settings.py (see Frontend Design Track,
// Phase 2 doc). Do not add fields here that the backend doesn't return.

export const ACCEPTED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.tif', '.tiff'] as const;
export const ACCEPTED_IMAGE_MIME_TYPES = ['image/jpeg', 'image/png', 'image/tiff'] as const;
export const MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024; // 10 MB, from Settings.MAX_UPLOAD_SIZE

/** Request options for POST /api/v1/predictions (multipart/form-data). */
export interface PredictionRequestOptions {
  /** 0.0–1.0. Flagging/reliability only — never alters inference. Default 0.5. */
  confidence_threshold: number;
  /** Default true. */
  include_individual_predictions: boolean;
  /** Default false. */
  include_runtime_statistics: boolean;
  /** Default true. Wired to real history persistence. */
  save_history: boolean;
  /**
   * Default false. Accepted by the backend for API contract stability only —
   * report generation is NOT performed by this endpoint yet. Never render a
   * "report generated" outcome from this flag.
   */
  generate_report: boolean;
}

export const DEFAULT_PREDICTION_OPTIONS: PredictionRequestOptions = {
  confidence_threshold: 0.5,
  include_individual_predictions: true,
  include_runtime_statistics: false,
  save_history: true,
  generate_report: false,
};

/** ADR-009 fault-tolerant ensemble status values. */
export type PredictionStatus = 'success' | 'partial_success' | 'failed' | 'pending';

export interface PredictionResult {
  prediction: string;
  /** 0–100 */
  confidence: number;
  /** 0–1. Not meaningful when only one model participated. */
  agreement_ratio: number;
  successful_models: string[];
  failed_models: string[];
  participating_models: number;
}

export interface IndividualModelPrediction {
  model_name: string;
  prediction: string;
  /** 0–100 */
  confidence: number;
  inference_time_ms: number;
}

export interface RuntimeStatistics {
  loaded_models: string[];
  failed_models: string[];
  total_models: number;
  runtime_status: string;
  loaded_model_count: number;
  successful_predictions: number;
  failed_predictions: number;
  participating_models: number;
  preprocessing_time_ms: number;
  total_inference_time_ms: number;
  total_execution_time_ms: number;
  overall_processing_time_ms: number;
}

export interface PredictionMetadata {
  api_version: string;
  backend_version: string;
  model_manifest_version: string;
  processing_time_ms: number;
}

/** data object of PredictionResponseSchema */
export interface PredictionResponse {
  prediction_id: string;
  status: PredictionStatus;
  message: string;
  timestamp: string;
  result: PredictionResult;
  individual_predictions: IndividualModelPrediction[] | null;
  runtime_statistics: RuntimeStatistics | null;
  metadata: PredictionMetadata;
}

/** Standard API envelope error entry. */
export interface ApiErrorDetail {
  field?: string;
  message: string;
}

export interface ApiErrorEnvelope {
  success: false;
  message: string;
  data: null;
  errors: ApiErrorDetail[] | null;
  request_id: string;
  timestamp: string;
  /** HTTP status actually returned (400 / 401 / 422 / 503 / 500). */
  status: number;
}
