import { Server, Cpu, Activity, Database, RefreshCw, CheckCircle2, AlertTriangle, XCircle, Info, HardDrive } from 'lucide-react';
import { SectionTitle } from '@/components/ui/SectionTitle';
import { Card, CardHeader, CardTitle, CardContent, StatCard } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { ErrorState } from '@/components/ui/ErrorState';
import { Skeleton } from '@/components/ui/Skeleton';
import { useMonitoring } from '@/hooks/queries/useMonitoring';
import { formatDateTime } from '@/utils/formatters';
import type { ComponentStatus } from '@/types';

export default function AdminSystemHealthPage() {
  const { data, isLoading, isError, refetch, isFetching } = useMonitoring();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <SectionTitle
          title="System Health"
          description="Live operational telemetry, inference engine state, and backend service monitoring."
        />
        <div className="flex items-center gap-2">
          {data && <OverallStatusBadge status={data.status} />}
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isFetching}
            className="gap-1.5 text-xs"
            aria-label="Refresh system health telemetry"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isFetching ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </Button>
        </div>
      </div>

      {isError ? (
        <ErrorState message="Could not retrieve monitoring telemetry from backend services." onRetry={() => refetch()} />
      ) : isLoading || !data ? (
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Card key={i} className="space-y-2 p-4">
                <Skeleton className="h-3 w-24" />
                <Skeleton className="h-6 w-16" />
              </Card>
            ))}
          </div>
          <Card className="p-6 space-y-4">
            <Skeleton className="h-5 w-40" />
            <div className="space-y-3">
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
            </div>
          </Card>
        </div>
      ) : (
        <>
          {/* Top Operational Metrics */}
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <StatCard
              label="Loaded Models"
              value={`${data.runtime.loaded_model_count}/${data.runtime.total_model_count}`}
              icon={<Cpu className="h-4 w-4" />}
            />
            <StatCard
              label="Total HTTP Requests"
              value={data.request_metrics.total_requests.toLocaleString()}
              icon={<Activity className="h-4 w-4" />}
            />
            <StatCard
              label="Mean Response Latency"
              value={`${data.request_metrics.average_duration_ms.toFixed(0)} ms`}
              icon={<Server className="h-4 w-4" />}
            />
            <StatCard
              label="Inference Throughput"
              value={`${data.prediction_metrics.successful_requests}/${data.prediction_metrics.total_requests}`}
              icon={<Database className="h-4 w-4" />}
            />
          </div>

          {/* Core Infrastructure Components */}
          <Card className="p-5">
            <CardHeader className="p-0 pb-3 border-b border-border">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Server className="h-4 w-4 text-primary" />
                  <CardTitle className="text-sm">Core Service Infrastructure</CardTitle>
                </div>
                <span className="text-xs font-mono text-text-muted">
                  Service Level Health
                </span>
              </div>
            </CardHeader>
            <CardContent className="p-0 pt-1 divide-y divide-border-subtle">
              <ComponentRow
                icon={<HardDrive className="h-4 w-4 text-text-muted" />}
                name={data.application.name}
                detail={`Build v${data.application.version} · Environment: ${data.application.environment}`}
                status={data.application.status}
              />
              <ComponentRow
                icon={<Database className="h-4 w-4 text-text-muted" />}
                name="PostgreSQL Database"
                detail={data.database.connected ? 'Active connection pool verified' : 'Database connection pool disconnected'}
                status={data.database.status}
              />
              <ComponentRow
                icon={<Cpu className="h-4 w-4 text-text-muted" />}
                name="Inference Runtime Engine"
                detail={`${data.runtime.loaded_model_count} active in memory · ${data.runtime.pending_model_count} pending · ${data.runtime.failed_model_count} faults`}
                status={data.runtime.status}
              />
            </CardContent>
          </Card>

          {/* Model Runtime Daemon State */}
          <Card className="p-5">
            <CardHeader className="p-0 pb-3 border-b border-border">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Cpu className="h-4 w-4 text-primary" />
                  <CardTitle className="text-sm">Runtime Estimator Daemon Instances</CardTitle>
                </div>
                <span className="text-xs font-mono text-text-muted">
                  {data.runtime.models.length} registered processes
                </span>
              </div>
            </CardHeader>
            <CardContent className="p-0 pt-1 divide-y divide-border-subtle">
              {data.runtime.models.length === 0 ? (
                <p className="py-4 text-xs font-mono text-text-muted text-center">
                  No individual model processes are currently reported by the runtime manager.
                </p>
              ) : (
                data.runtime.models.map((m) => (
                  <div key={m.model_id} className="flex items-center justify-between gap-4 py-3.5">
                    <div className="flex items-center gap-3">
                      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-surface-raised border border-border text-primary">
                        <Cpu className="h-4 w-4" />
                      </div>
                      <div className="min-w-0">
                        <p className="text-xs font-semibold text-text-primary truncate">{m.display_name}</p>
                        <p className="text-[11px] text-text-muted font-mono truncate">
                          {m.error_message ? (
                            <span className="text-error">{m.error_message}</span>
                          ) : (
                            `Daemon Process ID: ${m.model_id}`
                          )}
                        </p>
                      </div>
                    </div>
                    <Badge
                      variant={m.is_available ? 'success' : 'error'}
                      dot
                      className="text-[10px] capitalize font-mono shrink-0"
                    >
                      {m.state}
                    </Badge>
                  </div>
                ))
              )}
            </CardContent>
          </Card>

          {/* HTTP Gateway Breakdown */}
          <Card className="p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2">
                <Activity className="h-4 w-4 text-primary" />
                <h3 className="text-sm font-semibold text-text-primary">Gateway HTTP Status Distribution</h3>
              </div>
              <span className="text-xs font-mono text-text-muted">
                Cumulative Session Volume
              </span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <ResponseStat label="2xx Success" value={data.request_metrics.status_2xx} tone="success" desc="Normal operational requests" />
              <ResponseStat label="3xx Redirect" value={data.request_metrics.status_3xx} tone="secondary" desc="Route redirects" />
              <ResponseStat label="4xx Client Error" value={data.request_metrics.status_4xx} tone="warning" desc="Auth, 404, or validation faults" />
              <ResponseStat label="5xx Server Error" value={data.request_metrics.status_5xx} tone="destructive" desc="Runtime or internal faults" />
            </div>
          </Card>

          {/* Telemetry Provenance Notice & Timestamp */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 p-4 rounded-lg border border-border bg-surface-raised/40 text-xs text-text-secondary">
            <div className="flex items-start gap-2.5">
              <Info className="h-4 w-4 text-text-muted shrink-0 mt-0.5" />
              <p>
                Telemetry polled from backend health daemon (<code className="font-mono text-[11px] bg-secondary px-1 py-0.5 rounded">/api/v1/monitoring/status</code>).
                Statuses represent factual connectivity and response codes.
              </p>
            </div>
            <span className="font-mono text-[11px] text-text-muted shrink-0">
              Sampled: {formatDateTime(data.generated_at)}
            </span>
          </div>
        </>
      )}
    </div>
  );
}

function OverallStatusBadge({ status }: { status: ComponentStatus }) {
  if (status === 'healthy') {
    return (
      <Badge variant="success" dot className="text-xs font-mono px-2.5 py-1">
        <CheckCircle2 className="h-3 w-3 mr-1" />
        All Systems Operational
      </Badge>
    );
  }
  if (status === 'degraded') {
    return (
      <Badge variant="warning" dot className="text-xs font-mono px-2.5 py-1">
        <AlertTriangle className="h-3 w-3 mr-1" />
        Degraded Performance
      </Badge>
    );
  }
  if (status === 'down') {
    return (
      <Badge variant="error" dot className="text-xs font-mono px-2.5 py-1">
        <XCircle className="h-3 w-3 mr-1" />
        Service Disruption
      </Badge>
    );
  }
  return (
    <Badge variant="secondary" dot className="text-xs font-mono px-2.5 py-1">
      Operational State Unknown
    </Badge>
  );
}

function ComponentRow({
  icon,
  name,
  detail,
  status,
}: {
  icon: React.ReactNode;
  name: string;
  detail: string;
  status: ComponentStatus;
}) {
  const variant = status === 'healthy' ? 'success' : status === 'degraded' ? 'warning' : 'error';
  const label = status === 'healthy' ? 'Operational' : status === 'degraded' ? 'Degraded' : 'Unavailable';

  return (
    <div className="flex items-center justify-between gap-4 py-3.5">
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-surface-raised border border-border">
          {icon}
        </div>
        <div className="min-w-0">
          <p className="text-xs font-semibold text-text-primary">{name}</p>
          <p className="text-[11px] text-text-muted font-mono">{detail}</p>
        </div>
      </div>
      <Badge variant={variant} dot className="text-[10px] font-mono shrink-0">
        {label}
      </Badge>
    </div>
  );
}

function ResponseStat({
  label,
  value,
  tone,
  desc,
}: {
  label: string;
  value: number;
  tone: 'success' | 'secondary' | 'warning' | 'destructive';
  desc: string;
}) {
  return (
    <div className="p-3.5 rounded-lg border border-border bg-surface-raised/40 space-y-1">
      <div className="flex items-center justify-between">
        <Badge variant={tone} className="text-[10px] font-mono">
          {label}
        </Badge>
      </div>
      <p className="text-xl font-bold font-mono tabular-nums text-text-primary pt-1">
        {value.toLocaleString()}
      </p>
      <p className="text-[10px] text-text-muted leading-tight">{desc}</p>
    </div>
  );
}
