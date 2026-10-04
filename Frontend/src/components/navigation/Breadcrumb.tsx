import { Link, useLocation } from "react-router-dom"
import { ChevronRight, Home } from "lucide-react"
import { ROUTES } from "@/constants/routes"

const ROUTE_LABELS: Record<string, string> = {
  dashboard: "Workspace",
  predict: "New Prediction",
  history: "Prediction History",
  comparison: "Model Comparison",
  benchmark: "Clinical Benchmark",
  reports: "Reports",
  "saved-cases": "Saved Cases",
  favorites: "Favorites",
  notifications: "Notifications",
  profile: "Profile",
  settings: "Settings",
  "change-password": "Change Password",
  "ai-chat": "AI Medical Assistant",
  "prediction-chat": "Prediction Chat",
  admin: "Administration",
  users: "User Management",
  models: "Model Management",
  analytics: "Analytics",
  "audit-logs": "Audit Logs",
  "system-health": "System Health",
  "verify-email": "Verify Email",
  "reset-password": "Reset Password",
}

function formatSegmentLabel(seg: string): string {
  if (ROUTE_LABELS[seg]) {
    return ROUTE_LABELS[seg]
  }

  // Detect UUID or long alphanumeric hash
  if (/^[0-9a-fA-F-]{12,}$/.test(seg)) {
    return `Case #${seg.slice(0, 8)}`
  }

  // Detect pure numeric ID
  if (/^\d+$/.test(seg)) {
    return `Record #${seg}`
  }

  // Fallback: capitalize hyphenated words
  return seg
    .split("-")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ")
}

export function Breadcrumb() {
  const { pathname } = useLocation()
  const segments = pathname.split("/").filter(Boolean)

  // If user is at root /dashboard, show clean "Workspace / Dashboard"
  return (
    <nav
      aria-label="Breadcrumb"
      className="flex items-center min-w-0 overflow-hidden"
    >
      <ol className="flex items-center gap-1.5 text-xs text-text-muted flex-wrap">
        <li className="flex items-center">
          <Link
            to={ROUTES.DASHBOARD}
            className="flex items-center text-text-muted hover:text-text-primary transition-colors rounded p-0.5 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary"
            aria-label="Workspace Home"
          >
            <Home className="h-3.5 w-3.5" aria-hidden="true" />
          </Link>
        </li>

        {segments.map((seg, i) => {
          // Skip first 'dashboard' segment if it's right after Home link
          if (i === 0 && seg === "dashboard" && segments.length > 1) {
            return null
          }

          const path = "/" + segments.slice(0, i + 1).join("/")
          const label = formatSegmentLabel(seg)
          const isLast = i === segments.length - 1

          return (
            <li key={path} className="flex items-center gap-1.5 min-w-0">
              <ChevronRight
                className="h-3 w-3 text-text-muted/40 shrink-0"
                aria-hidden="true"
              />
              {isLast ? (
                <span
                  className="font-medium text-text-primary truncate max-w-[200px] sm:max-w-xs"
                  aria-current="page"
                >
                  {label}
                </span>
              ) : (
                <Link
                  to={path}
                  className="hover:text-text-primary transition-colors truncate max-w-[150px] sm:max-w-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary rounded px-0.5"
                >
                  {label}
                </Link>
              )}
            </li>
          )
        })}
      </ol>
    </nav>
  )
}
