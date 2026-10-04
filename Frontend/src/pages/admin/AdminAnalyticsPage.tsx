import { Users, Microscope, TrendingUp, CheckCircle, XCircle, Clock, ShieldCheck, Database } from 'lucide-react';
import { StatCard, Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { SectionTitle } from '@/components/ui/SectionTitle';
import { Badge } from '@/components/ui/Badge';
import { ErrorState } from '@/components/ui/ErrorState';
import { Skeleton } from '@/components/ui/Skeleton';
import { useAdminAnalytics } from '@/hooks/queries/useAdminHistory';
import { useAdminUsers } from '@/hooks/queries/useAdminUsers';
import { useMonitoring } from '@/hooks/queries/useMonitoring';
import { formatDateTime } from '@/utils/formatters';

function getDiseaseClassColor(label: string): string {
  const norm = label.toLowerCase();
  if (norm.includes('lung') && (norm.includes('adeno') || norm.includes('aca'))) return 'var(--color-class-lung-aca)';
  if (norm.includes('lung') && (norm.includes('squamous') || norm.includes('scc'))) return 'var(--color-class-lung-scc)';
  if (norm.includes('colon') && (norm.includes('adeno') || norm.includes('aca'))) return 'var(--color-class-colon-aca)';
  if (norm.includes('lung') && norm.includes('benign')) return 'var(--color-class-lung-benign)';
  if (norm.includes('colon') && norm.includes('benign')) return 'var(--color-class-colon-benign)';
  return 'var(--color-text-muted)';
}

export default function AdminAnalyticsPage() {
  const analytics = useAdminAnalytics();
  const users = useAdminUsers({ page: 1, page_size: 1 });
  const monitoring = useMonitoring();

  const isLoading = analytics.isLoading || users.isLoading || monitoring.isLoading;
  const isError = analytics.isError || users.isError || monitoring.isError;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <SectionTitle
          title="Platform Analytics"
          description="Operational telemetry, platform inference volume, and histopathological classification evidence."
        />
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="font-mono text-xs px-2.5 py-1">
            <span className="inline-block h-2 w-2 rounded-full bg-success mr-1.5" />
            <span className="text-text-muted">Provenance:</span>
            <span className="ml-1 font-semibold text-text-primary">Production Telemetry</span>
          </Badge>
        </div>
      </div>

      {isError ? (
        <ErrorState
          message="Could not load platform analytics from the reporting service."
          onRetry={() => {
            analytics.refetch();
            users.refetch();
            monitoring.refetch();
          }}
        />
      ) : isLoading || !analytics.data ? (
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Card key={i} className="space-y-2 p-4">
                <Skeleton className="h-3 w-20" />
                <Skeleton className="h-6 w-16" />
              </Card>
            ))}
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            <Skeleton className="h-48 w-full rounded-lg" />
            <Skeleton className="h-48 w-full rounded-lg" />
          </div>
        </div>
      ) : (
        <>
          {/* Key Platform Scale Indicators */}
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <StatCard
              label="Registered Accounts"
              value={users.data ? String(users.data.pagination.total_records) : '—'}
              icon={<Users className="h-4 w-4" />}
            />
            <StatCard
              label="Diagnostic Evaluations"
              value={analytics.data.total_predictions.toLocaleString()}
              icon={<Microscope className="h-4 w-4" />}
            />
            <StatCard
              label="Mean Model Confidence"
              value={`${analytics.data.average_confidence}%`}
              icon={<TrendingUp className="h-4 w-4" />}
            />
            <StatCard
              label="Mean Ensemble Concordance"
              value={
                analytics.data.average_agreement_ratio != null
                  ? `${Math.round(analytics.data.average_agreement_ratio * 100)}%`
                  : '—'
              }
              icon={<ShieldCheck className="h-4 w-4" />}
            />
          </div>

          {/* Temporal Inference Volume Card */}
          <Card className="p-5">
            <CardHeader className="p-0 pb-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Clock className="h-4 w-4 text-primary" />
                  <CardTitle className="text-sm">Inference Throughput &amp; Temporal Volume</CardTitle>
                </div>
                <span className="text-xs font-mono text-text-muted">
                  Active Period Tracking
                </span>
              </div>
            </CardHeader>
            <CardContent className="p-0 pt-2 grid grid-cols-2 sm:grid-cols-4 gap-4">
              <PeriodMetric label="Evaluations Today" value={analytics.data.predictions_today} />
              <PeriodMetric label="Evaluations This Week" value={analytics.data.predictions_this_week} />
              <PeriodMetric label="Evaluations This Month" value={analytics.data.predictions_this_month} />
              <div className="p-3 rounded-lg border border-border bg-surface-raised/40">
                <span className="text-[10px] uppercase tracking-wider font-mono text-text-muted block">
                  Pipeline Success Rate
                </span>
                <span className="text-xl font-bold font-mono tabular-nums text-text-primary mt-1 block">
                  {analytics.data.success_rate.toFixed(1)}%
                </span>
                <span className="text-[10px] text-text-muted mt-0.5 block">
                  {analytics.data.successful_predictions} of {analytics.data.total_predictions} executions
                </span>
              </div>
            </CardContent>
          </Card>

          {/* Classification Distribution & Operational Reliability */}
          <div className="grid md:grid-cols-2 gap-5">
            {/* Finding Distribution */}
            <Card className="p-5 flex flex-col justify-between">
              <div>
                <CardHeader className="p-0 pb-4 border-b border-border">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-sm">Histopathological Finding Distribution</CardTitle>
                    {analytics.data.most_predicted_class && (
                      <Badge variant="secondary" className="text-[10px]">
                        Modal: {analytics.data.most_predicted_class}
                      </Badge>
                    )}
                  </div>
                </CardHeader>
                <CardContent className="p-0 pt-4 space-y-3.5">
                  {Object.keys(analytics.data.class_distribution).length === 0 ? (
                    <p className="text-xs text-text-muted py-4 text-center font-mono">
                      No classification evaluations recorded in platform history.
                    </p>
                  ) : (
                    Object.entries(analytics.data.class_distribution).map(([label, count]) => {
                      const total = analytics.data!.total_predictions || 1;
                      const pct = (count / total) * 100;
                      const color = getDiseaseClassColor(label);

                      return (
                        <div key={label} className="space-y-1.5">
                          <div className="flex items-center justify-between text-xs">
                            <span className="font-medium text-text-primary truncate max-w-[220px]" title={label}>
                              {label}
                            </span>
                            <span className="font-mono text-xs tabular-nums text-text-muted shrink-0">
                              <span className="font-semibold text-text-primary">{count.toLocaleString()}</span>{' '}
                              <span className="text-[11px]">({pct.toFixed(1)}%)</span>
                            </span>
                          </div>
                          <div className="h-2 w-full rounded-full bg-surface-raised overflow-hidden border border-border-subtle">
                            <div
                              className="h-full rounded-full transition-all duration-300"
                              style={{ width: `${Math.max(pct, 1)}%`, backgroundColor: color }}
                            />
                          </div>
                        </div>
                      );
                    })
                  )}
                </CardContent>
              </div>
            </Card>

            {/* Operational Pipeline Reliability */}
            <Card className="p-5 flex flex-col justify-between">
              <div>
                <CardHeader className="p-0 pb-4 border-b border-border">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-sm">Pipeline Execution &amp; Reliability</CardTitle>
                    <Badge variant="outline" className="font-mono text-[10px]">
                      Operational Metrics
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="p-0 pt-4 space-y-4">
                  <div className="grid grid-cols-2 gap-3">
                    <div className="p-3 rounded-lg border border-border bg-surface-raised/40 space-y-1">
                      <div className="flex items-center gap-1.5 text-xs text-success">
                        <CheckCircle className="h-3.5 w-3.5" />
                        <span className="font-medium">Completed</span>
                      </div>
                      <span className="text-xl font-bold font-mono tabular-nums text-text-primary block">
                        {analytics.data.successful_predictions.toLocaleString()}
                      </span>
                      <span className="text-[10px] text-text-muted block">Valid ensemble inference</span>
                    </div>

                    <div className="p-3 rounded-lg border border-border bg-surface-raised/40 space-y-1">
                      <div className="flex items-center gap-1.5 text-xs text-error">
                        <XCircle className="h-3.5 w-3.5" />
                        <span className="font-medium">Failed</span>
                      </div>
                      <span className="text-xl font-bold font-mono tabular-nums text-text-primary block">
                        {analytics.data.failed_predictions.toLocaleString()}
                      </span>
                      <span className="text-[10px] text-text-muted block">Execution faults or timeouts</span>
                    </div>
                  </div>

                  <div className="space-y-2 pt-2 border-t border-border-subtle text-xs font-mono">
                    <div className="flex items-center justify-between py-1">
                      <span className="text-text-muted">Active Runtime Models:</span>
                      <span className="text-text-primary font-semibold">
                        {monitoring.data
                          ? `${monitoring.data.runtime.loaded_model_count} of ${monitoring.data.runtime.total_model_count} loaded`
                          : '—'}
                      </span>
                    </div>
                    <div className="flex items-center justify-between py-1">
                      <span className="text-text-muted">Earliest Recorded Case:</span>
                      <span className="text-text-secondary">
                        {analytics.data.first_prediction_date ? formatDateTime(analytics.data.first_prediction_date) : 'None'}
                      </span>
                    </div>
                    <div className="flex items-center justify-between py-1">
                      <span className="text-text-muted">Latest Evaluation Logged:</span>
                      <span className="text-text-secondary">
                        {analytics.data.latest_prediction_date ? formatDateTime(analytics.data.latest_prediction_date) : 'None'}
                      </span>
                    </div>
                  </div>
                </CardContent>
              </div>

              {/* Confidence Stratification if available */}
              {analytics.data.confidence_distribution && Object.keys(analytics.data.confidence_distribution).length > 0 && (
                <div className="pt-4 border-t border-border mt-4">
                  <span className="text-[10px] uppercase font-mono text-text-muted tracking-wider block mb-2">
                    Confidence Stratification
                  </span>
                  <div className="grid grid-cols-3 gap-2">
                    {Object.entries(analytics.data.confidence_distribution).map(([bucket, count]) => (
                      <div key={bucket} className="p-2 rounded bg-surface-raised border border-border-subtle text-center">
                        <span className="text-[10px] text-text-muted block font-mono capitalize">{bucket}</span>
                        <span className="font-mono text-xs font-semibold text-text-primary tabular-nums">
                          {count}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </Card>
          </div>

          {/* Evidence Methodology & Provenance Notice */}
          <div className="flex items-start gap-3 p-4 rounded-lg border border-border bg-surface-raised/40 text-xs text-text-secondary">
            <Database className="h-4 w-4 text-text-muted shrink-0 mt-0.5" />
            <div className="space-y-1">
              <p className="font-semibold text-text-primary">Data Provenance &amp; Statistical Context</p>
              <p className="leading-relaxed">
                All metrics on this page represent production-derived operational aggregations from platform inference logs
                (endpoint <code className="font-mono text-[11px] bg-secondary px-1 py-0.5 rounded">/api/v1/admin/analytics</code>)
                and active system health monitoring. Class distribution reflects raw model outputs and does not represent an epidemiological prevalence study.
              </p>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function PeriodMetric({ label, value }: { label: string; value: number }) {
  return (
    <div className="p-3 rounded-lg border border-border bg-surface-raised/40">
      <span className="text-[10px] uppercase tracking-wider font-mono text-text-muted block">{label}</span>
      <span className="text-xl font-bold font-mono tabular-nums text-text-primary mt-1 block">
        {value.toLocaleString()}
      </span>
      <span className="text-[10px] text-text-muted mt-0.5 block">Cross-account volume</span>
    </div>
  );
}
