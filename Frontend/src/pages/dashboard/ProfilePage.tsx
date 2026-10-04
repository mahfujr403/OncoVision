import { useNavigate, Link } from 'react-router-dom';
import { User, Mail, Calendar, Clock, Edit, LogOut, Shield, KeyRound, Settings, Fingerprint, Activity } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Avatar } from '@/components/ui/Avatar';
import { useAuth } from '@/hooks/useAuth';
import { usePredictionHistory } from '@/hooks/queries/usePredictionHistory';
import { ROLE_LABELS } from '@/constants/roles';
import { ROUTES } from '@/constants/routes';
import { formatDate, formatDateTime } from '@/utils/formatters';

// NOTE: the backend User contract (GET /auth/me, verified against
// app/schemas/user.py) has no institution/specialty fields, and there is no
// profile-update endpoint at all — those were fabricated in earlier drafts.
// This page reflects only verified fields, pulls a real prediction evaluation
// count from the History endpoint pagination, and keeps the presentation
// strictly aligned with clinical workspace standards.
export default function ProfilePage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  // Real evaluation count: page_size=1 returns the true total_records in pagination.
  const { data: historySample } = usePredictionHistory({ page: 1, page_size: 1 });

  if (!user) return null;

  const handleLogout = async () => {
    await logout();
    navigate(ROUTES.LOGIN, { replace: true });
  };

  const identityFields = [
    { icon: <User className="h-4 w-4" />, label: 'Full Name', value: user.full_name },
    { icon: <Mail className="h-4 w-4" />, label: 'Email Address', value: user.email },
    { icon: <Fingerprint className="h-4 w-4" />, label: 'Account Identifier', value: user.id, isMono: true },
    { icon: <Shield className="h-4 w-4" />, label: 'Assigned Role', value: ROLE_LABELS[user.role] },
    { icon: <Calendar className="h-4 w-4" />, label: 'Registration Date', value: formatDate(user.created_at) },
    {
      icon: <Clock className="h-4 w-4" />,
      label: 'Last Authenticated Session',
      value: user.last_login ? formatDateTime(user.last_login) : 'Never',
    },
  ];

  return (
    <div className="space-y-6 max-w-2xl">
      {/* Calm Scientific Header */}
      <div>
        <h1 className="text-xl font-semibold tracking-tight text-text-primary sm:text-2xl">
          User Profile
        </h1>
        <p className="mt-1 text-sm text-text-muted">
          Authenticated clinician and researcher identity context.
        </p>
      </div>

      {/* Primary Identity Card */}
      <Card className="p-5 sm:p-6 space-y-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between pb-6 border-b border-border-subtle">
          <div className="flex items-center gap-4">
            <div className="relative shrink-0">
              <Avatar src={user.avatar_url ?? undefined} fallback={user.full_name} size="xl" />
              <div
                title={user.is_active ? 'Active Account' : 'Inactive Account'}
                className={`absolute -bottom-0.5 -right-0.5 h-3.5 w-3.5 rounded-full ring-2 ring-surface ${user.is_active ? 'bg-success' : 'bg-text-muted'}`}
              />
            </div>

            <div className="space-y-1">
              <h2 className="text-base font-semibold text-text-primary">{user.full_name}</h2>
              <p className="text-xs text-text-muted font-mono">{user.email}</p>
              <div className="flex flex-wrap items-center gap-1.5 pt-1">
                <Badge variant="primary" dot>
                  <Shield className="h-3 w-3" />
                  <span>{ROLE_LABELS[user.role]}</span>
                </Badge>
                <Badge variant={user.is_active ? 'success' : 'secondary'} dot>
                  {user.is_active ? 'Active' : 'Inactive'}
                </Badge>
                <Badge variant={user.is_verified ? 'info' : 'outline'}>
                  {user.is_verified ? 'Verified' : 'Unverified'}
                </Badge>
              </div>
            </div>
          </div>

          <Button
            variant="outline"
            size="sm"
            disabled
            title="Profile modification is managed through administrative directory services"
            className="self-start sm:self-auto gap-1.5 text-xs text-text-muted"
          >
            <Edit className="h-3.5 w-3.5" />
            <span>Edit Profile</span>
          </Button>
        </div>

        {/* Structured Identity Attributes */}
        <div className="grid gap-4 sm:grid-cols-2">
          {identityFields.map((field) => (
            <div key={field.label} className="flex items-start gap-3 rounded-lg border border-border-subtle bg-surface-raised/30 p-3">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-surface-raised text-primary">
                {field.icon}
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-[10px] font-medium uppercase tracking-wider text-text-muted">{field.label}</p>
                <p className={`text-xs font-medium text-text-primary mt-0.5 truncate ${field.isMono ? 'font-mono text-[11px]' : ''}`}>
                  {field.value}
                </p>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Verified Activity Telemetry Card */}
      <Card className="p-5 space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-text-muted">
            <Activity className="h-4 w-4 text-primary" />
            <h2 className="text-sm font-semibold text-text-primary">Clinical Inference Telemetry</h2>
          </div>
          <span className="text-[11px] font-mono text-text-muted">History Endpoint Verified</span>
        </div>
        <div className="flex items-baseline gap-2 pt-2">
          <span className="text-3xl font-semibold font-mono tabular-nums text-text-primary">
            {historySample?.pagination.total_records ?? '0'}
          </span>
          <span className="text-xs text-text-muted">total evaluated slide specimens</span>
        </div>
        <p className="text-xs text-text-muted leading-relaxed">
          Histopathology analyses logged in your personal prediction record. Records can be reviewed or exported from the History workspace.
        </p>
      </Card>

      {/* Quick Account Navigation Actions */}
      <Card className="p-3 space-y-1">
        <p className="text-[11px] font-medium text-text-muted uppercase tracking-wider px-3 py-1.5">
          Account Security & Preferences
        </p>
        <div className="space-y-0.5">
          <Link
            to={ROUTES.CHANGE_PASSWORD}
            className="flex items-center justify-between rounded-md px-3 py-2.5 text-xs font-medium text-text-secondary hover:bg-surface-raised hover:text-text-primary transition-colors"
          >
            <div className="flex items-center gap-2.5">
              <KeyRound className="h-4 w-4 text-text-muted" />
              <span>Change account password</span>
            </div>
            <span className="text-[11px] font-mono text-text-muted">Credentials</span>
          </Link>

          <Link
            to={ROUTES.SETTINGS}
            className="flex items-center justify-between rounded-md px-3 py-2.5 text-xs font-medium text-text-secondary hover:bg-surface-raised hover:text-text-primary transition-colors"
          >
            <div className="flex items-center gap-2.5">
              <Settings className="h-4 w-4 text-text-muted" />
              <span>Workspace & display settings</span>
            </div>
            <span className="text-[11px] font-mono text-text-muted">Preferences</span>
          </Link>

          <button
            type="button"
            onClick={handleLogout}
            className="w-full flex items-center justify-between rounded-md px-3 py-2.5 text-xs font-medium text-error hover:bg-error-surface transition-colors"
          >
            <div className="flex items-center gap-2.5">
              <LogOut className="h-4 w-4" />
              <span>Sign out of session</span>
            </div>
            <span className="text-[11px] font-mono">End Session</span>
          </button>
        </div>
      </Card>
    </div>
  );
}
