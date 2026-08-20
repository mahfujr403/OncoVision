import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Bell, Sun, Moon, Search, Menu, LogOut, User, Settings, ChevronDown, KeyRound,
} from 'lucide-react';
import * as DropdownMenu from '@radix-ui/react-dropdown-menu';
import { cn } from '@/lib/utils';
import { useAuth } from '@/hooks/useAuth';
import { useTheme } from '@/hooks/useTheme';
import { Avatar } from '@/components/ui/Avatar';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { ROUTES } from '@/constants/routes';
import { ROLE_LABELS } from '@/constants/roles';

interface NavbarProps {
  onMenuClick?: () => void;
}

export function Navbar({ onMenuClick }: NavbarProps) {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const [searchOpen, setSearchOpen] = useState(false);

  const handleLogout = async () => {
    // AuthContext's logout() already calls authService.logout() and clears
    // state — calling authService.logout() again here would just be a
    // redundant, wasted request.
    await logout();
    navigate(ROUTES.LOGIN, { replace: true });
  };

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-border bg-card/80 backdrop-blur-md px-4">
      {/* Mobile menu */}
      <Button
        variant="ghost"
        size="icon-sm"
        className="md:hidden"
        onClick={onMenuClick}
        aria-label="Open navigation menu"
      >
        <Menu className="h-4 w-4" />
      </Button>

      {/* Desktop search */}
      <div className={cn('flex-1 max-w-xs', !searchOpen && 'hidden md:block')}>
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
          <input
            type="search"
            placeholder="Search cases, models..."
            aria-label="Search"
            className={cn(
              'h-8 w-full rounded-md border border-border bg-secondary pl-8 pr-3 text-sm',
              'placeholder:text-muted-foreground/50',
              'focus:outline-none focus:ring-1 focus:ring-ring',
            )}
          />
        </div>
      </div>

      {/* Mobile search toggle */}
      <div className="flex-1 md:hidden">
        <button
          onClick={() => setSearchOpen((v) => !v)}
          className="text-muted-foreground hover:text-foreground"
          aria-label="Toggle search"
        >
          <Search className="h-4 w-4" />
        </button>
      </div>

      <div className="ml-auto flex items-center gap-1">
        {/* Theme toggle */}
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={toggleTheme}
          aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
        >
          {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </Button>

        {/* Notifications */}
        <Button variant="ghost" size="icon-sm" asChild aria-label="View notifications">
          <Link to={ROUTES.NOTIFICATIONS}>
            <div className="relative">
              <Bell className="h-4 w-4" />
              <span className="absolute -top-1 -right-1 h-2 w-2 rounded-full bg-destructive" aria-hidden />
            </div>
          </Link>
        </Button>

        {/* Profile dropdown */}
        <DropdownMenu.Root>
          <DropdownMenu.Trigger asChild>
            <button
              className="flex items-center gap-2 rounded-md px-2 py-1 hover:bg-secondary transition-colors focus:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              aria-label="Open user menu"
            >
              <Avatar src={user?.avatar_url ?? undefined} fallback={user?.full_name} size="sm" />
              <div className="hidden md:block text-left">
                <p className="text-xs font-medium leading-none">{user?.full_name}</p>
                <p className="text-[10px] text-muted-foreground mt-0.5">
                  {user?.role ? ROLE_LABELS[user.role] : ''}
                </p>
              </div>
              <ChevronDown className="h-3 w-3 text-muted-foreground hidden md:block" />
            </button>
          </DropdownMenu.Trigger>

          <DropdownMenu.Portal>
            <DropdownMenu.Content
              align="end"
              sideOffset={6}
              className={cn(
                'z-50 min-w-52 rounded-lg border border-border bg-card p-1 shadow-xl shadow-black/30',
                'data-[state=open]:animate-in data-[state=closed]:animate-out',
                'data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0',
                'data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95',
              )}
            >
              {/* User info */}
              <div className="px-2 py-2 border-b border-border mb-1">
                <p className="text-xs font-medium">{user?.full_name}</p>
                <p className="text-[10px] text-muted-foreground">{user?.email}</p>
                {user?.role && (
                  <Badge variant="default" className="mt-1.5 text-[10px]">
                    {ROLE_LABELS[user.role]}
                  </Badge>
                )}
              </div>

              <DropdownItem
                icon={<User className="h-3.5 w-3.5" />}
                label="Profile"
                onClick={() => navigate(ROUTES.PROFILE)}
              />
              <DropdownItem
                icon={<Settings className="h-3.5 w-3.5" />}
                label="Settings"
                onClick={() => navigate(ROUTES.SETTINGS)}
              />
              <DropdownItem
                icon={<KeyRound className="h-3.5 w-3.5" />}
                label="Change password"
                onClick={() => navigate(ROUTES.CHANGE_PASSWORD)}
              />

              {/* Theme toggle inline */}
              <div className="flex items-center justify-between px-2 py-1.5 text-xs text-muted-foreground">
                <span className="flex items-center gap-2">
                  {theme === 'dark' ? <Moon className="h-3.5 w-3.5" /> : <Sun className="h-3.5 w-3.5" />}
                  {theme === 'dark' ? 'Dark mode' : 'Light mode'}
                </span>
                <button
                  onClick={toggleTheme}
                  className="h-5 w-9 rounded-full bg-secondary border border-border relative transition-colors hover:border-primary"
                  aria-label="Toggle theme"
                >
                  <span
                    className={cn(
                      'absolute top-0.5 h-4 w-4 rounded-full bg-primary transition-transform',
                      theme === 'dark' ? 'translate-x-0.5' : 'translate-x-4',
                    )}
                  />
                </button>
              </div>

              <DropdownMenu.Separator className="my-1 h-px bg-border" />

              <DropdownItem
                icon={<LogOut className="h-3.5 w-3.5" />}
                label="Sign out"
                onClick={handleLogout}
                destructive
              />
            </DropdownMenu.Content>
          </DropdownMenu.Portal>
        </DropdownMenu.Root>
      </div>
    </header>
  );
}

function DropdownItem({
  icon,
  label,
  onClick,
  destructive = false,
}: {
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
  destructive?: boolean;
}) {
  return (
    <DropdownMenu.Item
      onClick={onClick}
      className={cn(
        'flex items-center gap-2 rounded-md px-2 py-1.5 text-xs cursor-pointer select-none outline-none',
        'transition-colors',
        destructive
          ? 'text-destructive hover:bg-destructive/10'
          : 'text-foreground hover:bg-secondary',
      )}
    >
      {icon}
      {label}
    </DropdownMenu.Item>
  );
}
