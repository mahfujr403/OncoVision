export const ROUTES = {
  LANDING: '/',
  LOGIN: '/login',
  REGISTER: '/register',
  FORGOT_PASSWORD: '/forgot-password',
  RESET_PASSWORD: '/reset-password',
  VERIFY_EMAIL: '/verify-email',

  DASHBOARD: '/dashboard',
  PREDICT: '/dashboard/predict',
  HISTORY: '/dashboard/history',
  HISTORY_DETAIL: '/dashboard/history/:historyId',
  COMPARISON: '/dashboard/comparison',
  BENCHMARK: '/dashboard/benchmark',
  REPORTS: '/dashboard/reports',
  SAVED_CASES: '/dashboard/saved-cases',
  FAVORITES: '/dashboard/favorites',
  NOTIFICATIONS: '/dashboard/notifications',
  PROFILE: '/dashboard/profile',
  SETTINGS: '/dashboard/settings',
  CHANGE_PASSWORD: '/dashboard/change-password',

  ADMIN: '/dashboard/admin',
  ADMIN_USERS: '/dashboard/admin/users',
  ADMIN_MODELS: '/dashboard/admin/models',
  ADMIN_ANALYTICS: '/dashboard/admin/analytics',
  ADMIN_AUDIT_LOGS: '/dashboard/admin/audit-logs',
  ADMIN_SYSTEM_HEALTH: '/dashboard/admin/system-health',

  NOT_FOUND: '*',
} as const;

export type AppRoute = (typeof ROUTES)[keyof typeof ROUTES];
