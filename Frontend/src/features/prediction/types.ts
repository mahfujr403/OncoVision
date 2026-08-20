export type WorkspaceStatus = 'idle' | 'uploading' | 'processing' | 'complete' | 'error';

export interface ModelInfo {
  id: string;
  name: string;
  version: string;
  architecture: string;
  active: boolean;
}

export interface WorkflowStep {
  step: number;
  label: string;
  description: string;
  icon: string;
}

// ── Upload ────────────────────────────────────────────────────────────────────

export type UploadState = 'idle' | 'dragging' | 'validating' | 'ready' | 'error';

export type AnalyzeStep = 'upload' | 'prepare' | 'request' | 'waiting';

export type StepStatus = 'pending' | 'active' | 'done' | 'error';

export interface AnalyzeStepInfo {
  id: AnalyzeStep;
  label: string;
  status: StepStatus;
}

export interface ImageMeta {
  file: File;
  previewUrl: string;
  width: number;
  height: number;
  sizeBytes: number;
  mimeType: string;
  ext: string;
}

export interface ValidationError {
  code: 'type' | 'size' | 'corrupt' | 'empty' | 'unknown';
  message: string;
}

// Real, backend-accepted prediction options (verified against
// app/api/v1/predictions/schemas.py). `ensembleMethod` and `modelVersion`
// were removed — the backend has no such request fields; ensemble strategy
// and model versions are entirely server-controlled (ADR-006, ADR-009) and
// are never something the client selects.
export interface PredictionConfig {
  confidenceThreshold: number;
  includeIndividualPredictions: boolean;
  includeRuntimeStatistics: boolean;
  saveHistory: boolean;
  /** Accepted by the backend for contract stability — NOT yet acted on. */
  generateReport: boolean;
  imageSize: string;
}
