import type { UserRole } from '@/types';

export type Permission =
  | 'dashboard:view'
  | 'predict:view'
  | 'history:view'
  | 'reports:view'
  | 'saved-cases:view'
  | 'favorites:view'
  | 'notifications:view'
  | 'profile:view'
  | 'settings:view'
  | 'change-password:view'
  | 'comparison:view'
  | 'benchmark:view'
  | 'admin:view'
  | 'admin:users'
  | 'admin:models'
  | 'admin:analytics'
  | 'admin:audit-logs'
  | 'admin:system-health';

// Real backend roles are only 'admin' and 'user' (app/models/enums.py).
// Every general-purpose page — including the demo-only Comparison and
// Benchmark pages — is available to any authenticated user; there is no
// backend concept of a restricted "researcher" tier to gate them behind.
const GENERAL_PERMISSIONS: Permission[] = [
  'dashboard:view',
  'predict:view',
  'history:view',
  'reports:view',
  'saved-cases:view',
  'favorites:view',
  'notifications:view',
  'profile:view',
  'settings:view',
  'change-password:view',
  'comparison:view',
  'benchmark:view',
];

const ROLE_PERMISSIONS: Record<UserRole, Permission[]> = {
  user: GENERAL_PERMISSIONS,
  admin: [
    ...GENERAL_PERMISSIONS,
    'admin:view',
    'admin:users',
    'admin:models',
    'admin:analytics',
    'admin:audit-logs',
    'admin:system-health',
  ],
};

export function hasRole(role: UserRole | undefined, target: UserRole): boolean {
  return role === target;
}

export function hasPermission(role: UserRole | undefined, permission: Permission): boolean {
  if (!role) return false;
  return ROLE_PERMISSIONS[role]?.includes(permission) ?? false;
}

export function hasAnyPermission(role: UserRole | undefined, permissions: Permission[]): boolean {
  return permissions.some((p) => hasPermission(role, p));
}

export function canAccess(role: UserRole | undefined, route: string): boolean {
  const routePermissionMap: Record<string, Permission> = {
    '/dashboard': 'dashboard:view',
    '/dashboard/predict': 'predict:view',
    '/dashboard/history': 'history:view',
    '/dashboard/reports': 'reports:view',
    '/dashboard/comparison': 'comparison:view',
    '/dashboard/benchmark': 'benchmark:view',
    '/dashboard/admin/users': 'admin:users',
    '/dashboard/admin/models': 'admin:models',
    '/dashboard/admin/analytics': 'admin:analytics',
    '/dashboard/admin/audit-logs': 'admin:audit-logs',
    '/dashboard/admin/system-health': 'admin:system-health',
  };
  const permission = routePermissionMap[route];
  if (!permission) return true;
  return hasPermission(role, permission);
}

export function isAdmin(role: UserRole | undefined): boolean {
  return role === 'admin';
}

export function isAuthenticated(role: UserRole | undefined): boolean {
  return role !== undefined;
}

export function getRolePermissions(role: UserRole): Permission[] {
  return ROLE_PERMISSIONS[role] ?? [];
}
