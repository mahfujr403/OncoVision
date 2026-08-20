import { Server, Cpu, Activity, Database } from 'lucide-react';
import { SectionTitle } from '@/components/ui/SectionTitle';
import { Card, CardHeader, CardTitle, CardContent, StatCard } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { ErrorState } from '@/components/ui/ErrorState';
import { Skeleton } from '@/components/ui/Skeleton';
import { useMonitoring } from '@/hooks/queries/useMonitoring';
import { formatDateTime } from '@/utils/formatters';
import type { ComponentStatus } from '@/types';

// NOTE: the previous version of this page showed a fabricated service list
// (API Gateway, Notification Service, PostgreSQL latencies...) and fake
// CPU/Memory/GPU gauges — none of that exists on the backend. This page now
// reflects only what GET /api/v1/monitoring actually returns (verified
// against app/schemas/monitoring.py): application/database/runtime health,
// per-model runtime state, and request/prediction metrics. There is no
// GPU/CPU/memory utilization endpoint, so those gauges are gone rather than
// invented.
export default function AdminSystemHealthPage() {
  const { data, isLoading, isError, refetch } = useMonitoring();

  return (
    <div className="space-y-5">
      <SectionTitle
        title="System Health"
        description="Live status from the AI runtime and application monitoring endpoint"
        action={data && <StatusBadge status={data.status} />}
      />

      {isError ? (
        <ErrorState message="Couldn't load monitoring status." onRetry={() => refetch()} />
      ) : isLoading || !data ? (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Card key={i} className="space-y-2">
              <Skeleton className="h-3 w-20" />
              <Skeleton className="h-6 w-14" />
            </Card>
          ))}
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <StatCard
              label="Loaded Models"
              value={`${data.runtime.loaded_model_count}/${data.runtime.total_model_count}`}
              icon={<Cpu className="h-4 w-4" />}
            />
            <StatCard
              label="Total Requests"
              value={data.request_metrics.total_requests.toLocaleString()}
              icon={<Activity className="h-4 w-4" />}
            />
            <StatCard
              label="Avg. Request Time"
              value={`${data.request_metrics.average_duration_ms.toFixed(0)} ms`}
              icon={<Server className="h-4 w-4" />}
            />
            <StatCard
              label="Prediction Requests"
              value={`${data.prediction_metrics.successful_requests}/${data.prediction_metrics.total_requests}`}
              icon={<Database className="h-4 w-4" />}
            />
          </div>

          {/* Component health */}
          <Card>
            <CardHeader>
              <CardTitle>Component Status</CardTitle>
            </CardHeader>
            <CardContent className="divide-y divide-border">
              <ComponentRow
                name={data.application.name}
                detail={`v${data.application.version} · ${data.application.environment}`}
                status={data.application.status}
              />
              <ComponentRow
                name="Database"
                detail={data.database.connected ? 'Connected' : 'Not connected'}
                status={data.database.status}
              />
              <ComponentRow
                name="AI Runtime"
                detail={`${data.runtime.loaded_model_count} loaded · ${data.runtime.failed_model_count} failed · ${data.runtime.pending_model_count} pending`}
                status={data.runtime.status}
              />
            </CardContent>
          </Card>

          {/* Per-model runtime status */}
          <Card>
            <CardHeader>
              <CardTitle>Model Runtime</CardTitle>
            </CardHeader>
            <CardContent className="divide-y divide-border">
              {data.runtime.models.length === 0 ? (
                <p className="py-3 text-xs text-muted-foreground">No models registered.</p>
              ) : (
                data.runtime.models.map((m) => (
                  <div key={m.model_id} className="flex items-center gap-4 py-3">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-muted">
                      <Cpu className="h-4 w-4 text-muted-foreground" />
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium">{m.display_name}</p>
                      <p className="text-xs text-muted-foreground">
                        {m.error_message ?? `State: ${m.state}`}
                      </p>
                    </div>
                    <Badge variant={m.is_available ? 'success' : 'destructive'} dot className="text-[10px] capitalize">
                      {m.state}
                    </Badge>
                  </div>
                ))
              )}
            </CardContent>
          </Card>

          {/* Request breakdown */}
          <Card className="space-y-3">
            <p className="text-sm font-semibold">HTTP Response Breakdown</p>
            <div className="grid grid-cols-4 gap-3 text-center">
              <ResponseStat label="2xx" value={data.request_metrics.status_2xx} tone="success" />
              <ResponseStat label="3xx" value={data.request_metrics.status_3xx} tone="secondary" />
              <ResponseStat label="4xx" value={data.request_metrics.status_4xx} tone="warning" />
              <ResponseStat label="5xx" value={data.request_metrics.status_5xx} tone="destructive" />
            </div>
          </Card>

          <p className="text-[11px] text-muted-foreground">Generated {formatDateTime(data.generated_at)}</p>
        </>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: ComponentStatus }) {
  const variant = status === 'healthy' ? 'success' : status === 'degraded' ? 'warning' : 'destructive';
  const label =
    status === 'healthy' ? 'All systems operational' : status === 'degraded' ? 'Degraded performance' : 'Service disruption';
  return (
    <Badge variant={variant} dot>
      {label}
    </Badge>
  );
}

function ComponentRow({ name, detail, status }: { name: string; detail: string; status: ComponentStatus }) {
  return (
    <div className="flex items-center gap-4 py-3">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-muted">
        <Server className="h-4 w-4 text-muted-foreground" />
      </div>
      <div className="flex-1">
        <p className="text-sm font-medium">{name}</p>
        <p className="text-xs text-muted-foreground">{detail}</p>
      </div>
      <Badge variant={status === 'healthy' ? 'success' : status === 'degraded' ? 'warning' : 'destructive'} dot className="text-[10px] capitalize">
        {status}
      </Badge>
    </div>
  );
}

function ResponseStat({ label, value, tone }: { label: string; value: number; tone: 'success' | 'secondary' | 'warning' | 'destructive' }) {
  return (
    <div className="space-y-0.5">
      <p className="text-lg font-bold font-display">{value}</p>
      <Badge variant={tone} className="text-[10px]">
        {label}
      </Badge>
    </div>
  );
}
