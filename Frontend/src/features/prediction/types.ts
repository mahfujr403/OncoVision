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

export interface PredictionConfig {
  confidenceThreshold: number;
  ensembleMethod: string;
  imageSize: string;
  modelVersion: string;
}
