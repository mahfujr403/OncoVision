import type { ReactNode } from "react"
import { cn } from "@/lib/utils"
import { Button } from "./Button"

interface EmptyStateProps {
  icon?: ReactNode
  title: string
  description?: string
  action?: {
    label: string
    onClick: () => void
  }
  compact?: boolean
  className?: string
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 py-16 px-6 text-center",
        className,
      )}
    >
      {icon && (
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-surface-raised border border-border-subtle text-text-muted shadow-xs">
          {icon}
        </div>
      )}
      <div className="space-y-1">
        <h3 className="font-semibold text-base text-text-primary">{title}</h3>
        {description && (
          <p className="text-sm text-text-secondary max-w-sm">{description}</p>
        )}
      </div>
      {action && (
        <Button
          size="sm"
          variant="outline"
          onClick={action.onClick}
          className="mt-1"
        >
          {action.label}
        </Button>
      )}
    </div>
  )
}
