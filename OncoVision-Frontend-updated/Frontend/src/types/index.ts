// ============================================================================
// OncoVision AI — Frontend Types
//
// Every type below the "REAL BACKEND CONTRACT" divider is copied field-for-
// field from the actual backend Pydantic schemas (verified against
// `app/schemas/*.py` and `app/api/v1/**/responses.py` in the uploaded
// backend source). Do not add fields here that the backend does not return.
//
// Types below the "DEMO-ONLY TYPES" divider back UI that has no backend
// endpoint at all (see project instructions §"tag demo data"). Components
// using them MUST render a visible "Demo data" indicator — see
// `components/ui/DemoDataBanner.tsx`.
// ============================================================================

// ---------------------------------------------------------------------------
// REAL BACKEND CONTRACT
// ---------------------------------------------------------------------------

/** Backend enum: `app.models.enums.UserRole`. Only these two values exist. */
export type UserRole = 'admin' | 'user';

/** `app.schemas.user.UserResponse` */
export interface User {
  id: string;
  full_name: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  is_verified: boolean;
  avatar_url: string | null;
  last_login: string | null;
  created_at: string;
}

/** `app.schemas.auth.TokenResponse` (login/refresh) */
export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

// -- Prediction (`POST /api/v1/predictions`) --------------------------------

/** `app.api.v1.predictions.responses.PredictionStatus` */
export type PredictionStatus = 'pending' | 'success' | 'partial_success' | 'failed';

/** `app.api.v1.predictions.responses.RuntimeHealthStatus` */
export type RuntimeHealthStatus = 'operational' | 'degraded' | 'unavailable';

/** `app.api.v1.predictions.responses.IndividualModelResultSchema` */
export interface IndividualModelResult {
  model_name: string;
  prediction: string;
  confidence: number; // 0-100
  inference_time_ms: number;
}

/** `app.api.v1.predictions.responses.PredictionRuntimeSchema` */
export interface PredictionRuntimeStatistics {
  loaded_models: string[];
  failed_models: string[];
  total_models: number;
  runtime_status: RuntimeHealthStatus;
  loaded_model_count: number | null;
  successful_predictions: number | null;
  failed_predictions: number | null;
  participating_models: number | null;
  preprocessing_time_ms: number | null;
  total_inference_time_ms: number | null;
  total_execution_time_ms: number | null;
  overall_processing_time_ms: number | null;
}

/** `app.api.v1.predictions.responses.PredictionResultSchema` */
export interface PredictionResult {
  prediction: string;
  confidence: number; // 0-100
  agreement_ratio: number; // 0-1
  successful_models: string[];
  failed_models: string[];
  participating_models: number;
}

/** `app.api.v1.predictions.responses.PredictionMetadataSchema` */
export interface PredictionMetadata {
  api_version: string;
  backend_version: string;
  model_manifest_version: string | null;
  processing_time_ms: number;
}

/** `app.api.v1.predictions.responses.PredictionResponseSchema` */
export interface PredictionResponse {
  prediction_id: string;
  status: PredictionStatus;
  message: string;
  timestamp: string;
  result: PredictionResult | null;
  individual_predictions: IndividualModelResult[] | null;
  runtime_statistics: PredictionRuntimeStatistics | null;
  metadata: PredictionMetadata;
}

/** Real, optional request flags accepted by `POST /api/v1/predictions`. */
export interface PredictionRequestOptions {
  confidence_threshold: number; // 0-1, flagging only — never alters inference
  include_individual_predictions: boolean;
  include_runtime_statistics: boolean;
  save_history: boolean;
  /** Accepted by the backend for contract stability but NOT YET acted on. */
  generate_report: boolean;
}

// -- Prediction History (`/api/v1/predictions/history`) ---------------------

/** `app.history.enums.PredictionHistoryStatus` — same value set as PredictionStatus. */
export type PredictionHistoryStatus = PredictionStatus;

/** `app.api.v1.history.responses.PredictionHistoryModelEntrySchema` */
export interface PredictionHistoryModelEntry {
  model_name: string;
  prediction: string;
  confidence: number;
  inference_time_ms: number;
}

/** `app.api.v1.history.responses.PredictionHistoryItemSchema` */
export interface PredictionHistoryItem {
  history_id: string;
  request_id: string;
  status: PredictionHistoryStatus;
  created_at: string;
  image_filename: string;
  predicted_class: string | null;
  confidence: number;
  agreement_ratio: number;
  successful_models: string[];
  failed_models: string[];
  participating_models: number;
  individual_predictions: PredictionHistoryModelEntry[];
}

/** `app.api.v1.history.responses.PredictionHistoryPaginationSchema` */
export interface HistoryPagination {
  current_page: number;
  page_size: number;
  total_records: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
}

/** `app.api.v1.history.responses.PredictionHistoryListResponseSchema` */
export interface PredictionHistoryListResponse {
  items: PredictionHistoryItem[];
  count: number;
  pagination: HistoryPagination;
}

/** `app.api.v1.history.responses.PredictionHistoryImageMetadataSchema` */
export interface PredictionHistoryImageMetadata {
  filename: string;
  content_type: string;
  size_bytes: number;
  width: number;
  height: number;
}

/** `app.api.v1.history.responses.PredictionHistoryRuntimeInfoSchema` */
export interface PredictionHistoryRuntimeInfo {
  model_manifest_version: string | null;
  processing_time_ms: number | null;
}

/** `app.api.v1.history.responses.PredictionHistoryDetailResponseSchema` */
export interface PredictionHistoryDetail {
  history_id: string;
  request_id: string;
  status: PredictionHistoryStatus;
  created_at: string;
  predicted_class: string | null;
  confidence: number;
  agreement_ratio: number;
  successful_models: string[];
  failed_models: string[];
  participating_models: number;
  individual_predictions: PredictionHistoryModelEntry[];
  image_metadata: PredictionHistoryImageMetadata;
  runtime_info: PredictionHistoryRuntimeInfo;
}

/** Real, server-validated query params for `GET /predictions/history`. */
export interface HistoryQueryParams {
  page?: number;
  page_size?: number;
  status?: PredictionHistoryStatus;
  predicted_class?: string;
  start_date?: string;
  end_date?: string;
  min_confidence?: number;
  max_confidence?: number;
}

// -- Reports / Analytics (`/api/v1/reports/*`) -------------------------------

/** `app.schemas.reports.PredictionAnalyticsResponseSchema` */
export interface PredictionAnalytics {
  analytics_id: string;
  generated_at: string;
  total_predictions: number;
  successful_predictions: number;
  failed_predictions: number;
  success_rate: number; // 0-100
  average_confidence: number; // 0-100
  average_agreement_ratio: number; // 0-1
  most_predicted_class: string | null;
  class_distribution: Record<string, number>;
  confidence_distribution: Record<string, number>;
  first_prediction_date: string | null;
  latest_prediction_date: string | null;
  predictions_today: number;
  predictions_this_week: number;
  predictions_this_month: number;
}

// -- Admin (`/api/v1/admin/*`) -----------------------------------------------

/** `app.schemas.admin.AdminPaginationSchema` — same shape as HistoryPagination. */
export type AdminPagination = HistoryPagination;

/** `app.api.v1.admin.users` list response */
export interface AdminUserListResponse {
  items: User[];
  count: number;
  pagination: AdminPagination;
}

/** `app.schemas.admin.AdminSystemStatusSchema` — nested objects are backend-defined
 *  free-form dicts (`application`, `database`, `runtime`, `models`); render them
 *  generically rather than assuming a fixed shape. */
export interface AdminSystemStatus {
  application: Record<string, unknown>;
  database: Record<string, unknown>;
  runtime: Record<string, unknown>;
  models: Record<string, unknown>;
  generated_at: string;
}

/** `app.schemas.admin.AdminHistoryItemSchema` — same shape as the
 *  user-scoped `PredictionHistoryItemSchema` plus `user_id`, the one
 *  field administrative oversight needs but self-service retrieval
 *  never exposes. */
export interface AdminHistoryItem extends PredictionHistoryItem {
  user_id: string;
}

/** `app.schemas.admin.AdminHistoryDetailResponseSchema` — extends
 *  `AdminHistoryItemSchema` with the same runtime/image metadata fields
 *  `PredictionHistoryDetail` exposes, but flat rather than nested. */
export interface AdminHistoryDetail extends AdminHistoryItem {
  image_content_type: string;
  image_size_bytes: number;
  image_width: number;
  image_height: number;
  model_manifest_version: string | null;
  processing_time_ms: number | null;
}

// -- Monitoring (`/api/v1/monitoring`) ---------------------------------------

export type ComponentStatus = 'healthy' | 'degraded' | 'down' | 'unknown';

export interface ApplicationHealth {
  status: ComponentStatus;
  name: string;
  version: string;
  environment: string;
}

export interface DatabaseHealth {
  status: ComponentStatus;
  connected: boolean;
}

export interface ModelHealth {
  model_id: string;
  display_name: string;
  state: string;
  is_available: boolean;
  error_message: string | null;
}

export interface RuntimeHealth {
  status: ComponentStatus;
  is_operational: boolean;
  total_model_count: number;
  loaded_model_count: number;
  failed_model_count: number;
  pending_model_count: number;
  disabled_model_count: number;
  models: ModelHealth[];
}

export interface RequestMetrics {
  total_requests: number;
  status_2xx: number;
  status_3xx: number;
  status_4xx: number;
  status_5xx: number;
  average_duration_ms: number;
}

export interface PredictionRequestMetrics {
  total_requests: number;
  successful_requests: number;
  failed_requests: number;
}

/** `app.schemas.monitoring.MonitoringStatusSchema` */
export interface MonitoringStatus {
  status: ComponentStatus;
  application: ApplicationHealth;
  database: DatabaseHealth;
  runtime: RuntimeHealth;
  request_metrics: RequestMetrics;
  prediction_metrics: PredictionRequestMetrics;
  generated_at: string;
}

// -- System (`/api/v1/system*`) — /system loosely typed; /system/models has
// a concrete shape (ModelRegistryResponse), verified in
// app/ml/metadata/metadata_service.py + app/ml/metadata/schemas (ModelSummary).
export type SystemInfo = Record<string, unknown>;

export interface ModelSummary {
  id: string;
  display_name: string;
  version: string;
  framework: string;
  format: string;
  priority: number;
  ensemble_weight: number;
  input_size: number[] | number;
  num_classes: number;
  class_labels: string[];
  enabled: boolean;
  is_cached: boolean;
  description: string | null;
}

export interface ModelRegistryResponse {
  manifest_version: string;
  total_models: number;
  enabled_models: number;
  disabled_models: number;
  available_models: number;
  models: ModelSummary[];
}

export type ModelRuntimeStatusList = Record<string, unknown>;

// -- Global response envelope -------------------------------------------------

/** `app.schemas.response.APIResponse[T]` — every endpoint returns this shape. */
export interface ApiEnvelope<T> {
  success: boolean;
  message: string;
  data: T | null;
  errors: ApiErrorDetail[] | null;
  request_id: string;
  timestamp: string;
}

export interface ApiErrorDetail {
  code?: string | null;
  field?: string | null;
  message: string;
}

/** Normalized shape thrown by the axios interceptor on any failed request. */
export interface ApiError {
  message: string;
  statusCode?: number;
  requestId?: string;
  errors?: ApiErrorDetail[] | null;
}

// ============================================================================
// DEMO-ONLY TYPES
// No backend endpoint exists for any of the following today. Pages using
// these types must render <DemoDataBanner /> — do not present this data as
// live/real anywhere in the UI.
// ============================================================================

/** DEMO ONLY — no `/models` CRUD endpoint exists; not returned by the backend. */
export interface DemoModelBenchmark {
  id: string;
  modelName: string;
  architecture: string;
  accuracy: number;
  precision: number;
  recall: number;
  f1Score: number;
  auc: number;
  avgInferenceTimeMs: number;
  datasetName: string;
  datasetSize: number;
  runAt: string;
}

/** DEMO ONLY — no `/notifications` endpoint exists on the backend. */
export type NotificationLevel = 'info' | 'success' | 'warning' | 'error';

export interface DemoNotification {
  id: string;
  title: string;
  message: string;
  level: NotificationLevel;
  isRead: boolean;
  createdAt: string;
}

/** DEMO ONLY — no saved-cases/favorites endpoint exists; `save_history` only
 *  controls whether a prediction is written to Prediction History. */
export interface DemoSavedCase {
  id: string;
  imageName: string;
  predictedClass: string;
  confidence: number;
  note?: string;
  savedAt: string;
}

/** DEMO ONLY — no comparison endpoint/workflow exists on the backend. */
export interface DemoComparisonCase {
  id: string;
  imageNameA: string;
  imageNameB: string;
  createdAt: string;
}

/** DEMO ONLY — no audit-log endpoint exists on the backend. */
export interface DemoAuditLogEntry {
  id: string;
  actor: string;
  action: string;
  target: string;
  createdAt: string;
}
