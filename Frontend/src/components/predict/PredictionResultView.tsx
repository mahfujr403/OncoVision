import { AlertTriangle, XCircle, Cpu, Clock, Layers } from 'lucide-react';
import { Card, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { ErrorState } from '@/components/ui/ErrorState';
import type { ApiErrorEnvelope, PredictionResponse } from '@/types/prediction';
import { isApiErrorEnvelope } from '@/lib/mockPrediction';

function formatClassLabel(raw: string): string {
  if (!raw) return '—';
  return raw
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

function StatChip({ label, value, tone }: { label: string; value: string | number; tone?: 'success' | 'destructive' | 'default' }) {
  const toneClass =
    tone === 'success' ? 'text-success' : tone === 'destructive' ? 'text-destructive' : 'text-foreground';
  return (
    <div className="rounded-md border border-border bg-muted/20 px-3 py-2 min-w-[104px]">
      <p className="text-[10px] text-muted-foreground uppercase tracking-wide font-mono">{label}</p>
      <p className={`text-sm font-semibold mt-0.5 ${toneClass}`}>{value}</p>
    </div>
  );
}

function RuntimeStatusBadge({ status }: { status: string }) {
  const normalized = status.toLowerCase();
  if (normalized === 'operational') return <Badge variant="success" dot>Operational</Badge>;
  if (normalized === 'degraded') return <Badge variant="warning" dot>Degraded</Badge>;
  return <Badge variant="offline" dot>{status}</Badge>;
}

interface PredictionResultViewProps {
  response: PredictionResponse;
  onStartNew: () => void;
}

export function PredictionResultView({ response, onStartNew }: PredictionResultViewProps) {
  const { status, result, individual_predictions, runtime_statistics, metadata } = response;
  const isPartial = status === 'partial_success';
  const isFailed = status === 'failed' || status === 'pending';

  if (isFailed) {
    return (
      <Card>
        <ErrorState
          variant="full"
          title="No prediction available"
          message={response.message || 'All participating models failed to produce a prediction.'}
          onRetry={onStartNew}
        />
      </Card>
    );
  }

  return (
    <div className="space-y-5">
      <Card>
        {isPartial && (
          <div className="flex items-start gap-2.5 mb-5 p-3 rounded-md bg-warning/10 border border-warning/30">
            <AlertTriangle className="w-4 h-4 text-warning mt-0.5 shrink-0" />
            <p className="text-sm text-warning font-medium">
              Partial result — only one model completed. No ensemble agreement is available.
            </p>
          </div>
        )}

        <div className="flex items-start justify-between gap-4 mb-6">
          <div>
            <p className="text-xs text-muted-foreground uppercase tracking-widest font-mono mb-1.5">
              Predicted Class
            </p>
            <h2 className="text-2xl font-bold text-foreground">{formatClassLabel(result.prediction)}</h2>
          </div>
          <Badge variant={isPartial ? 'warning' : 'success'} dot>
            {isPartial ? 'Partial Success' : 'Success'}
          </Badge>
        </div>

        <div className="grid grid-cols-2 gap-5 mb-6">
          <div>
            <p className="text-xs text-muted-foreground uppercase tracking-wide font-mono mb-2">
              Model Confidence
            </p>
            <div className="flex items-end gap-2">
              <span className="text-3xl font-bold text-foreground">{result.confidence.toFixed(1)}%</span>
            </div>
            <div className="w-full h-1.5 rounded-full bg-muted mt-2 overflow-hidden">
              <div
                className="h-full bg-primary rounded-full"
                style={{ width: `${Math.min(100, Math.max(0, result.confidence))}%` }}
              />
            </div>
          </div>
          <div className={isPartial ? 'opacity-40' : ''}>
            <p className="text-xs text-muted-foreground uppercase tracking-wide font-mono mb-2">
              Model Agreement
            </p>
            <div className="flex items-end gap-2">
              <span className="text-3xl font-bold text-foreground">
                {isPartial ? '—' : `${Math.round(result.agreement_ratio * 100)}%`}
              </span>
            </div>
            {!isPartial && (
              <div className="w-full h-1.5 rounded-full bg-muted mt-2 overflow-hidden">
                <div
                  className="h-full bg-accent rounded-full"
                  style={{ width: `${Math.round(result.agreement_ratio * 100)}%` }}
                />
              </div>
            )}
          </div>
        </div>

        <div className="flex flex-wrap gap-3">
          <StatChip label="Participating" value={result.participating_models} />
          <StatChip label="Successful" value={result.successful_models.length} tone="success" />
          <StatChip
            label="Failed"
            value={result.failed_models.length}
            tone={result.failed_models.length > 0 ? 'destructive' : 'default'}
          />
        </div>
      </Card>

      {individual_predictions && individual_predictions.length > 0 && (
        <Card padding="none">
          <div className="flex items-center gap-2 px-5 py-4 border-b border-border">
            <Layers className="w-4 h-4 text-muted-foreground" />
            <h3 className="text-sm font-semibold text-foreground">Individual Model Predictions</h3>
            <Badge variant="outline" className="ml-auto">
              Per-model — not the final result
            </Badge>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[11px] text-muted-foreground uppercase tracking-wide font-mono border-b border-border">
                  <th className="px-5 py-2.5 font-medium">Model</th>
                  <th className="px-5 py-2.5 font-medium">Prediction</th>
                  <th className="px-5 py-2.5 font-medium">Confidence</th>
                  <th className="px-5 py-2.5 font-medium">Inference Time</th>
                </tr>
              </thead>
              <tbody>
                {individual_predictions.map((p) => (
                  <tr key={p.model_name} className="border-b border-border last:border-0">
                    <td className="px-5 py-3 font-mono text-xs text-foreground">{p.model_name}</td>
                    <td className="px-5 py-3 text-foreground">{formatClassLabel(p.prediction)}</td>
                    <td className="px-5 py-3 text-foreground">{p.confidence.toFixed(1)}%</td>
                    <td className="px-5 py-3 text-muted-foreground font-mono text-xs">
                      {p.inference_time_ms} ms
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {runtime_statistics && (
        <Card>
          <CardHeader>
            <CardTitle>Runtime Statistics</CardTitle>
            <RuntimeStatusBadge status={runtime_statistics.runtime_status} />
          </CardHeader>

          <div className="flex flex-wrap gap-2 mb-4">
            {runtime_statistics.loaded_models.map((m) => (
              <Badge key={m} variant="success" dot>
                {m}
              </Badge>
            ))}
            {runtime_statistics.failed_models.map((m) => (
              <Badge key={m} variant="destructive" dot>
                {m}
              </Badge>
            ))}
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {[
              { label: 'Preprocessing', value: `${runtime_statistics.preprocessing_time_ms} ms` },
              { label: 'Total Inference', value: `${runtime_statistics.total_inference_time_ms} ms` },
              { label: 'Total Execution', value: `${runtime_statistics.total_execution_time_ms} ms` },
              { label: 'Overall Processing', value: `${runtime_statistics.overall_processing_time_ms} ms` },
            ].map((item) => (
              <div key={item.label}>
                <p className="text-[10px] text-muted-foreground uppercase tracking-wide font-mono">
                  {item.label}
                </p>
                <p className="text-sm font-medium text-foreground mt-0.5 font-mono">{item.value}</p>
              </div>
            ))}
          </div>
        </Card>
      )}

      <div className="flex items-center gap-4 px-1 py-3 border-t border-border text-[11px] text-muted-foreground font-mono flex-wrap">
        <span className="inline-flex items-center gap-1.5">
          <Cpu className="w-3 h-3" /> API {metadata.api_version}
        </span>
        <span>Backend {metadata.backend_version}</span>
        <span>Manifest {metadata.model_manifest_version}</span>
        <span className="inline-flex items-center gap-1.5 ml-auto">
          <Clock className="w-3 h-3" /> {metadata.processing_time_ms} ms total
        </span>
      </div>

      <div className="flex justify-end">
        <Button variant="outline" size="sm" onClick={onStartNew}>
          Analyze another image
        </Button>
      </div>
    </div>
  );
}

interface PredictionErrorViewProps {
  error: unknown;
  onRetry: () => void;
}

export function PredictionErrorView({ error, onRetry }: PredictionErrorViewProps) {
  const envelope: ApiErrorEnvelope | null = isApiErrorEnvelope(error) ? error : null;
  const message =
    envelope?.errors?.[0]?.message ?? envelope?.message ?? 'An unexpected error occurred. Please try again.';
  const requestId = envelope?.request_id;

  return (
    <Card>
      <div className="flex flex-col items-center justify-center py-16 px-8 text-center">
        <div className="w-11 h-11 rounded-xl bg-destructive/10 flex items-center justify-center text-destructive mb-4">
          <XCircle className="w-5 h-5" />
        </div>
        <p className="text-sm font-semibold text-foreground">No prediction available</p>
        <p className="text-sm text-muted-foreground mt-1 max-w-sm">{message}</p>
        {requestId && (
          <p className="text-[11px] text-muted-foreground font-mono mt-3">Request ID: {requestId}</p>
        )}
        <Button variant="outline" size="sm" className="mt-5" onClick={onRetry}>
          Try again
        </Button>
      </div>
    </Card>
  );
}

export default PredictionResultView;
