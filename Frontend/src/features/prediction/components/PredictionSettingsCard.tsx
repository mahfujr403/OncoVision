import { motion } from "framer-motion"
import { Settings2, FlaskConical } from "lucide-react"
import { cn } from "@/lib/utils"
import type { PredictionConfig } from "../types"

interface PredictionSettingsCardProps {
  config: PredictionConfig
  onConfidenceChange: (value: number) => void
  onFlagChange: (
    key: "includeIndividualPredictions" | "includeRuntimeStatistics" | "saveHistory" | "generateReport",
    value: boolean,
  ) => void
  className?: string
}

function ToggleRow({
  label,
  description,
  checked,
  onChange,
  disabled = false,
  disabledNote,
}: {
  label: string
  description: string
  checked: boolean
  onChange: (value: boolean) => void
  disabled?: boolean
  disabledNote?: string
}) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div className="space-y-0.5">
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-medium text-text-primary">{label}</span>
          {disabled && disabledNote && (
            <span className="rounded-full bg-warning-surface px-1.5 py-0.5 text-[10px] font-semibold text-warning">
              {disabledNote}
            </span>
          )}
        </div>
        <p className="text-[11px] leading-snug text-text-muted max-w-[220px]">
          {description}
        </p>
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-label={label}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={cn(
          "relative mt-0.5 h-5 w-9 shrink-0 rounded-full transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 select-none cursor-pointer",
          checked && !disabled
            ? "bg-primary"
            : "bg-surface-raised border border-border",
          disabled && "cursor-not-allowed opacity-40",
        )}
      >
        <span
          className={cn(
            "inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow-xs transition-transform duration-150",
            checked ? "translate-x-[18px]" : "translate-x-0.5",
          )}
        />
      </button>
    </div>
  )
}

export function PredictionSettingsCard({
  config,
  onConfidenceChange,
  onFlagChange,
  className,
}: PredictionSettingsCardProps) {
  const pct = Math.round(config.confidenceThreshold * 100)

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: 0.05 }}
      className={cn(
        "rounded-xl border border-border bg-surface p-5 shadow-xs",
        className,
      )}
    >
      <div className="mb-4 flex items-center gap-2">
        <Settings2 className="h-4 w-4 text-primary" aria-hidden="true" />
        <h2 className="text-sm font-semibold tracking-tight text-text-primary">
          Prediction Settings
        </h2>
      </div>

      <div className="space-y-4">
        {/* Confidence threshold slider */}
        <div className="space-y-2.5">
          <div className="flex items-center justify-between">
            <span className="text-xs text-text-muted">
              Reliability Threshold
            </span>
            <span className="font-mono text-xs font-semibold text-primary tabular-nums">
              {pct}%
            </span>
          </div>
          <div className="relative">
            <input
              type="range"
              min={0}
              max={100}
              step={1}
              value={pct}
              onChange={(e) => onConfidenceChange(Number(e.target.value) / 100)}
              aria-label={`Reliability threshold: ${pct}%`}
              className="w-full cursor-pointer appearance-none rounded-full bg-surface-raised h-1.5 accent-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-1"
            />
            <div
              className="pointer-events-none absolute left-0 top-0 h-1.5 rounded-full bg-primary/70 mt-0"
              style={{ width: `${pct}%` }}
            />
          </div>
          <p className="text-[11px] leading-snug text-text-muted">
            Used only to flag low-reliability results for review — it never
            changes what the models predict.
          </p>
        </div>

        <hr className="border-border-subtle" />

        <ToggleRow
          label="Individual model predictions"
          description="Include each model's own prediction alongside the final ensemble result."
          checked={config.includeIndividualPredictions}
          onChange={(v) => onFlagChange("includeIndividualPredictions", v)}
        />

        <ToggleRow
          label="Runtime statistics"
          description="Include AI runtime health and execution timing in the response."
          checked={config.includeRuntimeStatistics}
          onChange={(v) => onFlagChange("includeRuntimeStatistics", v)}
        />

        <ToggleRow
          label="Save to history"
          description="Persist this prediction to your Prediction History."
          checked={config.saveHistory}
          onChange={(v) => onFlagChange("saveHistory", v)}
        />

        <ToggleRow
          label="Generate history report"
          description="Downloads a PDF report of your complete prediction history right after this analysis finishes."
          checked={config.generateReport}
          onChange={(v) => onFlagChange("generateReport", v)}
        />

        <hr className="border-border-subtle" />
        <div className="flex items-center justify-between gap-4">
          <span className="flex items-center gap-1.5 text-xs text-text-muted">
            <FlaskConical
              className="h-3.5 w-3.5 text-text-muted"
              aria-hidden="true"
            />
            Model input size
          </span>
          <span className="rounded-md border border-border-subtle bg-surface-raised px-2.5 py-1 font-mono text-xs text-text-primary tabular-nums">
            {config.imageSize}
          </span>
        </div>
        <p className="text-[11px] leading-snug text-text-muted -mt-1">
          Every image is resized to this before inference, regardless of the
          dimensions you upload.
        </p>
      </div>
    </motion.div>
  )
}
