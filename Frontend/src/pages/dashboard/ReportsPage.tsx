import { useState } from 'react';
import { toast } from 'sonner';
import { BarChart3, FileDown, FileSpreadsheet, ShieldAlert, Layers, Activity, Calendar } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { ErrorState } from '@/components/ui/ErrorState';
import { Skeleton } from '@/components/ui/Skeleton';
import { useAnalytics } from '@/hooks/queries/useAnalytics';
import { exportPredictionHistoryCsv, exportPredictionReportPdf } from '@/api/services/reportsService';
import { getClassLabelColor } from '@/constants/app';
import { formatDateTime } from '@/utils/formatters';
import type { ApiError } from '@/types';

function getDiseaseBadgeVariant(
  label: string | null | undefined,
): 'lungAca' | 'lungScc' | 'colonAca' | 'lungBenign' | 'colonBenign' | 'secondary' {
  if (!label) return 'secondary';
  const norm = label.toLowerCase();
  if (norm.includes('lung') && (norm.includes('adeno') || norm.includes('aca'))) return 'lungAca';
  if (norm.includes('lung') && (norm.includes('squamous') || norm.includes('scc'))) return 'lungScc';
  if (norm.includes('colon') && (norm.includes('adeno') || norm.includes('aca'))) return 'colonAca';
  if (norm.includes('lung') && norm.includes('benign')) return 'lungBenign';
  if (norm.includes('colon') && norm.includes('benign')) return 'colonBenign';
  return 'secondary';
}

function formatClassLabel(raw: string | null | undefined): string {
  if (!raw) return '—';
  return raw
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

export default function ReportsPage() {
  const { data, isLoading, isError, refetch } = useAnalytics();
  const [exporting, setExporting] = useState<'csv' | 'pdf' | null>(null);

  const handleExport = async (format: 'csv' | 'pdf') => {
    setExporting(format);
    try {
      if (format === 'csv') await exportPredictionHistoryCsv();
      else await exportPredictionReportPdf();
      toast.success(`${format.toUpperCase()} export downloaded successfully.`);
    } catch (err) {
      const apiErr = err as ApiError;
      toast.error(apiErr.message ?? `Failed to export ${format.toUpperCase()}.`);
    } finally {
      setExporting(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* ── Page Header ── */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-border pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl md:text-2xl font-bold tracking-tight font-display text-text-primary">
              Diagnostic Reports &amp; Evidence Telemetry
            </h1>
            <Badge variant="outline" className="font-mono text-[11px] text-text-muted">
              Live Telemetry
            </Badge>
          </div>
          <p className="text-xs md:text-sm text-text-muted mt-0.5">
            Review generated computational pathology reports and aggregated model evidence across historical evaluations.
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleExport('csv')}
            loading={exporting === 'csv'}
            disabled={exporting !== null}
            className="gap-1.5"
            aria-label="Export evaluation history as CSV"
          >
            <FileSpreadsheet className="h-3.5 w-3.5" />
            Export CSV
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleExport('pdf')}
            loading={exporting === 'pdf'}
            disabled={exporting !== null}
            className="gap-1.5"
            aria-label="Export diagnostic report as PDF"
          >
            <FileDown className="h-3.5 w-3.5" />
            Export PDF
          </Button>
        </div>
      </div>

      {/* ── Persistent Research Disclaimer Banner ── */}
      <div className="flex items-start gap-3 rounded-lg border border-border-subtle bg-surface-raised/40 px-4 py-3 text-xs text-text-secondary">
        <ShieldAlert className="h-4 w-4 shrink-0 text-accent mt-0.5" aria-hidden="true" />
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-text-primary">
            Investigational Clinical Decision Support
          </p>
          <p className="text-text-muted mt-0.5 leading-relaxed">
            Report analytics and model consensus distributions represent statistical computational evidence. These metrics do not represent clinical diagnostic accuracy or patient health outcomes and are provided exclusively for investigational pathology review.
          </p>
        </div>
      </div>

      {isError ? (
        <Card className="p-6 border border-border bg-surface">
          <ErrorState
            title="Failed to Load Evidence Telemetry"
            message="The analytics snapshot could not be computed or retrieved from the server."
            onRetry={() => refetch()}
          />
        </Card>
      ) : isLoading || !data ? (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Card key={i} className="space-y-2 p-4 border border-border bg-surface">
                <Skeleton className="h-3 w-20" />
                <Skeleton className="h-7 w-24" />
                <Skeleton className="h-3 w-28" />
              </Card>
            ))}
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Card className="h-64 p-4 border border-border bg-surface">
              <Skeleton className="h-full w-full" />
            </Card>
            <Card className="h-64 p-4 border border-border bg-surface">
              <Skeleton className="h-full w-full" />
            </Card>
          </div>
        </div>
      ) : (
        <>
          {/* ── Core Evidence Metrics ── */}
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <MetricCard
              label="Total Predictions"
              value={data.total_predictions.toLocaleString()}
              subtitle="Evaluated specimen slides"
            />
            <MetricCard
              label="Pipeline Reliability"
              value={`${data.success_rate.toFixed(1)}%`}
              subtitle="Inference completion rate"
            />
            <MetricCard
              label="Avg. Confidence"
              value={`${data.average_confidence}%`}
              subtitle="Posterior probability"
            />
            <MetricCard
              label="Avg. Agreement"
              value={`${Math.round(data.average_agreement_ratio * 100)}%`}
              subtitle="Cross-architecture consensus"
            />
          </div>

          {/* ── Distributions ── */}
          <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
            {/* Histopathological Class Distribution */}
            <Card className="space-y-4 border border-border bg-surface">
              <div className="flex items-center justify-between border-b border-border pb-3">
                <div className="flex items-center gap-2">
                  <Layers className="h-4 w-4 text-primary" />
                  <h3 className="text-sm font-semibold text-text-primary">
                    Histopathological Class Distribution
                  </h3>
                </div>
                <Badge variant="outline" className="font-mono text-[10px] text-text-muted">
                  Categorical
                </Badge>
              </div>

              {Object.keys(data.class_distribution).length === 0 ? (
                <p className="text-xs text-text-muted py-6 text-center font-mono">
                  No computational evaluations recorded yet.
                </p>
              ) : (
                <DistributionBars
                  distribution={data.class_distribution}
                  colorFor={getClassLabelColor}
                  formatLabel={formatClassLabel}
                />
              )}

              {data.most_predicted_class && (
                <div className="pt-3 border-t border-border flex items-center justify-between text-xs">
                  <span className="text-text-muted">Predominant Classification:</span>
                  <Badge
                    variant={getDiseaseBadgeVariant(data.most_predicted_class)}
                    className="font-semibold text-[11px]"
                  >
                    {formatClassLabel(data.most_predicted_class)}
                  </Badge>
                </div>
              )}
            </Card>

            {/* Ensemble Confidence Distribution */}
            <Card className="space-y-4 border border-border bg-surface">
              <div className="flex items-center justify-between border-b border-border pb-3">
                <div className="flex items-center gap-2">
                  <BarChart3 className="h-4 w-4 text-primary" />
                  <h3 className="text-sm font-semibold text-text-primary">
                    Ensemble Confidence Distribution
                  </h3>
                </div>
                <Badge variant="outline" className="font-mono text-[10px] text-text-muted">
                  Binned
                </Badge>
              </div>

              {Object.keys(data.confidence_distribution).length === 0 ? (
                <p className="text-xs text-text-muted py-6 text-center font-mono">
                  No confidence statistics calculated yet.
                </p>
              ) : (
                <DistributionBars
                  distribution={data.confidence_distribution}
                  colorFor={() => 'var(--color-primary)'}
                />
              )}

              <p className="text-[11px] text-text-muted pt-3 border-t border-border">
                Confidence reflects model prediction probability distribution across all completed analyses.
              </p>
            </Card>
          </div>

          {/* ── Activity Windows & Temporal Range ── */}
          <Card className="border border-border bg-surface p-4">
            <div className="flex items-center gap-2 mb-3 pb-2 border-b border-border-subtle">
              <Calendar className="h-3.5 w-3.5 text-text-muted" />
              <h4 className="text-xs font-semibold uppercase tracking-wider font-mono text-text-secondary">
                Temporal Activity &amp; Archival Boundaries
              </h4>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
              <TimeStat label="Today" value={data.predictions_today} />
              <TimeStat label="This Week" value={data.predictions_this_week} />
              <TimeStat label="This Month" value={data.predictions_this_month} />
              {data.first_prediction_date && (
                <TimeStat
                  label="Earliest Evaluation"
                  value={formatDateTime(data.first_prediction_date)}
                  isText
                />
              )}
              {data.latest_prediction_date && (
                <TimeStat
                  label="Latest Evaluation"
                  value={formatDateTime(data.latest_prediction_date)}
                  isText
                />
              )}
            </div>
          </Card>

          {/* ── Provenance Telemetry ── */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 text-[11px] font-mono text-text-muted pt-1">
            <span className="flex items-center gap-1.5">
              <Activity className="h-3 w-3 text-primary" />
              Generated {formatDateTime(data.generated_at)}
            </span>
            <span className="truncate">
              Telemetry Snapshot: {data.analytics_id}
            </span>
          </div>
        </>
      )}
    </div>
  );
}

function MetricCard({
  label,
  value,
  subtitle,
}: {
  label: string;
  value: string;
  subtitle: string;
}) {
  return (
    <Card className="space-y-1 p-4 border border-border bg-surface">
      <p className="text-[10px] uppercase tracking-wider text-text-muted font-mono">{label}</p>
      <p className="text-xl sm:text-2xl font-bold font-mono tabular-nums text-text-primary mt-1">
        {value}
      </p>
      <p className="text-[10px] text-text-muted">{subtitle}</p>
    </Card>
  );
}

function TimeStat({
  label,
  value,
  isText = false,
}: {
  label: string;
  value: number | string;
  isText?: boolean;
}) {
  return (
    <div className="space-y-0.5">
      <p className="text-[10px] uppercase tracking-wider text-text-muted font-mono">{label}</p>
      <p
        className={
          isText
            ? 'text-xs font-mono font-medium text-text-primary truncate'
            : 'text-base sm:text-lg font-bold font-mono tabular-nums text-text-primary'
        }
      >
        {value}
      </p>
    </div>
  );
}

function DistributionBars({
  distribution,
  colorFor,
  formatLabel,
}: {
  distribution: Record<string, number>;
  colorFor: (key: string) => string;
  formatLabel?: (key: string) => string;
}) {
  const entries = Object.entries(distribution);
  const max = Math.max(...entries.map(([, v]) => v), 1);
  return (
    <div className="space-y-3">
      {entries.map(([key, count]) => {
        const displayLabel = formatLabel ? formatLabel(key) : key;
        const color = colorFor(key);
        const percent = Math.round((count / max) * 100);

        return (
          <div key={key} className="space-y-1.5">
            <div className="flex items-center justify-between text-xs">
              <span className="font-medium text-text-primary truncate">{displayLabel}</span>
              <span className="font-mono tabular-nums text-text-muted text-[11px]">
                {count} {count === 1 ? 'case' : 'cases'}
              </span>
            </div>
            <div className="h-2 w-full rounded-full bg-surface-raised overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-300"
                style={{
                  width: `${percent}%`,
                  backgroundColor: color,
                }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
