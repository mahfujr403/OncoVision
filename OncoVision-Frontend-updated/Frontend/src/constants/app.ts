export const APP_NAME = 'OncoVision AI';
export const APP_TAGLINE = 'AI-Assisted Histopathology Image Analysis';
export const APP_VERSION = '1.0.0';

// Verified against app/ml/manifest/models.json in the uploaded backend
// source. These are the ONLY 5 class labels the current manifest defines.
// The backend schema types `predicted_class` as a plain string (not a
// server-enforced enum), so unknown values are handled gracefully by
// getClassLabelColor() below rather than assumed impossible.
export const KNOWN_CLASS_LABELS = [
  'Lung Adenocarcinoma',
  'Lung Squamous Cell Carcinoma',
  'Lung Benign Tissue',
  'Colon Adenocarcinoma',
  'Colon Benign Tissue',
] as const;

export const CLASS_LABEL_COLORS: Record<string, string> = {
  'Lung Adenocarcinoma': '#ef4444',
  'Lung Squamous Cell Carcinoma': '#f97316',
  'Lung Benign Tissue': '#22c55e',
  'Colon Adenocarcinoma': '#a855f7',
  'Colon Benign Tissue': '#06b6d4',
};

export const getClassLabelColor = (label: string | null | undefined): string =>
  (label && CLASS_LABEL_COLORS[label]) || '#64748b'; // neutral slate fallback for unknown labels

export const CONFIDENCE_THRESHOLDS = {
  HIGH: 0.85,
  MEDIUM: 0.7,
} as const;

// Verified against app/api/v1/predictions/constants.py — TIFF is accepted,
// BMP is not.
export const ACCEPTED_IMAGE_TYPES = {
  'image/jpeg': ['.jpg', '.jpeg'],
  'image/png': ['.png'],
  'image/tiff': ['.tif', '.tiff'],
} as const;

// Verified against app/core/settings.py: Settings.MAX_UPLOAD_SIZE = 10 MB.
export const MAX_IMAGE_SIZE_MB = 10;
export const MAX_IMAGE_SIZE_BYTES = MAX_IMAGE_SIZE_MB * 1024 * 1024;

export const DEFAULT_PAGE_SIZE = 20;
export const PAGE_SIZE_OPTIONS = [10, 20, 50, 100] as const;

// DEMO ONLY — legacy snake_case labels kept solely so the still-unwired
// demo pages (Favorites, Saved Cases) keep compiling. Do not use these for
// anything backed by real data; use KNOWN_CLASS_LABELS / getClassLabelColor
// above instead, which match the real manifest values.
export const CANCER_TYPE_LABELS: Record<string, string> = {
  lung_aca: 'Lung Adenocarcinoma',
  lung_scc: 'Lung Squamous Cell Carcinoma',
  lung_benign: 'Lung Benign Tissue',
  colon_aca: 'Colon Adenocarcinoma',
  colon_benign: 'Colon Benign Tissue',
};

export const DEBOUNCE_MS = 350;
export const STALE_TIME_MS = 5 * 60 * 1000;
export const CACHE_TIME_MS = 10 * 60 * 1000;
