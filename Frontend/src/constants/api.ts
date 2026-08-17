// Reads VITE_API_BASE_URL as documented in the backend contract
export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1';

export const API_ENDPOINTS = {
  AUTH: {
    LOGIN: '/auth/login',
    REGISTER: '/auth/register',
    LOGOUT: '/auth/logout',
    LOGOUT_ALL: '/auth/logout-all',
    REFRESH: '/auth/refresh',
    ME: '/auth/me',
  },
  PREDICTIONS: {
    BASE: '/predictions',
    HISTORY: '/predictions/history',
    HISTORY_BY_ID: (id: string) => `/predictions/history/${id}`,
  },
  REPORTS: {
    ANALYTICS: '/reports/analytics',
    EXPORT_CSV: '/reports/export/csv',
    EXPORT_PDF: '/reports/export/pdf',
  },
  ADMIN: {
    USERS: '/admin/users',
    USER_BY_ID: (id: string) => `/admin/users/${id}`,
    USER_ACTIVATE: (id: string) => `/admin/users/${id}/activate`,
    USER_DEACTIVATE: (id: string) => `/admin/users/${id}/deactivate`,
    HISTORY: '/admin/history',
    HISTORY_BY_ID: (id: string) => `/admin/history/${id}`,
    SYSTEM: '/admin/system',
  },
  SYSTEM: {
    INFO: '/system',
    MODELS: '/system/models',
    RUNTIME: '/system/runtime',
    MODEL_STATUS: '/system/models/status',
  },
  MONITORING: '/monitoring',
  HEALTH: '/health',
} as const;

export const QUERY_KEYS = {
  AUTH: {
    ME: ['auth', 'me'] as const,
  },
  HISTORY: {
    LIST: (filters?: Record<string, unknown>) =>
      filters ? ['history', 'list', filters] : (['history', 'list'] as const),
    DETAIL: (id: string) => ['history', 'detail', id] as const,
  },
  REPORTS: {
    ANALYTICS: ['reports', 'analytics'] as const,
  },
  ADMIN: {
    USERS: {
      LIST: (params?: Record<string, unknown>) =>
        params ? ['admin', 'users', 'list', params] : (['admin', 'users', 'list'] as const),
      DETAIL: (id: string) => ['admin', 'users', 'detail', id] as const,
    },
    HISTORY: {
      LIST: (params?: Record<string, unknown>) =>
        params ? ['admin', 'history', 'list', params] : (['admin', 'history', 'list'] as const),
      DETAIL: (id: string) => ['admin', 'history', 'detail', id] as const,
    },
    SYSTEM: ['admin', 'system'] as const,
  },
  SYSTEM: {
    INFO: ['system', 'info'] as const,
    MODELS: ['system', 'models'] as const,
    RUNTIME: ['system', 'runtime'] as const,
    MODEL_STATUS: ['system', 'model-status'] as const,
  },
  MONITORING: ['monitoring'] as const,
} as const;
