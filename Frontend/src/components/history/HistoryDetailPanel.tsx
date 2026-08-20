import { ArrowLeft, ImageIcon, Layers, AlertTriangle } from 'lucide-react';
import { Card, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { ErrorState } from '@/components/ui/ErrorState';
import { SkeletonCard } from '@/components/ui/Skeleton';
import type { HistoryRecord } from '@/types/history';

function formatClassLabel(raw: string): string {
  if (!raw) return '—';
  return raw
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

function formatBytes(bytes: number) {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

interface HistoryDetailPanelProps {
  loading: boolean;
  error: boolean;
  record: HistoryRecord | null;
  onBack: () => void;
  onRetry: () => void;
}

export function HistoryDetailPanel({ loading, error, record, onBack, onRetry }: HistoryDetailPanelProps) {
  return (
    <div className="space-y-5">
      <Button variant="ghost" size="sm" icon={<ArrowLeft className="w-3.5 h-3.5" />} onClick={onBack}>
        Back to history
      </Button>

      {loading && <SkeletonCard className="h-64" />}

      {!loading && error && (
        <Card>
          <ErrorState
            variant="full"
            title="Couldn't load this record"
            message="This prediction history record couldn't be loaded. Please try again."
            onRetry={onRetry}
          />
        </Card>
      )}

      {!loading && !error && !record && (
        <Card>
          <ErrorState variant="full" title="Record not found" message="This history record no longer exists." onRetry={onBack} />
        </Card>
      )}

      {!loading && !error && record && (
        <>
          <Card>
            {record.status === 'partial_success' && (
              <div className="flex items-start gap-2.5 mb-5 p-3 rounded-md bg-warning/10 border border-warning/30">
                <AlertTriangle className="w-4 h-4 text-warning mt-0.5 shrink-0" />
                <p className="text-sm text-warning font-medium">
                  Partial result — only one model completed. No ensemble agreement was available.
                </p>
              </div>
            )}
            {record.status === 'failed' && (
              <div className="flex items-start gap-2.5 mb-5 p-3 rounded-md bg-destructive/10 border border-destructive/30">
                <AlertTriangle className="w-4 h-4 text-destructive mt-0.5 shrink-0" />
                <p className="text-sm text-destructive font-medium">
                  This prediction failed — no models produced a usable result.
                </p>
              </div>
            )}

            <div className="flex items-start justify-between gap-4 mb-6">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-muted flex items-center justify-center text-muted-foreground shrink-0">
                  <ImageIcon className="w-4.5 h-4.5" />
                </div>
                <div>
                  <p className="text-xs text-muted-foreground uppercase tracking-widest font-mono mb-1">
                    Predicted Class
                  </p>
                  <h2 className="text-xl font-bold text-foreground">{formatClassLabel(record.predicted_class)}</h2>
                </div>
              </div>
              <Badge
                variant={
                  record.status === 'success'
                    ? 'success'
                    : record.status === 'partial_success'
                      ? 'warning'
                      : record.status === 'failed'
                        ? 'destructive'
                        : 'offline'
                }
                dot
              >
                {record.status.replace('_', ' ')}
              </Badge>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              {[
                { label: 'Confidence', value: record.status === 'failed' ? '—' : `${record.confidence.toFixed(1)}%` },
                {
                  label: 'Agreement',
                  value:
                    record.status === 'success' ? `${Math.round(record.agreement_ratio * 100)}%` : '—',
                },
                { label: 'Participating', value: record.participating_models },
                { label: 'Processing Time', value: `${record.processing_time_ms} ms` },
              ].map((item) => (
                <div key={item.label} className="rounded-md border border-border bg-muted/20 px-3 py-2">
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wide font-mono">
                    {item.label}
                  </p>
                  <p className="text-sm font-semibold text-foreground mt-0.5">{item.value}</p>
                </div>
              ))}
            </div>
          </Card>

          {record.individual_predictions && record.individual_predictions.length > 0 && (
            <Card padding="none">
              <div className="flex items-center gap-2 px-5 py-4 border-b border-border">
                <Layers className="w-4 h-4 text-muted-foreground" />
                <h3 className="text-sm font-semibold text-foreground">Individual Model Predictions</h3>
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
                    {record.individual_predictions.map((p) => (
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

          <Card>
            <CardHeader>
              <CardTitle>Image &amp; Record Metadata</CardTitle>
            </CardHeader>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
              {[
                { label: 'Filename', value: record.image_filename },
                { label: 'Content Type', value: record.image_content_type },
                { label: 'File Size', value: formatBytes(record.image_size_bytes) },
                { label: 'Dimensions', value: `${record.image_width} × ${record.image_height}` },
                { label: 'Manifest Version', value: record.model_manifest_version },
                { label: 'Created', value: new Date(record.created_at).toLocaleString() },
              ].map((item) => (
                <div key={item.label}>
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wide font-mono">
                    {item.label}
                  </p>
                  <p className="text-xs font-medium text-foreground mt-0.5 font-mono truncate">{item.value}</p>
                </div>
              ))}
            </div>
            <div className="mt-4 pt-4 border-t border-border grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px] font-mono text-muted-foreground">
              <span>History ID: {record.history_id}</span>
              <span>Request ID: {record.request_id}</span>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}

export default HistoryDetailPanel;
