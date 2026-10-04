import { Search, X } from "lucide-react"
import { cn } from "@/lib/utils"

interface SearchBoxProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  className?: string
}

export function SearchBox({
  value,
  onChange,
  placeholder = "Search...",
  className,
}: SearchBoxProps) {
  return (
    <div className={cn("relative flex items-center", className)}>
      <Search
        className="absolute left-3 h-3.5 w-3.5 text-text-muted pointer-events-none"
        aria-hidden="true"
      />
      <input
        type="search"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        aria-label={placeholder}
        className={cn(
          "h-9 w-full rounded-md border border-border bg-surface pl-9 pr-8 text-sm text-text-primary",
          "placeholder:text-text-muted",
          "focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary",
          "transition-colors duration-150",
        )}
      />
      {value && (
        <button
          type="button"
          onClick={() => onChange("")}
          aria-label="Clear search query"
          className="absolute right-2.5 text-text-muted hover:text-text-primary transition-colors p-0.5 rounded-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      )}
    </div>
  )
}
