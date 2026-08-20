import { Fragment } from 'react';
import {
  LayoutDashboard,
  ScanLine,
  History,
  BarChart3,
  User,
  Settings,
  Users,
  ClipboardList,
  Server,
  Activity,
  ChevronLeft,
  ChevronRight,
  X,
  LogOut,
  Sun,
  Moon,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { User as UserType, PageId, Theme } from '@/types';
import { Avatar } from '@/components/ui/Avatar';
import { Badge } from '@/components/ui/Badge';

interface NavItem {
  id: PageId;
  label: string;
  icon: React.ReactNode;
}

const PRIMARY_NAV: NavItem[] = [
  { id: 'dashboard', label: 'Dashboard', icon: <LayoutDashboard className="w-4 h-4" /> },
  { id: 'predict', label: 'Predict', icon: <ScanLine className="w-4 h-4" /> },
  { id: 'history', label: 'History', icon: <History className="w-4 h-4" /> },
  { id: 'reports', label: 'Reports', icon: <BarChart3 className="w-4 h-4" /> },
];

const SECONDARY_NAV: NavItem[] = [
  { id: 'profile', label: 'Profile', icon: <User className="w-4 h-4" /> },
  { id: 'settings', label: 'Settings', icon: <Settings className="w-4 h-4" /> },
];

const ADMIN_NAV: NavItem[] = [
  { id: 'admin-users', label: 'Users', icon: <Users className="w-4 h-4" /> },
  { id: 'admin-history', label: 'All History', icon: <ClipboardList className="w-4 h-4" /> },
  { id: 'admin-system', label: 'System', icon: <Server className="w-4 h-4" /> },
  { id: 'admin-monitoring', label: 'Monitoring', icon: <Activity className="w-4 h-4" /> },
];

interface SidebarProps {
  user: UserType;
  activePage: PageId;
  onNavigate: (page: PageId) => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
  mobileOpen: boolean;
  onCloseMobile: () => void;
  onLogout: () => void;
  theme: Theme;
  onToggleTheme: () => void;
}

function NavItemButton({
  item,
  active,
  collapsed,
  onClick,
}: {
  item: NavItem;
  active: boolean;
  collapsed: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      title={collapsed ? item.label : undefined}
      className={cn(
        'w-full flex items-center gap-3 px-3 h-9 rounded text-sm font-medium transition-all duration-150 cursor-pointer',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        active
          ? 'bg-primary/10 text-primary'
          : 'text-sidebar-foreground/60 hover:bg-muted/50 hover:text-sidebar-foreground',
        collapsed && 'justify-center px-0'
      )}
    >
      <span className="shrink-0">{item.icon}</span>
      {!collapsed && <span className="truncate">{item.label}</span>}
    </button>
  );
}

function SidebarContent({
  user,
  activePage,
  onNavigate,
  collapsed,
  onToggleCollapse,
  onLogout,
  theme,
  onToggleTheme,
  onCloseMobile,
  isMobileDrawer,
}: SidebarProps & { isMobileDrawer?: boolean }) {
  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div
        className={cn(
          'flex items-center h-14 px-4 border-b border-border shrink-0',
          collapsed && !isMobileDrawer ? 'justify-center px-0' : 'justify-between'
        )}
      >
        {(!collapsed || isMobileDrawer) && (
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-7 h-7 rounded-md bg-primary flex items-center justify-center shrink-0">
              <svg className="w-4 h-4 text-primary-foreground" viewBox="0 0 16 16" fill="none">
                <circle cx="8" cy="8" r="5.5" stroke="currentColor" strokeWidth="1.5" />
                <circle cx="8" cy="8" r="2" fill="currentColor" />
                <line x1="8" y1="1" x2="8" y2="3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                <line x1="8" y1="13" x2="8" y2="15" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                <line x1="1" y1="8" x2="3" y2="8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                <line x1="13" y1="8" x2="15" y2="8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
              </svg>
            </div>
            <div className="min-w-0">
              <p className="text-sm font-semibold text-sidebar-foreground leading-tight truncate">
                OncoVision AI
              </p>
            </div>
          </div>
        )}

        {collapsed && !isMobileDrawer && (
          <div className="w-7 h-7 rounded-md bg-primary flex items-center justify-center">
            <svg className="w-4 h-4 text-primary-foreground" viewBox="0 0 16 16" fill="none">
              <circle cx="8" cy="8" r="5.5" stroke="currentColor" strokeWidth="1.5" />
              <circle cx="8" cy="8" r="2" fill="currentColor" />
              <line x1="8" y1="1" x2="8" y2="3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
              <line x1="8" y1="13" x2="8" y2="15" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
              <line x1="1" y1="8" x2="3" y2="8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
              <line x1="13" y1="8" x2="15" y2="8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          </div>
        )}

        {isMobileDrawer ? (
          <button
            onClick={onCloseMobile}
            className="text-muted-foreground hover:text-foreground transition-colors ml-2"
          >
            <X className="w-4 h-4" />
          </button>
        ) : (
          <button
            onClick={onToggleCollapse}
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            className={cn(
              'text-muted-foreground hover:text-foreground transition-colors',
              collapsed && 'hidden'
            )}
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-4 px-2 space-y-5">
        {/* Primary */}
        <div className="space-y-0.5">
          {!collapsed && (
            <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-widest px-3 mb-2">
              Navigation
            </p>
          )}
          {PRIMARY_NAV.map((item) => (
            <NavItemButton
              key={item.id}
              item={item}
              active={activePage === item.id}
              collapsed={collapsed && !isMobileDrawer}
              onClick={() => { onNavigate(item.id); if (isMobileDrawer) onCloseMobile(); }}
            />
          ))}
        </div>

        {/* Secondary */}
        <div className="space-y-0.5">
          {!collapsed && (
            <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-widest px-3 mb-2">
              Account
            </p>
          )}
          {SECONDARY_NAV.map((item) => (
            <NavItemButton
              key={item.id}
              item={item}
              active={activePage === item.id}
              collapsed={collapsed && !isMobileDrawer}
              onClick={() => { onNavigate(item.id); if (isMobileDrawer) onCloseMobile(); }}
            />
          ))}
        </div>

        {/* Admin */}
        {user.role === 'admin' && (
          <div className="space-y-0.5">
            {!collapsed && (
              <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-widest px-3 mb-2">
                Admin
              </p>
            )}
            {collapsed && !isMobileDrawer && (
              <div className="mx-auto w-8 h-px bg-border my-2" />
            )}
            {ADMIN_NAV.map((item) => (
              <NavItemButton
                key={item.id}
                item={item}
                active={activePage === item.id}
                collapsed={collapsed && !isMobileDrawer}
                onClick={() => { onNavigate(item.id); if (isMobileDrawer) onCloseMobile(); }}
              />
            ))}
          </div>
        )}
      </nav>

      {/* Footer */}
      <div className="border-t border-border p-2 space-y-1 shrink-0">
        {/* Theme toggle */}
        <button
          onClick={onToggleTheme}
          title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          className={cn(
            'w-full flex items-center gap-3 px-3 h-9 rounded text-sm font-medium transition-colors',
            'text-muted-foreground hover:text-foreground hover:bg-muted/50 cursor-pointer',
            (collapsed && !isMobileDrawer) && 'justify-center px-0'
          )}
        >
          {theme === 'dark' ? <Sun className="w-4 h-4 shrink-0" /> : <Moon className="w-4 h-4 shrink-0" />}
          {(!collapsed || isMobileDrawer) && (
            <span>{theme === 'dark' ? 'Light mode' : 'Dark mode'}</span>
          )}
        </button>

        {/* Logout */}
        <button
          onClick={onLogout}
          title="Sign out"
          className={cn(
            'w-full flex items-center gap-3 px-3 h-9 rounded text-sm font-medium transition-colors',
            'text-muted-foreground hover:text-destructive hover:bg-destructive/5 cursor-pointer',
            (collapsed && !isMobileDrawer) && 'justify-center px-0'
          )}
        >
          <LogOut className="w-4 h-4 shrink-0" />
          {(!collapsed || isMobileDrawer) && <span>Sign out</span>}
        </button>

        {/* User info */}
        {(!collapsed || isMobileDrawer) && (
          <div className="flex items-center gap-2.5 px-3 py-2 mt-1">
            <Avatar name={user.name} size="sm" />
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-foreground truncate">{user.name}</p>
              <p className="text-[11px] text-muted-foreground truncate font-mono">{user.email}</p>
            </div>
            <Badge variant={user.role === 'admin' ? 'admin' : 'user'}>
              {user.role}
            </Badge>
          </div>
        )}

        {/* Collapsed avatar */}
        {collapsed && !isMobileDrawer && (
          <div className="flex justify-center py-1">
            <Avatar name={user.name} size="sm" />
          </div>
        )}
      </div>
    </div>
  );
}

export function Sidebar(props: SidebarProps) {
  const { collapsed, mobileOpen, onCloseMobile } = props;

  return (
    <Fragment>
      {/* Desktop sidebar */}
      <aside
        className={cn(
          'hidden md:flex flex-col fixed inset-y-0 left-0 z-30',
          'bg-sidebar border-r border-border',
          'transition-[width] duration-200 ease-out',
          collapsed ? 'w-16' : 'w-[220px]'
        )}
      >
        <SidebarContent {...props} />

        {/* Expand handle when collapsed */}
        {collapsed && (
          <button
            onClick={props.onToggleCollapse}
            title="Expand sidebar"
            className="absolute -right-3 top-[72px] w-6 h-6 rounded-full bg-card border border-border flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-muted transition-colors shadow-sm z-10"
          >
            <ChevronRight className="w-3 h-3" />
          </button>
        )}
      </aside>

      {/* Mobile backdrop */}
      {mobileOpen && (
        <div
          className="md:hidden fixed inset-0 z-40 bg-background/70 backdrop-blur-sm"
          onClick={onCloseMobile}
        />
      )}

      {/* Mobile drawer */}
      <aside
        className={cn(
          'md:hidden fixed inset-y-0 left-0 z-50 w-[220px]',
          'bg-sidebar border-r border-border',
          'transition-transform duration-200 ease-out',
          mobileOpen ? 'translate-x-0 slide-in-left' : '-translate-x-full'
        )}
      >
        <SidebarContent {...props} isMobileDrawer />
      </aside>
    </Fragment>
  );
}

export default Sidebar;
