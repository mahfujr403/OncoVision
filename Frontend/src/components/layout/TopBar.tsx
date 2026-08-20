import { useState, useRef, useEffect } from 'react';
import {
  Menu,
  ChevronRight,
  WifiOff,
  Bell,
  User,
  Settings,
  LogOut,
  Sun,
  Moon,
  ChevronDown,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { User as UserType, PageId, Theme } from '@/types';
import { Avatar } from '@/components/ui/Avatar';
import { Badge } from '@/components/ui/Badge';

const PAGE_LABELS: Record<PageId, string> = {
  dashboard: 'Dashboard',
  predict: 'Predict',
  history: 'History',
  reports: 'Reports',
  profile: 'Profile',
  settings: 'Settings',
  'admin-users': 'Users',
  'admin-history': 'Prediction History',
  'admin-system': 'System',
  'admin-monitoring': 'Monitoring',
};

interface TopBarProps {
  user: UserType;
  activePage: PageId;
  onOpenMobileSidebar: () => void;
  onLogout: () => void;
  onNavigate: (page: PageId) => void;
  theme: Theme;
  onToggleTheme: () => void;
}

export function TopBar({
  user,
  activePage,
  onOpenMobileSidebar,
  onLogout,
  onNavigate,
  theme,
  onToggleTheme,
}: TopBarProps) {
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setUserMenuOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const isAdmin = activePage.startsWith('admin-');
  const pageLabel = PAGE_LABELS[activePage];

  return (
    <header className="h-14 border-b border-border bg-card flex items-center px-4 gap-4 shrink-0 z-20">
      {/* Mobile hamburger */}
      <button
        onClick={onOpenMobileSidebar}
        className="md:hidden text-muted-foreground hover:text-foreground transition-colors"
      >
        <Menu className="w-5 h-5" />
      </button>

      {/* Breadcrumb */}
      <div className="flex items-center gap-1.5 text-sm min-w-0 flex-1">
        <span className="text-muted-foreground hidden sm:block font-medium">OncoVision AI</span>
        <ChevronRight className="w-3.5 h-3.5 text-border hidden sm:block shrink-0" />
        {isAdmin && (
          <>
            <span className="text-muted-foreground hidden sm:block">Admin</span>
            <ChevronRight className="w-3.5 h-3.5 text-border hidden sm:block shrink-0" />
          </>
        )}
        <span className="font-semibold text-foreground truncate">{pageLabel}</span>
      </div>

      {/* Right side */}
      <div className="flex items-center gap-2 shrink-0">
        {/* AI Runtime status */}
        <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-border bg-muted/40">
          <WifiOff className="w-3 h-3 text-muted-foreground" />
          <span className="text-xs text-muted-foreground font-mono whitespace-nowrap">
            AI Runtime: Offline
          </span>
        </div>

        {/* Theme toggle */}
        <button
          onClick={onToggleTheme}
          title={theme === 'dark' ? 'Light mode' : 'Dark mode'}
          className="w-8 h-8 flex items-center justify-center rounded text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
        >
          {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </button>

        {/* Notifications */}
        <button
          title="Notifications"
          className="w-8 h-8 flex items-center justify-center rounded text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
        >
          <Bell className="w-4 h-4" />
        </button>

        {/* User menu */}
        <div className="relative" ref={menuRef}>
          <button
            onClick={() => setUserMenuOpen((v) => !v)}
            className={cn(
              'flex items-center gap-2 h-8 pl-2 pr-2 rounded transition-colors',
              'hover:bg-muted',
              userMenuOpen && 'bg-muted'
            )}
          >
            <Avatar name={user.name} size="xs" />
            <div className="hidden sm:flex flex-col items-start leading-tight">
              <span className="text-xs font-semibold text-foreground leading-none">
                {user.name.split(' ')[0]}
              </span>
            </div>
            <Badge variant={user.role === 'admin' ? 'admin' : 'user'} className="hidden sm:inline-flex">
              {user.role}
            </Badge>
            <ChevronDown className="w-3 h-3 text-muted-foreground hidden sm:block" />
          </button>

          {userMenuOpen && (
            <div className="absolute right-0 top-full mt-1.5 w-52 rounded-lg border border-border bg-card shadow-lg z-50 py-1 fade-up">
              <div className="px-3 py-2.5 border-b border-border">
                <p className="text-xs font-semibold text-foreground">{user.name}</p>
                <p className="text-[11px] text-muted-foreground font-mono truncate mt-0.5">
                  {user.email}
                </p>
              </div>

              <div className="py-1">
                <MenuButton
                  icon={<User className="w-3.5 h-3.5" />}
                  label="Profile"
                  onClick={() => { onNavigate('profile'); setUserMenuOpen(false); }}
                />
                <MenuButton
                  icon={<Settings className="w-3.5 h-3.5" />}
                  label="Settings"
                  onClick={() => { onNavigate('settings'); setUserMenuOpen(false); }}
                />
                <MenuButton
                  icon={theme === 'dark' ? <Sun className="w-3.5 h-3.5" /> : <Moon className="w-3.5 h-3.5" />}
                  label={theme === 'dark' ? 'Light mode' : 'Dark mode'}
                  onClick={() => { onToggleTheme(); setUserMenuOpen(false); }}
                />
              </div>

              <div className="border-t border-border py-1">
                <MenuButton
                  icon={<LogOut className="w-3.5 h-3.5" />}
                  label="Sign out"
                  onClick={() => { onLogout(); setUserMenuOpen(false); }}
                  destructive
                />
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}

function MenuButton({
  icon,
  label,
  onClick,
  destructive,
}: {
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
  destructive?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'w-full flex items-center gap-2.5 px-3 py-1.5 text-sm transition-colors cursor-pointer',
        destructive
          ? 'text-destructive hover:bg-destructive/5'
          : 'text-foreground hover:bg-muted'
      )}
    >
      <span className="shrink-0 opacity-70">{icon}</span>
      {label}
    </button>
  );
}

export default TopBar;
