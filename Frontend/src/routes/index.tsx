import { lazy, Suspense } from 'react';
import { Routes, Route } from 'react-router-dom';
import { ROUTES } from '@/constants/routes';
import { DashboardLayout } from '@/layouts/DashboardLayout';
import { AuthLayout } from '@/layouts/AuthLayout';
import { LandingLayout } from '@/layouts/LandingLayout';
import { ProtectedRoute, PublicRoute, AdminRoute } from './guards';
import { PageLoader } from '@/components/ui/Loader';

// Landing
const LandingPage = lazy(() => import('@/pages/landing/LandingPage'));

// Auth
const LoginPage = lazy(() => import('@/pages/auth/LoginPage'));
const RegisterPage = lazy(() => import('@/pages/auth/RegisterPage'));
const ForgotPasswordPage = lazy(() => import('@/pages/auth/ForgotPasswordPage'));
const ResetPasswordPage = lazy(() => import('@/pages/auth/ResetPasswordPage'));
const VerifyEmailPage = lazy(() => import('@/pages/auth/VerifyEmailPage'));

// Dashboard
const DashboardPage = lazy(() => import('@/pages/dashboard/DashboardPage'));
const PredictPage = lazy(() => import('@/pages/dashboard/PredictPage'));
const HistoryPage = lazy(() => import('@/pages/dashboard/HistoryPage'));
const HistoryDetailPage = lazy(() => import('@/pages/dashboard/HistoryDetailPage'));
const ReportsPage = lazy(() => import('@/pages/dashboard/ReportsPage'));
const SavedCasesPage = lazy(() => import('@/pages/dashboard/SavedCasesPage'));
const FavoritesPage = lazy(() => import('@/pages/dashboard/FavoritesPage'));
const NotificationsPage = lazy(() => import('@/pages/dashboard/NotificationsPage'));
const ProfilePage = lazy(() => import('@/pages/dashboard/ProfilePage'));
const SettingsPage = lazy(() => import('@/pages/dashboard/SettingsPage'));
const ChangePasswordPage = lazy(() => import('@/pages/dashboard/ChangePasswordPage'));

// Researcher-only
const ComparisonPage = lazy(() => import('@/pages/dashboard/ComparisonPage'));
const BenchmarkPage = lazy(() => import('@/pages/dashboard/BenchmarkPage'));

// Admin-only
const AdminUsersPage = lazy(() => import('@/pages/admin/AdminUsersPage'));
const AdminModelsPage = lazy(() => import('@/pages/admin/AdminModelsPage'));
const AdminAnalyticsPage = lazy(() => import('@/pages/admin/AdminAnalyticsPage'));
const AdminAuditLogsPage = lazy(() => import('@/pages/admin/AdminAuditLogsPage'));
const AdminSystemHealthPage = lazy(() => import('@/pages/admin/AdminSystemHealthPage'));

// 404
const NotFoundPage = lazy(() => import('@/pages/NotFoundPage'));

export function AppRoutes() {
  return (
    <Suspense fallback={<PageLoader />}>
      <Routes>
        {/* Public landing */}
        <Route element={<LandingLayout />}>
          <Route path={ROUTES.LANDING} element={<LandingPage />} />
        </Route>

        {/* Auth pages — guests only */}
        <Route element={<PublicRoute />}>
          <Route element={<AuthLayout />}>
            <Route path={ROUTES.LOGIN} element={<LoginPage />} />
            <Route path={ROUTES.REGISTER} element={<RegisterPage />} />
            <Route path={ROUTES.FORGOT_PASSWORD} element={<ForgotPasswordPage />} />
            <Route path={ROUTES.RESET_PASSWORD} element={<ResetPasswordPage />} />
          </Route>
        </Route>

        {/* Email verification — accessible to anyone with a token */}
        <Route element={<AuthLayout />}>
          <Route path={ROUTES.VERIFY_EMAIL} element={<VerifyEmailPage />} />
        </Route>

        {/* Dashboard — authenticated users */}
        <Route element={<ProtectedRoute />}>
          <Route element={<DashboardLayout />}>
            {/* All authenticated roles */}
            <Route path={ROUTES.DASHBOARD} element={<DashboardPage />} />
            <Route path={ROUTES.PREDICT} element={<PredictPage />} />
            <Route path={ROUTES.HISTORY} element={<HistoryPage />} />
            <Route path={`${ROUTES.HISTORY}/:historyId`} element={<HistoryDetailPage />} />
            <Route path={ROUTES.REPORTS} element={<ReportsPage />} />
            <Route path={ROUTES.SAVED_CASES} element={<SavedCasesPage />} />
            <Route path={ROUTES.FAVORITES} element={<FavoritesPage />} />
            <Route path={ROUTES.NOTIFICATIONS} element={<NotificationsPage />} />
            <Route path={ROUTES.PROFILE} element={<ProfilePage />} />
            <Route path={ROUTES.SETTINGS} element={<SettingsPage />} />
            <Route path={ROUTES.CHANGE_PASSWORD} element={<ChangePasswordPage />} />

            {/* Comparison and Benchmark are demo-only pages (see
                DemoDataBanner within them) but open to any authenticated
                user — the backend has no restricted role to gate them
                behind. */}
            <Route path={ROUTES.COMPARISON} element={<ComparisonPage />} />
            <Route path={ROUTES.BENCHMARK} element={<BenchmarkPage />} />

            {/* Admin only */}
            <Route element={<AdminRoute />}>
              <Route path={ROUTES.ADMIN_USERS} element={<AdminUsersPage />} />
              <Route path={ROUTES.ADMIN_MODELS} element={<AdminModelsPage />} />
              <Route path={ROUTES.ADMIN_ANALYTICS} element={<AdminAnalyticsPage />} />
              <Route path={ROUTES.ADMIN_AUDIT_LOGS} element={<AdminAuditLogsPage />} />
              <Route path={ROUTES.ADMIN_SYSTEM_HEALTH} element={<AdminSystemHealthPage />} />
            </Route>
          </Route>
        </Route>

        {/* 404 */}
        <Route path={ROUTES.NOT_FOUND} element={<NotFoundPage />} />
      </Routes>
    </Suspense>
  );
}
