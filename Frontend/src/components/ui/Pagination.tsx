import { ChevronLeft, ChevronRight } from "lucide-react"
import { Button } from "./Button"
import { cn } from "@/lib/utils"

interface PaginationProps {
  page: number
  totalPages: number
  onPageChange: (page: number) => void
  className?: string
}

export function Pagination({
  page,
  totalPages,
  onPageChange,
  className,
}: PaginationProps) {
  const pages = Array.from({ length: Math.min(totalPages, 7) }, (_, i) => {
    if (totalPages <= 7) return i + 1
    if (page <= 4) return i + 1
    if (page >= totalPages - 3) return totalPages - 6 + i
    return page - 3 + i
  })

  return (
    <nav
      role="navigation"
      aria-label="Pagination Navigation"
      className={cn("flex items-center gap-1", className)}
    >
      <Button
        variant="ghost"
        size="icon-sm"
        onClick={() => onPageChange(page - 1)}
        disabled={page <= 1}
        aria-label="Previous page"
      >
        <ChevronLeft className="h-4 w-4" />
      </Button>

      {pages[0] > 1 && (
        <>
          <PageButton page={1} current={page} onClick={onPageChange} />
          {pages[0] > 2 && (
            <span
              className="px-1 text-text-muted text-xs font-mono"
              aria-hidden="true"
            >
              …
            </span>
          )}
        </>
      )}

      {pages.map((p) => (
        <PageButton key={p} page={p} current={page} onClick={onPageChange} />
      ))}

      {pages[pages.length - 1] < totalPages && (
        <>
          {pages[pages.length - 1] < totalPages - 1 && (
            <span
              className="px-1 text-text-muted text-xs font-mono"
              aria-hidden="true"
            >
              …
            </span>
          )}
          <PageButton page={totalPages} current={page} onClick={onPageChange} />
        </>
      )}

      <Button
        variant="ghost"
        size="icon-sm"
        onClick={() => onPageChange(page + 1)}
        disabled={page >= totalPages}
        aria-label="Next page"
      >
        <ChevronRight className="h-4 w-4" />
      </Button>
    </nav>
  )
}

function PageButton({
  page,
  current,
  onClick,
}: {
  page: number
  current: number
  onClick: (p: number) => void
}) {
  const isCurrent = page === current
  return (
    <button
      onClick={() => onClick(page)}
      aria-label={`Page ${page}`}
      aria-current={isCurrent ? "page" : undefined}
      className={cn(
        "h-7 min-w-7 px-2 rounded-md text-xs font-mono font-medium transition-colors select-none focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary",
        isCurrent
          ? "bg-primary text-primary-foreground font-semibold shadow-xs"
          : "text-text-secondary hover:bg-surface-raised hover:text-text-primary",
      )}
    >
      {page}
    </button>
  )
}
