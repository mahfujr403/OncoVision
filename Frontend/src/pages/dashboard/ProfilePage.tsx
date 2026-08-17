import { useNavigate, Link } from 'react-router-dom';
import { User, Mail, Calendar, LogOut, Shield, KeyRound } from 'lucide-react';
import { SectionTitle } from '@/components/ui/SectionTitle';
import { Card, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Avatar } from '@/components/ui/Avatar';
import { useAuth } from '@/hooks/useAuth';
import { ROLE_LABELS } from '@/constants/roles';
import { ROUTES } from '@/constants/routes';
import { formatDate } from '@/utils/formatters';
import { getRefreshToken } from '@/api';
import { authService } from '@/features/auth/services/authService';

export default function ProfilePage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  if (!user) return null;

  const handleLogout = async () => {
    const refreshToken = getRefreshToken();
    if (refreshToken) {
      try {
        await authService.logout(refreshToken);
      } catch {
        // Best-effort
      }
    }
    logout();
    navigate(ROUTES.LOGIN, { replace: true });
  };

  const profileFields = [
    { icon: <User className="h-4 w-4" />, label: 'Full name', value: user.full_name },
    { icon: <Mail className="h-4 w-4" />, label: 'Email address', value: user.email },
    {
      icon: <Shield className="h-4 w-4" />,
      label: 'Role',
      value: ROLE_LABELS[user.role],
    },
    {
      icon: <Calendar className="h-4 w-4" />,
      label: 'Member since',
      value: formatDate(user.created_at),
    },
  ];

  return (
    <div className="space-y-5 max-w-xl">
      <SectionTitle
        title="Profile"
        description="Your account information"
      />

      {/* Identity card */}
      <Card>
        <CardContent>
          <div className="flex items-center gap-4 pb-5 border-b border-border">
            <div className="relative">
              <Avatar src={user.avatar_url ?? undefined} fallback={user.full_name} size="xl" />
              {user.is_active && (
                <div className="absolute -bottom-1 -right-1 h-4 w-4 rounded-full bg-emerald-400 ring-2 ring-card" />
              )}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-lg font-semibold truncate">{user.full_name}</p>
              <p className="text-sm text-muted-foreground truncate">{user.email}</p>
              <div className="flex items-center gap-2 mt-1.5">
                <Badge variant="default">{ROLE_LABELS[user.role]}</Badge>
                {user.is_verified && (
                  <Badge variant="success">Verified</Badge>
                )}
              </div>
            </div>
          </div>

          <div className="pt-4 space-y-3">
            {profileFields.map((f) => (
              <div key={f.label} className="flex items-center gap-3">
                <span className="shrink-0 text-muted-foreground">{f.icon}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider">
                    {f.label}
                  </p>
                  <p className="text-sm truncate">{f.value}</p>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Actions */}
      <div className="flex flex-col gap-2 sm:flex-row">
        <Button asChild variant="outline" size="sm">
          <Link to={ROUTES.CHANGE_PASSWORD}>
            <KeyRound className="mr-1.5 h-3.5 w-3.5" />
            Change password
          </Link>
        </Button>
        <Button asChild variant="outline" size="sm">
          <Link to={ROUTES.SETTINGS}>Settings</Link>
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleLogout}
          className="text-destructive hover:text-destructive hover:bg-destructive/10"
        >
          <LogOut className="mr-1.5 h-3.5 w-3.5" />
          Sign out
        </Button>
      </div>
    </div>
  );
}
