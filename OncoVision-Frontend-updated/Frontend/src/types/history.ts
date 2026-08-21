import type { PredictionStatus, IndividualModelPrediction } from './prediction';

// NOTE ON VERIFICATION: unlike the Phase 2 prediction contract (verified
// directly against backend source), the exact shape of the history list
// pagination envelope has NOT been verified against app/api/v1/history/
// source in this session — no backend codebase was available to read. The
// per-record field list below IS taken from the project's documented
// backend contract (history_id, request_id, status, ... created_at) and
// the filter field names are documented the same way. The pagination
// wrapper shape (page/page_size/total_items/total_pages/has_next) is a
// reasonable, clearly-labeled assumption pending that verification — see
// the "Simulated data" badge on HistoryPage. Do not treat this file as a
// verified contract the way prediction.ts is.

export type HistoryStatus = PredictionStatus;

export interface HistoryFilters {
  page: number;
  page_size: number;
  status: HistoryStatus | 'all';
  predicted_class: string | 'all';
  start_date: string | null; // ISO date
  end_date: string | null; // ISO date
  min_confidence: number | null; // 0-100
  max_confidence: number | null; // 0-100
}

export const DEFAULT_HISTORY_FILTERS: HistoryFilters = {
  page: 1,
  page_size: 10,
  status: 'all',
  predicted_class: 'all',
  start_date: null,
  end_date: null,
  min_confidence: null,
  max_confidence: null,
};

/** A single prediction history record, as documented. */
export interface HistoryRecord {
  history_id: string;
  request_id: string;
  status: HistoryStatus;
  image_filename: string;
  predicted_class: string;
  confidence: number; // 0-100
  agreement_ratio: number; // 0-1
  successful_models: string[];
  failed_models: string[];
  participating_models: number;
  individual_predictions: IndividualModelPrediction[] | null;
  image_content_type: string;
  image_size_bytes: number;
  image_width: number;
  image_height: number;
  model_manifest_version: string;
  processing_time_ms: number;
  created_at: string; // ISO timestamp
}

/** Assumed pagination wrapper — see verification note above. */
export interface PaginatedHistoryResponse {
  items: HistoryRecord[];
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
}
