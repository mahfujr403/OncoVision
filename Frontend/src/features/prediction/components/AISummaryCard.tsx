import { useState } from "react"
import { Link } from "react-router-dom"
import {
  Brain,
  MessageSquare,
  Copy,
  Check,
  RefreshCw,
  AlertCircle,
  ShieldAlert,
  FileText,
} from "lucide-react"
import { Button } from "@/components/ui/Button"
import { Badge } from "@/components/ui/Badge"
import { Loader } from "@/components/ui/Loader"
import { ROUTES } from "@/constants/routes"
import { generatePredictionSummary } from "@/api/services/chatService"
import { toast } from "sonner"
import { cn } from "@/lib/utils"

interface AISummaryCardProps {
  predictionId: string
  initialSummary?: string | null
  className?: string
}

export function AISummaryCard({
  predictionId,
  initialSummary,
  className,
}: AISummaryCardProps) {
  const [summary, setSummary] = useState<string | null>(initialSummary ?? null)
  const [language, setLanguage] = useState<"en" | "bn">("en")
  const [isLoading, setIsLoading] = useState(false)
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleGenerate = async (targetLang = language) => {
    if (!predictionId) return
    setIsLoading(true)
    setError(null)
    try {
      const resp = await generatePredictionSummary(predictionId, {
        language: targetLang,
      })
      setSummary(resp.summary_text)
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Failed to generate AI summary"
      setError(msg)
      toast.error("Could not generate clinical summary. Please try again.")
    } finally {
      setIsLoading(false)
    }
  }

  const handleCopy = async () => {
    if (!summary) return
    try {
      await navigator.clipboard.writeText(summary)
      setCopied(true)
      toast.success("Clinical summary copied to clipboard")
      setTimeout(() => setCopied(false), 2000)
    } catch {
      toast.error("Failed to copy text")
    }
  }

  const handleLanguageChange = (lang: "en" | "bn") => {
    setLanguage(lang)
    if (summary) {
      handleGenerate(lang)
    }
  }

  return (
    <div
      className={cn(
        "rounded-xl border border-border bg-surface p-5 shadow-xs space-y-4",
        className,
      )}
    >
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-border-subtle">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary shrink-0">
            <Brain className="w-4 h-4" aria-hidden="true" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold text-text-primary">
                Clinical Decision Support Summary
              </h3>
              <Badge
                variant="secondary"
                className="text-[10px] font-mono px-1.5 py-0"
              >
                Gemini 2.5
              </Badge>
            </div>
            <p className="text-xs text-text-muted">
              Synthesized histopathological rationale &amp; differential
              diagnostic context
            </p>
          </div>
        </div>

        {/* Language selector & Interactive Chat link */}
        <div className="flex items-center gap-2 self-start sm:self-auto">
          <div className="inline-flex rounded-md border border-border-subtle bg-surface-raised p-0.5 text-xs font-medium">
            <button
              type="button"
              onClick={() => handleLanguageChange("en")}
              className={cn(
                "px-2.5 py-1 rounded transition-colors",
                language === "en"
                  ? "bg-surface text-text-primary shadow-xs font-semibold"
                  : "text-text-muted hover:text-text-primary",
              )}
            >
              English
            </button>
            <button
              type="button"
              onClick={() => handleLanguageChange("bn")}
              className={cn(
                "px-2.5 py-1 rounded transition-colors",
                language === "bn"
                  ? "bg-surface text-text-primary shadow-xs font-semibold"
                  : "text-text-muted hover:text-text-primary",
              )}
            >
              বাংলা
            </button>
          </div>

          <Button
            asChild
            variant="outline"
            size="sm"
            className="gap-1.5 text-xs border-border text-text-secondary hover:text-text-primary"
          >
            <Link to={`${ROUTES.PREDICTION_CHAT}/${predictionId}`}>
              <MessageSquare className="w-3.5 h-3.5 text-primary" />
              Case Discussion
            </Link>
          </Button>
        </div>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div
          className="py-8 flex flex-col items-center justify-center gap-3 text-center"
          role="status"
        >
          <Loader size="md" />
          <div className="space-y-1">
            <p className="text-sm font-medium text-text-primary">
              Synthesizing clinical findings…
            </p>
            <p className="text-xs text-text-muted">
              Analyzing ensemble probabilities and formulating structured
              pathological assessment notes.
            </p>
          </div>
        </div>
      )}

      {/* Error state */}
      {!isLoading && error && (
        <div
          className="rounded-lg border border-error/30 bg-error-surface p-4 space-y-3"
          role="alert"
        >
          <div className="flex items-start gap-2.5 text-error text-xs font-medium">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={() => handleGenerate()}
            className="gap-1.5 text-xs"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Retry Synthesis
          </Button>
        </div>
      )}

      {/* Empty / Not yet generated state */}
      {!isLoading && !summary && !error && (
        <div className="rounded-lg border border-dashed border-border bg-surface-raised/30 p-6 text-center space-y-3">
          <div className="flex justify-center">
            <div className="h-9 w-9 rounded-full bg-primary/10 flex items-center justify-center text-primary">
              <FileText className="h-4.5 w-4.5" />
            </div>
          </div>
          <div className="space-y-1 max-w-md mx-auto">
            <p className="text-xs font-medium text-text-primary">
              Generate Pathologist Synthesis
            </p>
            <p className="text-[11px] text-text-muted leading-relaxed">
              Synthesize an AI-formulated clinical interpretation of this
              ensemble prediction, confidence distribution, and diagnostic
              implications in {language === "en" ? "English" : "Bangla"}.
            </p>
          </div>
          <div className="pt-1">
            <Button
              variant="primary"
              size="sm"
              onClick={() => handleGenerate()}
              className="gap-2 shadow-xs"
            >
              <Brain className="w-3.5 h-3.5" />
              Generate Clinical Summary
            </Button>
          </div>
        </div>
      )}

      {/* Summary rendered state */}
      {!isLoading && summary && (
        <div className="space-y-3">
          <div className="rounded-lg border border-border-subtle bg-surface-raised/40 p-4 text-xs md:text-sm text-text-primary leading-relaxed whitespace-pre-line font-sans">
            {summary}
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
            <div className="flex items-center gap-1.5 text-[11px] text-text-muted">
              <ShieldAlert
                className="h-3.5 w-3.5 text-accent"
                aria-hidden="true"
              />
              <span>
                Computational synthesis — correlate with slide specimen &amp;
                clinical history.
              </span>
            </div>

            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="xs"
                onClick={handleCopy}
                className="gap-1.5 text-text-muted hover:text-text-primary"
                aria-label="Copy summary to clipboard"
              >
                {copied ? (
                  <Check className="w-3 h-3 text-success" />
                ) : (
                  <Copy className="w-3 h-3" />
                )}
                {copied ? "Copied" : "Copy"}
              </Button>
              <Button
                variant="ghost"
                size="xs"
                onClick={() => handleGenerate()}
                className="gap-1.5 text-text-muted hover:text-text-primary"
                aria-label="Regenerate summary"
              >
                <RefreshCw className="w-3 h-3" />
                Regenerate
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
