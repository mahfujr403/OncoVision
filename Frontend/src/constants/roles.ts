import type { UserRole } from '@/types';

// Verified against app/models/enums.py — UserRole has exactly two members.
// Do not add DOCTOR/RESEARCHER/VIEWER (or any other role) here unless the
// backend enum is actually extended; the previous Figma build invented
// three roles the backend has never supported.
export const ROLES: Record<string, UserRole> = {
  ADMIN: 'admin',
  USER: 'user',
} as const;

export const ROLE_LABELS: Record<UserRole, string> = {
  admin: 'Administrator',
  user: 'User',
};

export const ROLE_HIERARCHY: Record<UserRole, number> = {
  admin: 2,
  user: 1,
};

export const hasAdminAccess = (role?: UserRole): boolean => role === ROLES.ADMIN;
