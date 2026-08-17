import type { UserRole } from '@/types';

// Backend supports only 'admin' and 'user' roles.
// Permission-level routing has been retired — use AdminRoute for admin-only pages.

export function isAdmin(role: UserRole | undefined | null): boolean {
  return role === 'admin';
}

export function isUser(role: UserRole | undefined | null): boolean {
  return role === 'user' || role === 'admin';
}
