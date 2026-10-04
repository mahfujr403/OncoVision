import { useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import {
  Bell,
  Sun,
  Moon,
  Search,
  Menu,
  LogOut,
  User,
  Settings,
  ChevronDown,
  KeyRound,
  X,
} from "lucide-react"
import * as DropdownMenu from "@radix-ui/react-dropdown-menu"
import { cn } from "@/lib/utils"
import { useAuth } from "@/hooks/useAuth"
import { useTheme } from "@/hooks/useTheme"
import { Avatar } from "@/components/ui/Avatar"
import { Button } from "@/components/ui/Button"
import { Badge } from "@/components/ui/Badge"
import { ROUTES } from "@/constants/routes"
import { ROLE_LABELS } from "@/constants/roles"

interface NavbarProps {
  onMenuClick?: () => void
}

export function Navbar({ onMenuClick }: NavbarProps) {
  const { user, logout } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const navigate = useNavigate()
  const [searchOpen, setSearchOpen] = useState(false)

  const handleLogout = async () => {
    await logout()
    navigate(ROUTES.LOGIN, { replace: true })
  }

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-border bg-surface/90 backdrop-blur-md px-4 md:px-6">
      {/* Mobile Menu Trigger */}
      <Button
        variant="ghost"
        size="icon-sm"
        className="md:hidden text-text-secondary hover:text-text-primary"
        onClick={onMenuClick}
        aria-label="Open navigation menu"
      >
        <Menu className="h-5 w-5" />
      </Button>

      {/* Desktop Search Bar */}
      <div className="hidden md:block flex-1 max-w-xs lg:max-w-md">
        <div className="relative">
          <Search
            className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-text-muted pointer-events-none"
            aria-hidden="true"
          />
          <input
            type="search"
            placeholder="Search cases, reports, models..."
            aria-label="Global clinical search"
            className={cn(
              "h-9 w-full rounded-md border border-border bg-surface-raised/70 pl-9 pr-12 text-sm text-text-primary",
              "placeholder:text-text-muted/70",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-1 focus-visible:ring-offset-surface",
              "transition-colors duration-150",
            )}
          />
          <kbd
            className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 hidden sm:inline-flex items-center gap-0.5 rounded border border-border-subtle px-1.5 py-0.5 text-[10px] font-mono text-text-muted bg-surface select-none"
            aria-hidden="true"
          >
            ⌘K
          </kbd>
        </div>
      </div>

      {/* Mobile Search Toggle */}
      <div className="flex-1 md:hidden flex items-center">
        {searchOpen ? (
          <div className="relative w-full flex items-center">
            <Search
              className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-text-muted pointer-events-none"
              aria-hidden="true"
            />
            <input
              type="search"
              placeholder="Search..."
              autoFocus
              aria-label="Mobile search"
              className="h-8 w-full rounded-md border border-border bg-surface-raised pl-8 pr-8 text-xs text-text-primary placeholder:text-text-muted focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary"
            />
            <button
              onClick={() => setSearchOpen(false)}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary p-0.5"
              aria-label="Close search"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        ) : (
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={() => setSearchOpen(true)}
            className="text-text-secondary hover:text-text-primary"
            aria-label="Open search input"
          >
            <Search className="h-4 w-4" />
          </Button>
        )}
      </div>

      {/* Header Actions */}
      <div className="ml-auto flex items-center gap-1.5">
        {/* Theme Toggle */}
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={toggleTheme}
          aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
          className="text-text-secondary hover:text-text-primary"
        >
          {theme === "dark" ? (
            <Sun className="h-4 w-4" />
          ) : (
            <Moon className="h-4 w-4" />
          )}
        </Button>

        {/* Notifications Entry Point */}
        <Button
          variant="ghost"
          size="icon-sm"
          asChild
          className="relative text-text-secondary hover:text-text-primary"
          aria-label="View notifications"
        >
          <Link to={ROUTES.NOTIFICATIONS}>
            <div className="relative flex items-center justify-center">
              <Bell className="h-4 w-4" />
              <span
                className="absolute -top-1 -right-1 h-2 w-2 rounded-full bg-primary ring-2 ring-surface"
                aria-hidden="true"
              />
            </div>
          </Link>
        </Button>

        {/* User Profile Dropdown */}
        <DropdownMenu.Root>
          <DropdownMenu.Trigger asChild>
            <button
              className="flex items-center gap-2 rounded-md p-1 md:px-2 md:py-1 hover:bg-surface-raised transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary text-left"
              aria-label="Open user profile menu"
            >
              <Avatar
                src={user?.avatar_url ?? undefined}
                fallback={user?.full_name}
                size="sm"
              />
              <div className="hidden md:block">
                <p className="text-xs font-semibold text-text-primary leading-tight truncate max-w-[120px]">
                  {user?.full_name}
                </p>
                <p className="text-[10px] text-text-muted truncate max-w-[120px]">
                  {user?.role ? ROLE_LABELS[user.role] : ""}
                </p>
              </div>
              <ChevronDown
                className="h-3.5 w-3.5 text-text-muted hidden md:block"
                aria-hidden="true"
              />
            </button>
          </DropdownMenu.Trigger>

          <DropdownMenu.Portal>
            <DropdownMenu.Content
              align="end"
              sideOffset={6}
              className={cn(
                "z-50 min-w-56 rounded-lg border border-border bg-surface p-1.5 shadow-elevation-3 text-text-primary",
                "data-[state=open]:animate-in data-[state=closed]:animate-out",
                "data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0",
                "data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95",
              )}
            >
              {/* User Identity Header */}
              <div className="px-2.5 py-2 border-b border-border mb-1">
                <p className="text-xs font-semibold text-text-primary">
                  {user?.full_name}
                </p>
                <p className="text-[11px] text-text-muted truncate">
                  {user?.email}
                </p>
                {user?.role && (
                  <Badge variant="secondary" className="mt-1.5 text-[10px]">
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
                label="Change Password"
                onClick={() => navigate(ROUTES.CHANGE_PASSWORD)}
              />

              <DropdownMenu.Separator className="my-1 h-px bg-border" />

              {/* Theme Toggle in Menu */}
              <div className="flex items-center justify-between px-2.5 py-1.5 text-xs text-text-secondary select-none">
                <span className="flex items-center gap-2">
                  {theme === "dark" ? (
                    <Moon className="h-3.5 w-3.5 text-text-muted" />
                  ) : (
                    <Sun className="h-3.5 w-3.5 text-text-muted" />
                  )}
                  <span>{theme === "dark" ? "Dark Theme" : "Light Theme"}</span>
                </span>
                <button
                  type="button"
                  onClick={toggleTheme}
                  className="h-5 w-9 rounded-full bg-surface-raised border border-border relative transition-colors hover:border-primary focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary"
                  aria-label="Toggle color theme"
                >
                  <span
                    className={cn(
                      "absolute top-0.5 h-4 w-4 rounded-full bg-primary transition-transform duration-150",
                      theme === "dark" ? "translate-x-0.5" : "translate-x-4",
                    )}
                  />
                </button>
              </div>

              <DropdownMenu.Separator className="my-1 h-px bg-border" />

              <DropdownItem
                icon={<LogOut className="h-3.5 w-3.5" />}
                label="Sign Out"
                onClick={handleLogout}
                destructive
              />
            </DropdownMenu.Content>
          </DropdownMenu.Portal>
        </DropdownMenu.Root>
      </div>
    </header>
  )
}

function DropdownItem({
  icon,
  label,
  onClick,
  destructive = false,
}: {
  icon: React.ReactNode
  label: string
  onClick: () => void
  destructive?: boolean
}) {
  return (
    <DropdownMenu.Item
      onClick={onClick}
      className={cn(
        "flex items-center gap-2 rounded-md px-2.5 py-1.5 text-xs font-medium cursor-pointer select-none outline-none transition-colors duration-150",
        destructive
          ? "text-error hover:bg-error-surface hover:text-error"
          : "text-text-secondary hover:bg-surface-raised hover:text-text-primary",
      )}
    >
      <span className="shrink-0">{icon}</span>
      <span>{label}</span>
    </DropdownMenu.Item>
  )
}
