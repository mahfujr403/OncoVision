import type { UserRole } from '@/types';

export const ROLES = {
  ADMIN: 'admin' as UserRole,
  USER: 'user' as UserRole,
} as const;

// Backend only supports 'admin' and 'user'
export const ROLE_LABELS: Record<UserRole, string> = {
  admin: 'Administrator',
  user: 'User',
};

export const hasAdminAccess = (role?: UserRole): boolean => role === 'admin';
