import { motion, AnimatePresence } from "framer-motion"
import { Check, Loader2, AlertCircle, Clock } from "lucide-react"
import { cn } from "@/lib/utils"
import type { AnalyzeStepInfo, StepStatus } from "../types"

function StepIcon({ status }: { status: StepStatus }) {
  if (status === "done")
    return (
      <span className="flex h-6 w-6 items-center justify-center rounded-full bg-success-surface text-success border border-success/30">
        <Check className="h-3.5 w-3.5" strokeWidth={2.5} />
      </span>
    )
  if (status === "active")
    return (
      <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary-surface text-primary border border-primary/30">
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
      </span>
    )
  if (status === "error")
    return (
      <span className="flex h-6 w-6 items-center justify-center rounded-full bg-error-surface text-error border border-error/30">
        <AlertCircle className="h-3.5 w-3.5" />
      </span>
    )
  return (
    <span className="flex h-6 w-6 items-center justify-center rounded-full border border-border-subtle bg-surface text-text-muted">
      <Clock className="h-3 w-3" />
    </span>
  )
}

interface UploadProgressProps {
  steps: AnalyzeStepInfo[]
  visible: boolean
  className?: string
}

export function UploadProgress({
  steps,
  visible,
  className,
}: UploadProgressProps) {
  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          key="upload-progress"
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: "auto" }}
          exit={{ opacity: 0, height: 0 }}
          transition={{ duration: 0.2 }}
          className={cn("overflow-hidden", className)}
          role="status"
          aria-live="polite"
        >
          <div className="rounded-xl border border-border bg-surface p-4 shadow-xs">
            <div className="flex items-center justify-between mb-3 border-b border-border-subtle pb-2">
              <p className="text-xs font-semibold uppercase tracking-wider text-text-muted">
                Inference Pipeline Progress
              </p>
              <span className="text-[10px] font-mono text-text-muted">
                Ensemble Pipeline
              </span>
            </div>

            <ol
              className="relative space-y-0"
              aria-label="Pipeline progress steps"
            >
              {steps.map((step, idx) => {
                const isLast = idx === steps.length - 1
                return (
                  <li key={step.id} className="relative flex gap-3">
                    {/* Connector line */}
                    {!isLast && (
                      <span
                        className={cn(
                          "absolute left-[11px] top-6 h-[calc(100%-4px)] w-px transition-colors duration-200",
                          step.status === "done"
                            ? "bg-success/50"
                            : "bg-border-subtle",
                        )}
                        aria-hidden="true"
                      />
                    )}

                    {/* Step Icon */}
                    <div className="relative z-10 mt-0.5 shrink-0">
                      <StepIcon status={step.status} />
                    </div>

                    {/* Step Label */}
                    <div className={cn("pb-3.5", isLast && "pb-0")}>
                      <p
                        className={cn(
                          "text-xs font-medium leading-6 transition-colors duration-150",
                          step.status === "done" &&
                            "text-text-primary font-semibold",
                          step.status === "active" &&
                            "text-primary font-semibold",
                          step.status === "error" && "text-error font-semibold",
                          step.status === "pending" && "text-text-muted",
                        )}
                      >
                        {step.label}
                      </p>
                    </div>
                  </li>
                )
              })}
            </ol>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
