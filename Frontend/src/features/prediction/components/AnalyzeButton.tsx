import { Microscope, Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"

interface AnalyzeButtonProps {
  disabled: boolean
  isAnalyzing: boolean
  onClick: () => void
  className?: string
}

export function AnalyzeButton({
  disabled,
  isAnalyzing,
  onClick,
  className,
}: AnalyzeButtonProps) {
  const isReady = !disabled && !isAnalyzing

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled || isAnalyzing}
      aria-label={
        isAnalyzing ? "Analysis in progress…" : "Run Ensemble AI Prediction"
      }
      aria-busy={isAnalyzing}
      className={cn(
        "relative flex w-full items-center justify-center gap-2.5 rounded-xl px-6 py-3.5 text-sm font-semibold tracking-wide transition-all duration-150",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background",
        isReady
          ? "bg-primary text-primary-foreground shadow-xs hover:bg-primary-hover active:scale-[0.99] cursor-pointer"
          : isAnalyzing
            ? "bg-primary/80 text-primary-foreground cursor-wait"
            : "bg-surface-raised border border-border text-text-muted cursor-not-allowed opacity-70",
        className,
      )}
    >
      {isAnalyzing ? (
        <>
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          <span>Analyzing Histopathology Slide…</span>
        </>
      ) : isReady ? (
        <>
          <Microscope className="h-4 w-4" aria-hidden="true" />
          <span>Run Ensemble Classification</span>
        </>
      ) : (
        <>
          <Microscope className="h-4 w-4 opacity-50" aria-hidden="true" />
          <span>Upload an image to start analysis</span>
        </>
      )}
    </button>
  )
}
