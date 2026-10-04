import { motion } from "framer-motion"
import {
  AlertTriangle,
  Microscope,
  Cpu,
  Layers,
  RotateCcw,
  Archive,
} from "lucide-react"
import { Link } from "react-router-dom"
import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/Badge"
import { Button } from "@/components/ui/Button"
import { getClassLabelColor } from "@/constants/app"
import { ROUTES } from "@/constants/routes"
import type { ApiError, PredictionResponse } from "@/types"
import type { ImageMeta } from "../types"
import { AISummaryCard } from "./AISummaryCard"

function getDiseaseBadgeVariant(
  label: string | null | undefined,
): "lungAca" | "lungScc" | "colonAca" | "lungBenign" | "colonBenign" | "secondary" {
  if (!label) return "secondary"
  const norm = label.toLowerCase()
  if (norm.includes("lung") && (norm.includes("adeno") || norm.includes("aca")))
    return "lungAca"
  if (
    norm.includes("lung") &&
    (norm.includes("squamous") || norm.includes("scc"))
  )
    return "lungScc"
  if (
    norm.includes("colon") &&
    (norm.includes("adeno") || norm.includes("aca"))
  )
    return "colonAca"
  if (norm.includes("lung") && norm.includes("benign")) return "lungBenign"
  if (norm.includes("colon") && norm.includes("benign")) return "colonBenign"
  return "secondary"
}

interface PredictionResultCardProps {
  result: PredictionResponse | null
  error: ApiError | null
  onReset: () => void
  imageMeta?: ImageMeta | null
  className?: string
}

export function PredictionResultCard({
  result,
  error,
  onReset,
  imageMeta,
  className,
}: PredictionResultCardProps) {
  if (!result && !error) return null

  if (error) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className={cn(
          "rounded-xl border border-error/30 bg-error-surface p-6 shadow-xs",
          className,
        )}
        role="alert"
      >
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-error/10 text-error">
            <AlertTriangle className="h-5 w-5" />
          </div>
          <div className="space-y-1">
            <h3 className="text-sm font-semibold text-text-primary">
              Analysis could not be completed
            </h3>
            <p className="text-xs md:text-sm text-text-secondary">
              {error.message}
            </p>
            {error.requestId && (
              <p className="text-[11px] font-mono text-text-muted">
                Request ID: {error.requestId}
              </p>
            )}
          </div>
        </div>
        <Button
          size="sm"
          variant="outline"
          onClick={onReset}
          className="mt-4 gap-1.5 border-border"
        >
          <RotateCcw className="h-3.5 w-3.5" />
          Try Again
        </Button>
      </motion.div>
    )
  }

  if (!result) return null

  const {
    status,
    result: outcome,
    individual_predictions,
    runtime_statistics,
    metadata,
  } = result

  const hasResult = Boolean(outcome) && outcome!.participating_models > 0

  if (status === "failed" || !hasResult) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className={cn(
          "rounded-xl border border-error/30 bg-error-surface p-6 shadow-xs",
          className,
        )}
        role="alert"
      >
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-error/10 text-error">
            <AlertTriangle className="h-5 w-5" />
          </div>
          <div className="space-y-1">
            <h3 className="text-sm font-semibold text-text-primary">
              No prediction available
            </h3>
            <p className="text-xs md:text-sm text-text-secondary">
              {status === "pending"
                ? "The prediction pipeline hasn't finished running for this request."
                : result.message}
            </p>
          </div>
        </div>
        <Button
          size="sm"
          variant="outline"
          onClick={onReset}
          className="mt-4 gap-1.5 border-border"
        >
          <RotateCcw className="h-3.5 w-3.5" />
          Try Again
        </Button>
      </motion.div>
    )
  }

  const hasFailedModels = outcome!.failed_models.length > 0
  const labelColor = getClassLabelColor(outcome!.prediction)
  const diseaseVariant = getDiseaseBadgeVariant(outcome!.prediction)

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className={cn("space-y-5", className)}
    >
      {/* Degraded Pipeline Notice */}
      {hasFailedModels && (
        <div className="flex items-start gap-2.5 rounded-lg border border-warning/30 bg-warning-surface px-4 py-3">
          <AlertTriangle
            className="mt-0.5 h-4 w-4 shrink-0 text-warning"
            aria-hidden="true"
          />
          <p className="text-xs text-text-secondary leading-relaxed">
            {outcome!.failed_models.length} model
            {outcome!.failed_models.length > 1 ? "s" : ""} failed to produce a
            result. Figures reflect the {outcome!.successful_models.length}{" "}
            model
            {outcome!.successful_models.length > 1 ? "s" : ""} that completed
            evaluation.
          </p>
        </div>
      )}

      {/* ── Primary Diagnostic Finding Card ── */}
      <div className="rounded-xl border border-border bg-surface p-5 sm:p-6 shadow-xs">
        <div className="flex items-center justify-between border-b border-border-subtle pb-3 mb-4">
          <div className="flex items-center gap-2 text-xs font-semibold text-text-muted uppercase tracking-wider">
            <Microscope className="h-4 w-4 text-primary" aria-hidden="true" />
            <span>Histopathological Finding</span>
          </div>
          <Badge variant={diseaseVariant} className="text-[11px] font-semibold">
            {outcome!.prediction}
          </Badge>
        </div>

        <div
          className={cn(
            "grid gap-6",
            imageMeta?.previewUrl
              ? "md:grid-cols-[220px_1fr] lg:grid-cols-[260px_1fr]"
              : "grid-cols-1",
          )}
        >
          {/* Specimen Evidence Thumbnail */}
          {imageMeta?.previewUrl && (
            <div className="overflow-hidden rounded-lg border border-border bg-neutral-950 flex items-center justify-center max-h-64 sm:max-h-full">
              <img
                src={imageMeta.previewUrl}
                alt="Histopathology slide specimen"
                className="max-h-full max-w-full object-contain"
              />
            </div>
          )}

          {/* Finding Metrics & Details */}
          <div className="space-y-4">
            <div>
              <p className="text-xs text-text-muted uppercase tracking-wider font-mono">
                Predicted Tissue Morphology
              </p>
              <h2
                className="text-2xl sm:text-3xl font-bold tracking-tight font-display mt-0.5"
                style={{ color: labelColor }}
              >
                {outcome!.prediction}
              </h2>
            </div>

            {/* Metrics Triad: Confidence, Agreement, Participating Models */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 pt-2">
              <MetricCard
                label="Model Confidence"
                value={`${outcome!.confidence}%`}
                desc="Ensemble probability"
              />
              <MetricCard
                label="Model Agreement"
                value={formatAgreement(outcome!.agreement_ratio)}
                desc="Cross-model consensus"
              />
              <MetricCard
                label="Active Models"
                value={String(outcome!.participating_models)}
                desc="Contributing architectures"
              />
            </div>

            {/* Model Architecture Badges */}
            <div className="pt-2">
              <p className="text-[11px] font-mono text-text-muted uppercase tracking-wider mb-1.5">
                Architecture Consensus
              </p>
              <div className="flex flex-wrap gap-1.5">
                {outcome!.successful_models.map((m) => (
                  <Badge
                    key={m}
                    variant="secondary"
                    className="text-[10px] font-mono"
                  >
                    ✓ {m}
                  </Badge>
                ))}
                {outcome!.failed_models.map((m) => (
                  <Badge
                    key={m}
                    variant="error"
                    className="text-[10px] font-mono"
                  >
                    ✕ {m} failed
                  </Badge>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── AI Clinical Decision Support Summary ── */}
      <AISummaryCard predictionId={result.prediction_id} />

      {/* ── Individual Model Predictions Breakdown ── */}
      {individual_predictions && individual_predictions.length > 0 && (
        <div className="rounded-xl border border-border bg-surface p-5 shadow-xs">
          <div className="mb-3.5 flex items-center justify-between border-b border-border-subtle pb-2.5">
            <div className="flex items-center gap-2 text-xs font-semibold text-text-muted uppercase tracking-wider">
              <Layers className="h-4 w-4 text-text-muted" aria-hidden="true" />
              <span>Individual Model Breakdown</span>
            </div>
            <span className="text-[10px] font-mono text-text-muted">
              {individual_predictions.length} Networks Evaluated
            </span>
          </div>

          <div className="space-y-2">
            {individual_predictions.map((m) => (
              <div
                key={m.model_name}
                className="flex items-center justify-between rounded-lg border border-border-subtle bg-surface-raised/40 px-3.5 py-2.5 text-xs"
              >
                <span className="font-mono font-semibold text-text-primary">
                  {m.model_name}
                </span>
                <span className="text-text-secondary font-medium">
                  {m.prediction}
                </span>
                <span className="font-mono tabular-nums font-semibold text-text-primary">
                  {m.confidence}%
                </span>
                <span className="font-mono tabular-nums text-text-muted">
                  {m.inference_time_ms} ms
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Runtime Performance Telemetry ── */}
      {runtime_statistics && (
        <div className="rounded-xl border border-border bg-surface p-5 shadow-xs">
          <div className="mb-3 flex items-center justify-between border-b border-border-subtle pb-2">
            <div className="flex items-center gap-2 text-xs font-semibold text-text-muted uppercase tracking-wider">
              <Cpu className="h-4 w-4 text-text-muted" aria-hidden="true" />
              <span>Inference Telemetry</span>
            </div>
            <Badge
              variant={
                runtime_statistics.runtime_status === "operational"
                  ? "success"
                  : "warning"
              }
              className="text-[10px] capitalize"
            >
              {runtime_statistics.runtime_status}
            </Badge>
          </div>

          <div className="grid grid-cols-2 gap-3 text-xs sm:grid-cols-4">
            <MetricItem
              label="Loaded Models"
              value={String(runtime_statistics.loaded_model_count ?? "—")}
            />
            <MetricItem
              label="Preprocessing"
              value={fmtMs(runtime_statistics.preprocessing_time_ms)}
            />
            <MetricItem
              label="Total Inference"
              value={fmtMs(runtime_statistics.total_inference_time_ms)}
            />
            <MetricItem
              label="Overall Processing"
              value={fmtMs(runtime_statistics.overall_processing_time_ms)}
            />
          </div>
        </div>
      )}

      {/* ── Workflow Navigation Actions & Metadata Footer ── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pt-1">
        <div className="flex items-center gap-2.5">
          <Button
            size="sm"
            variant="primary"
            onClick={onReset}
            className="gap-2 shadow-xs"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            Analyze Another Slide
          </Button>

          <Button
            asChild
            size="sm"
            variant="outline"
            className="gap-1.5 border-border text-text-secondary hover:text-text-primary"
          >
            <Link to={ROUTES.HISTORY}>
              <Archive className="h-3.5 w-3.5" />
              History Archive
            </Link>
          </Button>
        </div>

        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] font-mono tabular-nums text-text-muted">
          <span>API v{metadata.api_version}</span>
          <span>·</span>
          <span>Engine v{metadata.backend_version}</span>
          <span>·</span>
          <span>{metadata.processing_time_ms} ms</span>
        </div>
      </div>
    </motion.div>
  )
}

function MetricCard({
  label,
  value,
  desc,
}: {
  label: string
  value: string
  desc?: string
}) {
  return (
    <div className="rounded-lg border border-border-subtle bg-surface-raised/40 p-3">
      <p className="text-[10px] uppercase tracking-wider text-text-muted font-medium">
        {label}
      </p>
      <p className="text-xl font-bold font-mono tabular-nums text-text-primary mt-0.5">
        {value}
      </p>
      {desc && (
        <p className="text-[10px] text-text-muted mt-0.5 truncate">{desc}</p>
      )}
    </div>
  )
}

function MetricItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border-subtle bg-surface-raised/30 p-2.5">
      <p className="text-[10px] uppercase tracking-wider text-text-muted font-mono">
        {label}
      </p>
      <p className="text-sm font-semibold font-mono tabular-nums text-text-primary mt-0.5">
        {value}
      </p>
    </div>
  )
}

function fmtMs(value: number | null): string {
  return value === null ? "—" : `${value} ms`
}

function formatAgreement(agreementRatio: number | null | undefined): string {
  if (
    agreementRatio === null ||
    agreementRatio === undefined ||
    Number.isNaN(agreementRatio)
  ) {
    return "N/A"
  }
  return `${Math.round(agreementRatio * 100)}%`
}
