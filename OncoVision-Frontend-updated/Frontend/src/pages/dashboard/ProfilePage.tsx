import { useNavigate, Link } from 'react-router-dom';
import { User, Mail, Calendar, Clock, Edit, LogOut, Shield, KeyRound } from 'lucide-react';
import { SectionTitle } from '@/components/ui/SectionTitle';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
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
// profile-update endpoint at all — those were fabricated in the previous
// version of this page, along with an "Activity Summary" of made-up
// prediction/report/saved-case counts. This version shows only real fields,
// pulls a real prediction count from the History endpoint, and disables
// editing with an explanation rather than pretending it saves anywhere.
export default function ProfilePage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  // Cheap real count: page_size=1 still returns the true total in pagination.
  const { data: historySample } = usePredictionHistory({ page: 1, page_size: 1 });

  if (!user) return null;

  const handleLogout = async () => {
    await logout();
    navigate(ROUTES.LOGIN, { replace: true });
  };

  const profileFields = [
    { icon: <User className="h-4 w-4" />, label: 'Full name', value: user.full_name },
    { icon: <Mail className="h-4 w-4" />, label: 'Email address', value: user.email },
    { icon: <Calendar className="h-4 w-4" />, label: 'Member since', value: formatDate(user.created_at) },
    {
      icon: <Clock className="h-4 w-4" />,
      label: 'Last login',
      value: user.last_login ? formatDateTime(user.last_login) : 'Never',
    },
  ];

  return (
    <div className="space-y-5 max-w-xl">
      <SectionTitle title="Profile" description="Your account information" />

      {/* Identity card */}
      <Card>
        <div className="flex items-center gap-4 pb-5 border-b border-border">
          <div className="relative">
            <Avatar src={user.avatar_url ?? undefined} fallback={user.full_name} size="xl" />
            <div
              className={`absolute -bottom-1 -right-1 h-4 w-4 rounded-full ring-2 ring-card ${user.is_active ? 'bg-emerald-400' : 'bg-muted-foreground'}`}
            />
          </div>
          <div className="flex-1">
            <h2 className="text-base font-semibold">{user.full_name}</h2>
            <p className="text-xs text-muted-foreground">{user.email}</p>
            <div className="flex items-center gap-2 mt-2">
              <Badge variant="default">
                <Shield className="h-3 w-3" />
                {ROLE_LABELS[user.role]}
              </Badge>
              <Badge variant={user.is_active ? 'success' : 'destructive'} dot>
                {user.is_active ? 'Active' : 'Inactive'}
              </Badge>
              <Badge variant={user.is_verified ? 'info' : 'outline'}>
                {user.is_verified ? 'Verified' : 'Unverified'}
              </Badge>
            </div>
          </div>
          <Button variant="outline" size="sm" disabled title="No profile-update endpoint exists yet">
            <Edit className="h-3.5 w-3.5" />
            Edit
          </Button>
        </div>

        <div className="pt-5 space-y-4">
          {profileFields.map((f) => (
            <div key={f.label} className="flex items-center gap-3">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
                {f.icon}
              </div>
              <div>
                <p className="text-[10px] text-muted-foreground uppercase tracking-wider">{f.label}</p>
                <p className="text-sm font-medium">{f.value}</p>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Real activity: total prediction count from history pagination */}
      <Card>
        <CardHeader>
          <CardTitle>Activity</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center">
            <p className="text-2xl font-bold font-mono text-primary">
              {historySample?.pagination.total_records ?? '—'}
            </p>
            <p className="text-[10px] text-muted-foreground mt-0.5">Total predictions</p>
          </div>
        </CardContent>
      </Card>

      {/* Actions */}
      <Card className="space-y-2" padding="sm">
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider px-2">Account Actions</p>
        <div className="space-y-0.5">
          <Link
            to={ROUTES.CHANGE_PASSWORD}
            className="flex items-center gap-2.5 rounded-md px-3 py-2.5 text-sm hover:bg-secondary transition-colors group"
          >
            <KeyRound className="h-4 w-4 text-muted-foreground group-hover:text-foreground" />
            Change password
          </Link>
          <Link
            to={ROUTES.SETTINGS}
            className="flex items-center gap-2.5 rounded-md px-3 py-2.5 text-sm hover:bg-secondary transition-colors group"
          >
            <User className="h-4 w-4 text-muted-foreground group-hover:text-foreground" />
            Account settings
          </Link>
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-2.5 rounded-md px-3 py-2.5 text-sm text-destructive hover:bg-destructive/10 transition-colors"
          >
            <LogOut className="h-4 w-4" />
            Sign out
          </button>
        </div>
      </Card>
    </div>
  );
}
