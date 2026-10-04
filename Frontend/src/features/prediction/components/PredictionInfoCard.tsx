import { FileImage, Info } from "lucide-react"
import { cn } from "@/lib/utils"
import { SUPPORTED_FORMATS, IMAGE_REQUIREMENTS } from "../constants"

interface PredictionInfoCardProps {
  className?: string
}

export function PredictionInfoCard({ className }: PredictionInfoCardProps) {
  return (
    <div className={cn("space-y-4", className)}>
      {/* Supported Formats */}
      <div className="rounded-xl border border-border bg-surface p-4 shadow-xs">
        <div className="mb-3 flex items-center justify-between border-b border-border-subtle pb-2">
          <div className="flex items-center gap-2">
            <FileImage
              className="h-3.5 w-3.5 text-primary"
              aria-hidden="true"
            />
            <h3 className="text-xs font-semibold uppercase tracking-wider text-text-muted">
              Supported Formats
            </h3>
          </div>
          <span className="text-[10px] font-mono text-text-muted">
            H&amp;E Slides
          </span>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {SUPPORTED_FORMATS.filter(
            (f, i, arr) => arr.findIndex((x) => x.ext === f.ext) === i,
          ).map((fmt) => (
            <span
              key={fmt.ext}
              className="rounded-md border border-border-subtle bg-surface-raised px-2 py-0.5 font-mono text-xs font-medium text-text-secondary"
            >
              .{fmt.ext}
            </span>
          ))}
        </div>
      </div>

      {/* Image Requirements */}
      <div className="rounded-xl border border-border bg-surface p-4 shadow-xs">
        <div className="mb-3 flex items-center justify-between border-b border-border-subtle pb-2">
          <div className="flex items-center gap-2">
            <Info className="h-3.5 w-3.5 text-accent" aria-hidden="true" />
            <h3 className="text-xs font-semibold uppercase tracking-wider text-text-muted">
              Slide Criteria
            </h3>
          </div>
          <span className="text-[10px] font-mono text-text-muted">
            Quality Spec
          </span>
        </div>
        <ul className="space-y-2.5">
          {IMAGE_REQUIREMENTS.map((req) => (
            <li
              key={req.label}
              className="flex items-center justify-between gap-2 text-xs"
            >
              <span className="text-text-muted">{req.label}</span>
              <span className="font-mono font-medium tabular-nums text-text-primary">
                {req.value}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
