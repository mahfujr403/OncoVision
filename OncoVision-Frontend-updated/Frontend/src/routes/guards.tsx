import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { isAdmin, hasPermission, type Permission } from '@/utils/permissions';
import { ROUTES } from '@/constants/routes';
import { PageLoader } from '@/components/ui/Loader';
import type { UserRole } from '@/types';

export function ProtectedRoute() {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) return <PageLoader />;
  if (!isAuthenticated) {
    return <Navigate to={ROUTES.LOGIN} state={{ from: location }} replace />;
  }
  return <Outlet />;
}

export function PublicRoute() {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) return <PageLoader />;
  if (isAuthenticated) return <Navigate to={ROUTES.DASHBOARD} replace />;

  return <Outlet />;
}

export function AdminRoute() {
  const { user, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) return <PageLoader />;
  if (!isAdmin(user?.role)) {
    return <Navigate to={ROUTES.DASHBOARD} state={{ from: location }} replace />;
  }
  return <Outlet />;
}

// NOTE: a ResearcherRoute previously existed here, gating Comparison/
// Benchmark behind a 'researcher' role. The real backend only has
// 'admin'/'user' (app/models/enums.py) — there is no restricted middle
// tier — so those routes are now just ProtectedRoute like everything else.
// See utils/permissions.ts for the corresponding permission change.

export function RoleRoute({ allowedRoles }: { allowedRoles: UserRole[] }) {
  const { user, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) return <PageLoader />;
  if (!user || !allowedRoles.includes(user.role)) {
    return <Navigate to={ROUTES.DASHBOARD} state={{ from: location }} replace />;
  }
  return <Outlet />;
}

export function PermissionRoute({ permission }: { permission: Permission }) {
  const { user, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) return <PageLoader />;
  if (!hasPermission(user?.role, permission)) {
    return <Navigate to={ROUTES.DASHBOARD} state={{ from: location }} replace />;
  }
  return <Outlet />;
}
