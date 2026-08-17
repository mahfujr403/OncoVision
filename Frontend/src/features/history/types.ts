import type { IndividualPrediction, BackendPredictionStatus } from '@/types';

export interface PredictionHistoryItem {
  history_id: string;
  request_id: string;
  status: BackendPredictionStatus;
  created_at: string;
  image_filename: string;
  predicted_class: string | null;
  /** Already a percentage (0–100) — render directly */
  confidence: number;
  agreement_ratio: number;
  successful_models: string[];
  failed_models: string[];
  participating_models: number;
  individual_predictions: IndividualPrediction[];
}

export interface PredictionHistoryPagination {
  current_page: number;
  page_size: number;
  total_records: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
}

export interface PredictionHistoryListResponse {
  items: PredictionHistoryItem[];
  count: number;
  pagination: PredictionHistoryPagination;
}

export interface PredictionHistoryImageMetadata {
  filename: string;
  content_type: string;
  size_bytes: number;
  width: number;
  height: number;
}

export interface PredictionHistoryRuntimeInfo {
  model_manifest_version: string | null;
  processing_time_ms: number | null;
}

export interface PredictionHistoryDetail extends PredictionHistoryItem {
  image_metadata: PredictionHistoryImageMetadata;
  runtime_info: PredictionHistoryRuntimeInfo;
}

export interface PredictionHistoryFilters {
  page?: number;
  page_size?: number;
  status?: BackendPredictionStatus;
  predicted_class?: string;
  start_date?: string;
  end_date?: string;
  min_confidence?: number;
  max_confidence?: number;
}
