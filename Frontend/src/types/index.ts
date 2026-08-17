// Matches the backend's UserResponse exactly — roles are 'admin' | 'user' only
export type UserRole = 'admin' | 'user';

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

export type CancerType = 'lung' | 'colon';
export type CancerSubtype =
  | 'lung_aca'
  | 'lung_scc'
  | 'lung_benign'
  | 'colon_aca'
  | 'colon_benign';

export type PredictionStatus = 'pending' | 'processing' | 'completed' | 'failed';
export type ConfidenceLevel = 'high' | 'medium' | 'low';

export interface ModelPrediction {
  modelId: string;
  modelName: string;
  label: CancerSubtype;
  confidence: number;
  probabilities: Record<CancerSubtype, number>;
  inferenceTimeMs: number;
}

export interface Prediction {
  id: string;
  userId: string;
  imageUrl: string;
  imageName: string;
  imageSize: number;
  status: PredictionStatus;
  cancerType?: CancerType;
  finalLabel?: CancerSubtype;
  ensembleConfidence?: number;
  confidenceLevel?: ConfidenceLevel;
  modelPredictions: ModelPrediction[];
  notes?: string;
  isFavorite: boolean;
  tags: string[];
  createdAt: string;
  completedAt?: string;
}

export type ModelStatus = 'active' | 'inactive' | 'deprecated' | 'training';
export type ModelArchitecture =
  | 'ResNet50'
  | 'EfficientNetB4'
  | 'VGG16'
  | 'DenseNet121'
  | 'InceptionV3'
  | 'ViT-B16';

export interface Model {
  id: string;
  name: string;
  architecture: ModelArchitecture;
  version: string;
  status: ModelStatus;
  accuracy: number;
  precision: number;
  recall: number;
  f1Score: number;
  auc: number;
  trainedOn: string;
  datasetSize: number;
  parameters: number;
  inferenceTimeMs: number;
  description?: string;
  createdAt: string;
  updatedAt: string;
}

export interface BenchmarkResult {
  id: string;
  modelId: string;
  modelName: string;
  datasetName: string;
  datasetSize: number;
  accuracy: number;
  precision: number;
  recall: number;
  f1Score: number;
  auc: number;
  avgInferenceTimeMs: number;
  runAt: string;
}

export interface HistoryItem {
  id: string;
  predictionId: string;
  imageName: string;
  status: PredictionStatus;
  finalLabel?: CancerSubtype;
  confidence?: number;
  createdAt: string;
}

export type NotificationLevel = 'info' | 'success' | 'warning' | 'error';

export interface Notification {
  id: string;
  userId: string;
  title: string;
  message: string;
  level: NotificationLevel;
  isRead: boolean;
  link?: string;
  createdAt: string;
}

export interface Report {
  id: string;
  userId: string;
  title: string;
  predictionIds: string[];
  summary?: string;
  generatedAt: string;
  format: 'pdf' | 'csv' | 'json';
  url?: string;
}

// ── Prediction API (backend contract, Phase 5) ────────────────────────────────

/** Maps exactly to backend PredictionStatus enum */
export type BackendPredictionStatus = 'pending' | 'success' | 'partial_success' | 'failed';

export interface PredictionResult {
  prediction: string;
  /** Already a percentage (0–100) — render directly, do not multiply */
  confidence: number;
  agreement_ratio: number;
  successful_models: string[];
  failed_models: string[];
  participating_models: number;
}

export interface IndividualPrediction {
  model_name: string;
  prediction: string;
  /** Already a percentage (0–100) */
  confidence: number;
  inference_time_ms: number;
}

export interface RuntimeStatistics {
  loaded_models: string[];
  failed_models: string[];
  total_models: number;
  runtime_status: 'operational' | 'degraded' | 'unavailable';
  loaded_model_count: number | null;
  successful_predictions: number | null;
  failed_predictions: number | null;
  participating_models: number | null;
  preprocessing_time_ms: number | null;
  total_inference_time_ms: number | null;
  total_execution_time_ms: number | null;
  overall_processing_time_ms: number | null;
}

export interface PredictionMetadata {
  api_version: string;
  backend_version: string;
  model_manifest_version: string | null;
  processing_time_ms: number;
}

export interface PredictionResponse {
  prediction_id: string;
  status: BackendPredictionStatus;
  message: string;
  timestamp: string;
  result: PredictionResult | null;
  individual_predictions: IndividualPrediction[] | null;
  runtime_statistics: RuntimeStatistics | null;
  metadata: PredictionMetadata;
}

export interface PredictionRequestOptions {
  confidence_threshold?: number;
  include_individual_predictions?: boolean;
  include_runtime_statistics?: boolean;
  save_history?: boolean;
  generate_report?: boolean;
}

// Matches the backend envelope exactly
export interface ApiResponse<T> {
  success: boolean;
  message: string;
  data: T | null;
  errors: unknown | null;
  request_id: string;
  timestamp: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  limit: number;
  totalPages: number;
}

export interface ApiError {
  message: string;
  code?: string;
  statusCode?: number;
  details?: Record<string, string[]>;
}

// Token shape returned by /auth/login and /auth/refresh
export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

// Login response data
export interface LoginResponseData {
  user: User;
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

// Register response data
export interface RegisterResponseData {
  user: User;
}

// Refresh response data
export interface RefreshResponseData {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface SystemHealth {
  status: 'healthy' | 'degraded' | 'down';
  uptime: number;
  modelServicesOnline: number;
  totalModels: number;
  predictionsToday: number;
  queueDepth: number;
  avgInferenceMs: number;
  lastChecked: string;
}
