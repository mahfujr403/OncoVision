import { Link, useLocation } from 'react-router-dom';
import { ChevronRight, Home } from 'lucide-react';

const ROUTE_LABELS: Record<string, string> = {
  dashboard: 'Dashboard',
  predict: 'Predict',
  history: 'History',
  comparison: 'Comparison',
  benchmark: 'Benchmark',
  reports: 'Reports',
  'saved-cases': 'Saved Cases',
  favorites: 'Favorites',
  notifications: 'Notifications',
  profile: 'Profile',
  settings: 'Settings',
  admin: 'Admin',
  users: 'User Management',
  models: 'Model Management',
  analytics: 'Analytics',
  'audit-logs': 'Audit Logs',
  'system-health': 'System Health',
  'change-password': 'Change Password',
  'reset-password': 'Reset Password',
  'verify-email': 'Verify Email',
};

export function Breadcrumb() {
  const { pathname } = useLocation();
  const segments = pathname.split('/').filter(Boolean);

  return (
    <nav className="flex items-center gap-1 text-xs text-muted-foreground">
      <Link to="/" className="hover:text-foreground transition-colors">
        <Home className="h-3.5 w-3.5" />
      </Link>
      {segments.map((seg, i) => {
        const path = '/' + segments.slice(0, i + 1).join('/');
        const label = ROUTE_LABELS[seg] ?? seg;
        const isLast = i === segments.length - 1;

        return (
          <span key={path} className="flex items-center gap-1">
            <ChevronRight className="h-3 w-3 text-muted-foreground/50" />
            {isLast ? (
              <span className="text-foreground font-medium">{label}</span>
            ) : (
              <Link to={path} className="hover:text-foreground transition-colors">
                {label}
              </Link>
            )}
          </span>
        );
      })}
    </nav>
  );
}
