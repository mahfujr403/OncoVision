import { Upload, Cpu, GitMerge, FileText } from "lucide-react"
import { cn } from "@/lib/utils"
import { WORKFLOW_STEPS } from "../constants"
import type { WorkspaceStatus } from "../types"

const ICON_MAP: Record<string, React.ReactNode> = {
  upload: <Upload className="h-3.5 w-3.5" />,
  cpu: <Cpu className="h-3.5 w-3.5" />,
  "git-merge": <GitMerge className="h-3.5 w-3.5" />,
  "file-text": <FileText className="h-3.5 w-3.5" />,
}

function stepStatusFromWorkspace(
  step: number,
  workspaceStatus: WorkspaceStatus,
  analysisStage: number,
): "done" | "active" | "pending" {
  if (workspaceStatus === "complete") return "done"
  if (workspaceStatus === "error" || workspaceStatus === "idle")
    return "pending"

  if (workspaceStatus === "uploading") {
    if (step === 1) return "done"
    return "pending"
  }

  if (step === 1) return "done"
  if (step === 2) return analysisStage >= 2 ? "done" : "active"
  if (step === 3) return analysisStage >= 2 ? "active" : "pending"
  return "pending"
}

interface PredictionWorkflowCardProps {
  status?: WorkspaceStatus
  analysisStage?: number
  className?: string
}

export function PredictionWorkflowCard({
  status = "idle",
  analysisStage = 0,
  className,
}: PredictionWorkflowCardProps) {
  return (
    <div
      className={cn(
        "rounded-xl border border-border bg-surface p-4 shadow-xs",
        className,
      )}
    >
      <div className="flex items-center justify-between mb-4 border-b border-border-subtle pb-2.5">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-text-muted">
          Diagnostic Workflow
        </h3>
        <span className="text-[10px] font-mono text-text-muted">
          Protocol 4.2
        </span>
      </div>

      <ol className="relative space-y-0" aria-label="Analysis workflow steps">
        {WORKFLOW_STEPS.map((wf, idx) => {
          const stepStatus = stepStatusFromWorkspace(
            wf.step,
            status,
            analysisStage,
          )
          const isLast = idx === WORKFLOW_STEPS.length - 1

          return (
            <li key={wf.step} className="relative flex gap-3">
              {/* Connector line */}
              {!isLast && (
                <span
                  className={cn(
                    "absolute left-[13px] top-7 h-[calc(100%-4px)] w-px",
                    stepStatus === "done"
                      ? "bg-primary/50"
                      : "bg-border-subtle",
                  )}
                  aria-hidden="true"
                />
              )}

              {/* Step node */}
              <div
                className={cn(
                  "relative z-10 mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border text-xs font-semibold transition-colors duration-150",
                  stepStatus === "done" &&
                    "border-primary bg-primary-surface text-primary",
                  stepStatus === "active" &&
                    "border-primary bg-primary/20 text-primary ring-2 ring-primary/30",
                  stepStatus === "pending" &&
                    "border-border-subtle bg-surface-raised text-text-muted",
                )}
                aria-label={`Step ${wf.step}: ${stepStatus}`}
              >
                {ICON_MAP[wf.icon]}
              </div>

              {/* Step text */}
              <div className={cn("pb-4.5", isLast && "pb-0")}>
                <p
                  className={cn(
                    "text-xs font-medium leading-5",
                    stepStatus === "pending" && "text-text-muted",
                    stepStatus === "active" && "text-primary font-semibold",
                    stepStatus === "done" && "text-text-primary font-semibold",
                  )}
                >
                  {wf.label}
                </p>
                <p className="mt-0.5 text-[11px] leading-relaxed text-text-muted">
                  {wf.description}
                </p>
              </div>
            </li>
          )
        })}
      </ol>
    </div>
  )
}
