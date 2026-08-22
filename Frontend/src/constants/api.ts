// Verified against app/api/v1/**/router.py in the uploaded backend source.
// Do not add an endpoint here that does not exist in that source.

export const API_BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1';

export const API_ENDPOINTS = {
  AUTH: {
    REGISTER: '/auth/register',
    LOGIN: '/auth/login',
    REFRESH: '/auth/refresh',
    LOGOUT: '/auth/logout',
    LOGOUT_ALL: '/auth/logout-all',
    ME: '/auth/me',
    // NOTE: forgot-password / reset-password / verify-email / change-password
    // do NOT exist on the backend. Do not add them here — the corresponding
    // pages are demo-only (see DemoDataBanner usage in those pages).
  },
  PREDICTIONS: {
    CREATE: '/predictions',
    HISTORY: '/predictions/history',
    HISTORY_DETAIL: (id: string) => `/predictions/history/${id}`,
  },
  REPORTS: {
    ANALYTICS: '/reports/analytics',
    EXPORT_CSV: '/reports/export/csv',
    EXPORT_PDF: '/reports/export/pdf',
  },
  ADMIN: {
    USERS: '/admin/users',
    USER_DETAIL: (id: string) => `/admin/users/${id}`,
    USER_ACTIVATE: (id: string) => `/admin/users/${id}/activate`,
    USER_DEACTIVATE: (id: string) => `/admin/users/${id}/deactivate`,
    HISTORY: '/admin/history',
    HISTORY_DETAIL: (id: string) => `/admin/history/${id}`,
    ANALYTICS: '/admin/analytics',
    SYSTEM: '/admin/system',
  },
  MONITORING: '/monitoring',
  SYSTEM: {
    INFO: '/system',
    MODELS: '/system/models',
    RUNTIME: '/system/runtime',
    MODELS_STATUS: '/system/models/status',
  },
  HEALTH: '/health',
} as const;

export const QUERY_KEYS = {
  ME: ['auth', 'me'] as const,
  PREDICTION_HISTORY: (params: unknown) => ['predictions', 'history', params] as const,
  PREDICTION_HISTORY_DETAIL: (id: string) => ['predictions', 'history', id] as const,
  ANALYTICS: ['reports', 'analytics'] as const,
  ADMIN_USERS: (params: unknown) => ['admin', 'users', params] as const,
  ADMIN_USER: (id: string) => ['admin', 'users', id] as const,
  ADMIN_HISTORY: (params: unknown) => ['admin', 'history', params] as const,
  ADMIN_ANALYTICS: (userId?: string) => ['admin', 'analytics', userId ?? 'all'] as const,
  ADMIN_SYSTEM: ['admin', 'system'] as const,
  MONITORING: ['monitoring'] as const,
  SYSTEM_INFO: ['system', 'info'] as const,
  SYSTEM_MODELS: ['system', 'models'] as const,
  SYSTEM_MODELS_STATUS: ['system', 'models', 'status'] as const,
} as const;
