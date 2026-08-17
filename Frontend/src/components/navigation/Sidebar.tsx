import { NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard, Microscope, History,
  FileText, Bookmark, Heart, Bell, User, Settings,
  Users, Cpu, Activity, ScrollText, ChevronRight,
  Stethoscope, ChevronLeft, Zap, KeyRound,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuth } from '@/hooks/useAuth';
import { ROUTES } from '@/constants/routes';
import { isAdmin } from '@/utils/permissions';
import { Avatar } from '@/components/ui/Avatar';
import { APP_NAME } from '@/constants/app';
import { ROLE_LABELS } from '@/constants/roles';

interface NavItem {
  label: string;
  icon: React.ReactNode;
  to: string;
}

interface NavGroup {
  label: string;
  items: NavItem[];
}

function buildNavGroups(role: ReturnType<typeof useAuth>['role']): NavGroup[] {
  const groups: NavGroup[] = [
    {
      label: 'Core',
      items: [
        { label: 'Dashboard', icon: <LayoutDashboard className="h-4 w-4" />, to: ROUTES.DASHBOARD },
        { label: 'Predict', icon: <Microscope className="h-4 w-4" />, to: ROUTES.PREDICT },
        { label: 'History', icon: <History className="h-4 w-4" />, to: ROUTES.HISTORY },
      ],
    },
  ];

  // All authenticated users see Reports; Comparison/Benchmark are placeholder pages
  const analysisItems: NavItem[] = [
    { label: 'Reports', icon: <FileText className="h-4 w-4" />, to: ROUTES.REPORTS },
  ];
  if (analysisItems.length > 0) {
    groups.push({ label: 'Analysis', items: analysisItems });
  }

  groups.push({
    label: 'Library',
    items: [
      { label: 'Saved Cases', icon: <Bookmark className="h-4 w-4" />, to: ROUTES.SAVED_CASES },
      { label: 'Favorites', icon: <Heart className="h-4 w-4" />, to: ROUTES.FAVORITES },
    ],
  });

  groups.push({
    label: 'Account',
    items: [
      { label: 'Notifications', icon: <Bell className="h-4 w-4" />, to: ROUTES.NOTIFICATIONS },
      { label: 'Profile', icon: <User className="h-4 w-4" />, to: ROUTES.PROFILE },
      { label: 'Settings', icon: <Settings className="h-4 w-4" />, to: ROUTES.SETTINGS },
      { label: 'Change Password', icon: <KeyRound className="h-4 w-4" />, to: ROUTES.CHANGE_PASSWORD },
    ],
  });

  if (isAdmin(role ?? undefined)) {
    groups.push({
      label: 'Administration',
      items: [
        { label: 'User Management', icon: <Users className="h-4 w-4" />, to: ROUTES.ADMIN_USERS },
        { label: 'Model Management', icon: <Cpu className="h-4 w-4" />, to: ROUTES.ADMIN_MODELS },
        { label: 'Analytics', icon: <Activity className="h-4 w-4" />, to: ROUTES.ADMIN_ANALYTICS },
        { label: 'Audit Logs', icon: <ScrollText className="h-4 w-4" />, to: ROUTES.ADMIN_AUDIT_LOGS },
        { label: 'System Health', icon: <Zap className="h-4 w-4" />, to: ROUTES.ADMIN_SYSTEM_HEALTH },
      ],
    });
  }

  return groups;
}

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
  mobile?: boolean;
  onClose?: () => void;
}

export function Sidebar({ collapsed, onToggle, mobile, onClose }: SidebarProps) {
  const { user, role } = useAuth();
  const location = useLocation();
  const groups = buildNavGroups(role);

  return (
    <aside
      className={cn(
        'flex flex-col h-full bg-card border-r border-border transition-all duration-300 ease-in-out',
        collapsed ? 'w-14' : 'w-56',
        mobile && 'w-56',
      )}
    >
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-3 h-14 border-b border-border shrink-0">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary">
          <Stethoscope className="h-4 w-4 text-primary-foreground" />
        </div>
        {(!collapsed || mobile) && (
          <div className="overflow-hidden flex-1">
            <p className="text-sm font-semibold leading-none tracking-tight font-display">{APP_NAME}</p>
            <p className="text-[10px] text-muted-foreground mt-0.5 truncate">Pathology AI Platform</p>
          </div>
        )}
        {!mobile && (
          <button
            onClick={onToggle}
            className={cn(
              'shrink-0 flex h-5 w-5 items-center justify-center rounded text-muted-foreground hover:text-foreground transition-colors',
              collapsed && 'ml-0',
            )}
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? <ChevronRight className="h-3.5 w-3.5" /> : <ChevronLeft className="h-3.5 w-3.5" />}
          </button>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-4" aria-label="Main navigation">
        {groups.map((group) => (
          <NavGroup
            key={group.label}
            group={group}
            collapsed={collapsed && !mobile}
            currentPath={location.pathname}
            onItemClick={onClose}
          />
        ))}
      </nav>

      {/* User footer */}
      <div className="border-t border-border p-2 shrink-0">
        <div className={cn('flex items-center gap-2.5 rounded-md px-2 py-2 hover:bg-secondary transition-colors')}>
          <Avatar src={user?.avatar_url ?? undefined} fallback={user?.full_name} size="sm" />
          {(!collapsed || mobile) && user && (
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium truncate">{user.full_name}</p>
              <p className="text-[10px] text-muted-foreground truncate">
                {ROLE_LABELS[user.role]}
              </p>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}

function NavGroup({
  group,
  collapsed,
  currentPath,
  onItemClick,
}: {
  group: NavGroup;
  collapsed: boolean;
  currentPath: string;
  onItemClick?: () => void;
}) {
  return (
    <div>
      {!collapsed && (
        <p className="px-2 mb-1 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/60">
          {group.label}
        </p>
      )}
      <ul className="space-y-0.5">
        {group.items.map((item) => (
          <SidebarItem
            key={item.to}
            item={item}
            collapsed={collapsed}
            active={
              currentPath === item.to ||
              (item.to !== ROUTES.DASHBOARD && currentPath.startsWith(item.to))
            }
            onClick={onItemClick}
          />
        ))}
      </ul>
    </div>
  );
}

function SidebarItem({
  item,
  collapsed,
  active,
  onClick,
}: {
  item: NavItem;
  collapsed: boolean;
  active: boolean;
  onClick?: () => void;
}) {
  return (
    <li>
      <NavLink
        to={item.to}
        onClick={onClick}
        className={cn(
          'flex items-center gap-2.5 rounded-md px-2 py-1.5 text-sm transition-colors',
          active
            ? 'bg-primary/10 text-primary font-medium'
            : 'text-muted-foreground hover:bg-secondary hover:text-foreground',
          collapsed && 'justify-center px-0',
        )}
        title={collapsed ? item.label : undefined}
        aria-current={active ? 'page' : undefined}
      >
        <span className={cn('shrink-0', active && 'text-primary')}>{item.icon}</span>
        {!collapsed && <span className="flex-1 truncate">{item.label}</span>}
        {!collapsed && active && <ChevronRight className="h-3 w-3 text-primary shrink-0" />}
      </NavLink>
    </li>
  );
}
