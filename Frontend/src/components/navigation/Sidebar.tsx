import { NavLink, useLocation } from "react-router-dom"
import {
  LayoutDashboard,
  Microscope,
  History,
  GitCompare,
  BarChart3,
  FileText,
  Bookmark,
  Star,
  Bell,
  User,
  Settings,
  Users,
  Cpu,
  Activity,
  ScrollText,
  ChevronRight,
  ChevronLeft,
  KeyRound,
  Brain,
  ShieldCheck,
} from "lucide-react"
import * as Tooltip from "@radix-ui/react-tooltip"
import { cn } from "@/lib/utils"
import { useAuth } from "@/hooks/useAuth"
import { ROUTES } from "@/constants/routes"
import { isAdmin, hasPermission } from "@/utils/permissions"
import { Avatar } from "@/components/ui/Avatar"
import { APP_NAME } from "@/constants/app"
import { ROLE_LABELS } from "@/constants/roles"

interface NavItem {
  label: string
  icon: React.ReactNode
  to: string
}

interface NavGroup {
  label: string
  items: NavItem[]
}

function buildNavGroups(role: ReturnType<typeof useAuth>["role"]): NavGroup[] {
  // 1. Primary Workspace
  const workspaceItems: NavItem[] = [
    {
      label: "Dashboard",
      icon: <LayoutDashboard className="h-4 w-4" />,
      to: ROUTES.DASHBOARD,
    },
    {
      label: "New Prediction",
      icon: <Microscope className="h-4 w-4" />,
      to: ROUTES.PREDICT,
    },
    {
      label: "Prediction History",
      icon: <History className="h-4 w-4" />,
      to: ROUTES.HISTORY,
    },
  ]

  if (hasPermission(role ?? undefined, "reports:view")) {
    workspaceItems.push({
      label: "Reports",
      icon: <FileText className="h-4 w-4" />,
      to: ROUTES.REPORTS,
    })
  }

  const groups: NavGroup[] = [
    {
      label: "Workspace",
      items: workspaceItems,
    },
  ]

  // 2. Intelligence
  const intelligenceItems: NavItem[] = [
    {
      label: "AI Medical Assistant",
      icon: <Brain className="h-4 w-4" />,
      to: ROUTES.AI_CHAT,
    },
  ]

  if (hasPermission(role ?? undefined, "comparison:view")) {
    intelligenceItems.push(
      {
        label: "Comparison",
        icon: <GitCompare className="h-4 w-4" />,
        to: ROUTES.COMPARISON,
      },
      {
        label: "Benchmark",
        icon: <BarChart3 className="h-4 w-4" />,
        to: ROUTES.BENCHMARK,
      },
    )
  }

  groups.push({
    label: "Intelligence",
    items: intelligenceItems,
  })

  // 3. Cases
  groups.push({
    label: "Cases",
    items: [
      {
        label: "Saved Cases",
        icon: <Bookmark className="h-4 w-4" />,
        to: ROUTES.SAVED_CASES,
      },
      {
        label: "Favorites",
        icon: <Star className="h-4 w-4" />,
        to: ROUTES.FAVORITES,
      },
    ],
  })

  // 4. System / Account
  groups.push({
    label: "System",
    items: [
      {
        label: "Notifications",
        icon: <Bell className="h-4 w-4" />,
        to: ROUTES.NOTIFICATIONS,
      },
      {
        label: "Profile",
        icon: <User className="h-4 w-4" />,
        to: ROUTES.PROFILE,
      },
      {
        label: "Settings",
        icon: <Settings className="h-4 w-4" />,
        to: ROUTES.SETTINGS,
      },
      {
        label: "Change Password",
        icon: <KeyRound className="h-4 w-4" />,
        to: ROUTES.CHANGE_PASSWORD,
      },
    ],
  })

  // 5. Administration (Role Restricted)
  if (isAdmin(role ?? undefined)) {
    groups.push({
      label: "Administration",
      items: [
        {
          label: "User Management",
          icon: <Users className="h-4 w-4" />,
          to: ROUTES.ADMIN_USERS,
        },
        {
          label: "All Prediction History",
          icon: <History className="h-4 w-4" />,
          to: ROUTES.ADMIN_HISTORY,
        },
        {
          label: "Model Management",
          icon: <Cpu className="h-4 w-4" />,
          to: ROUTES.ADMIN_MODELS,
        },
        {
          label: "Analytics",
          icon: <Activity className="h-4 w-4" />,
          to: ROUTES.ADMIN_ANALYTICS,
        },
        {
          label: "Audit Logs",
          icon: <ScrollText className="h-4 w-4" />,
          to: ROUTES.ADMIN_AUDIT_LOGS,
        },
        {
          label: "System Health",
          icon: <ShieldCheck className="h-4 w-4" />,
          to: ROUTES.ADMIN_SYSTEM_HEALTH,
        },
      ],
    })
  }

  return groups
}

interface SidebarProps {
  collapsed: boolean
  onToggle: () => void
  mobile?: boolean
  onClose?: () => void
}

export function Sidebar({
  collapsed,
  onToggle,
  mobile,
  onClose,
}: SidebarProps) {
  const { user, role } = useAuth()
  const location = useLocation()
  const groups = buildNavGroups(role)
  const isCollapsed = collapsed && !mobile

  return (
    <Tooltip.Provider delayDuration={120}>
      <aside
        className={cn(
          "flex flex-col h-full bg-surface border-r border-border transition-all duration-200 ease-in-out motion-reduce:transition-none select-none",
          isCollapsed ? "w-16" : "w-60",
          mobile && "w-64 max-w-full",
        )}
      >
        {/* Brand Area */}
        <div className="flex items-center gap-3 px-3.5 h-14 border-b border-border shrink-0 bg-surface">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-xs">
            <Microscope className="h-4 w-4" aria-hidden="true" />
          </div>
          {(!isCollapsed || mobile) && (
            <div className="overflow-hidden flex-1 min-w-0">
              <p className="text-sm font-semibold leading-none tracking-tight font-display text-text-primary truncate">
                {APP_NAME}
              </p>
              <p className="text-[11px] text-text-muted mt-1 truncate font-sans">
                Clinical Intelligence
              </p>
            </div>
          )}
          {!mobile && (
            <button
              onClick={onToggle}
              className={cn(
                "shrink-0 flex h-7 w-7 items-center justify-center rounded-md text-text-muted hover:text-text-primary hover:bg-surface-raised transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary",
                isCollapsed && "mx-auto",
              )}
              aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
              title={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
            >
              {isCollapsed ? (
                <ChevronRight className="h-4 w-4" />
              ) : (
                <ChevronLeft className="h-4 w-4" />
              )}
            </button>
          )}
        </div>

        {/* Navigation List */}
        <nav
          className="flex-1 overflow-y-auto py-3 px-2 space-y-4 focus-visible:outline-none"
          aria-label="Clinical workspace navigation"
        >
          {groups.map((group) => (
            <NavGroupSection
              key={group.label}
              group={group}
              collapsed={isCollapsed}
              currentPath={location.pathname}
              onItemClick={onClose}
            />
          ))}
        </nav>

        {/* User Profile Footer */}
        <div className="border-t border-border p-2.5 shrink-0 bg-surface/50">
          <NavLink
            to={ROUTES.PROFILE}
            onClick={onClose}
            className={cn(
              "flex items-center gap-2.5 rounded-md p-1.5 hover:bg-surface-raised transition-colors group focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary",
              isCollapsed && "justify-center p-1",
            )}
            title={isCollapsed ? user?.full_name || "User Profile" : undefined}
            aria-label="View user profile"
          >
            <Avatar
              src={user?.avatar_url ?? undefined}
              fallback={user?.full_name}
              size="sm"
            />
            {(!isCollapsed || mobile) && user && (
              <div className="flex-1 min-w-0 text-left">
                <p className="text-xs font-medium text-text-primary truncate group-hover:text-primary transition-colors">
                  {user.full_name}
                </p>
                <p className="text-[10px] text-text-muted truncate">
                  {ROLE_LABELS[user.role] ?? user.role}
                </p>
              </div>
            )}
          </NavLink>
        </div>
      </aside>
    </Tooltip.Provider>
  )
}

function NavGroupSection({
  group,
  collapsed,
  currentPath,
  onItemClick,
}: {
  group: NavGroup
  collapsed: boolean
  currentPath: string
  onItemClick?: () => void
}) {
  return (
    <div>
      {!collapsed && (
        <p className="px-2.5 mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-text-muted select-none">
          {group.label}
        </p>
      )}
      <ul className="space-y-0.5" role="list">
        {group.items.map((item) => {
          const isExact = currentPath === item.to
          const isChild =
            item.to !== ROUTES.DASHBOARD &&
            currentPath.startsWith(item.to + "/")
          const active = isExact || isChild

          return (
            <SidebarItem
              key={item.to}
              item={item}
              collapsed={collapsed}
              active={active}
              onClick={onItemClick}
            />
          )
        })}
      </ul>
    </div>
  )
}

function SidebarItem({
  item,
  collapsed,
  active,
  onClick,
}: {
  item: NavItem
  collapsed: boolean
  active: boolean
  onClick?: () => void
}) {
  const linkContent = (
    <NavLink
      to={item.to}
      onClick={onClick}
      className={cn(
        "flex items-center gap-3 rounded-md px-2.5 h-10 text-sm font-medium transition-colors duration-150 relative focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary",
        active
          ? "bg-primary/10 text-primary font-semibold before:absolute before:left-0 before:top-2 before:bottom-2 before:w-1 before:rounded-r-full before:bg-primary"
          : "text-text-secondary hover:bg-surface-raised hover:text-text-primary",
        collapsed && "justify-center px-0 w-10 mx-auto",
      )}
      aria-current={active ? "page" : undefined}
    >
      <span
        className={cn(
          "shrink-0 flex items-center justify-center",
          active ? "text-primary" : "text-text-muted",
        )}
      >
        {item.icon}
      </span>
      {!collapsed && (
        <span className="flex-1 truncate text-left">{item.label}</span>
      )}
      {!collapsed && active && (
        <ChevronRight
          className="h-3.5 w-3.5 text-primary shrink-0 opacity-70 ml-auto"
          aria-hidden="true"
        />
      )}
    </NavLink>
  )

  return (
    <li>
      {collapsed ? (
        <Tooltip.Root>
          <Tooltip.Trigger asChild>{linkContent}</Tooltip.Trigger>
          <Tooltip.Portal>
            <Tooltip.Content
              side="right"
              sideOffset={12}
              className="z-50 rounded-md border border-border bg-surface-raised px-2.5 py-1 text-xs font-medium text-text-primary shadow-elevation-2 animate-in fade-in-0 zoom-in-95"
            >
              {item.label}
              <Tooltip.Arrow className="fill-surface-raised" />
            </Tooltip.Content>
          </Tooltip.Portal>
        </Tooltip.Root>
      ) : (
        linkContent
      )}
    </li>
  )
}
