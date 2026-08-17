export const APP_NAME = 'OncoVision AI';
export const APP_TAGLINE = 'Precision Cancer Pathology Classification';
export const APP_VERSION = '1.0.0';

export const CANCER_TYPE_LABELS: Record<string, string> = {
  lung_aca: 'Lung Adenocarcinoma',
  lung_scc: 'Lung Squamous Cell Carcinoma',
  lung_benign: 'Lung Benign Tissue',
  colon_aca: 'Colon Adenocarcinoma',
  colon_benign: 'Colon Benign Tissue',
};

export const CANCER_TYPE_COLORS: Record<string, string> = {
  lung_aca: '#ef4444',
  lung_scc: '#f97316',
  lung_benign: '#22c55e',
  colon_aca: '#a855f7',
  colon_benign: '#06b6d4',
};

export const CONFIDENCE_THRESHOLDS = {
  HIGH: 0.85,
  MEDIUM: 0.70,
} as const;

export const ACCEPTED_IMAGE_TYPES = {
  'image/jpeg': ['.jpg', '.jpeg'],
  'image/png': ['.png'],
  'image/tiff': ['.tif', '.tiff'],
  'image/bmp': ['.bmp'],
} as const;

export const MAX_IMAGE_SIZE_MB = 10;
export const MAX_IMAGE_SIZE_BYTES = MAX_IMAGE_SIZE_MB * 1024 * 1024;

export const DEFAULT_PAGE_SIZE = 20;
export const PAGE_SIZE_OPTIONS = [10, 20, 50, 100] as const;

export const DEBOUNCE_MS = 350;
export const STALE_TIME_MS = 5 * 60 * 1000;
export const CACHE_TIME_MS = 10 * 60 * 1000;
