import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, ImageIcon, Layers, AlertTriangle, FileWarning } from 'lucide-react';
import { SectionTitle } from '@/components/ui/SectionTitle';
import { Card, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { ErrorState } from '@/components/ui/ErrorState';
import { EmptyState } from '@/components/ui/EmptyState';
import { Skeleton } from '@/components/ui/Skeleton';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/Table';
import { useAdminHistoryDetail } from '@/hooks/queries/useAdminHistory';
import { formatDateTime, formatFileSize, formatInferenceTime } from '@/utils/formatters';
import { ROUTES } from '@/constants/routes';
import type { PredictionHistoryStatus } from '@/types';

function formatClassLabel(raw: string | null): string {
  if (!raw) return '—';
  return raw
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

function statusBadgeVariant(status: PredictionHistoryStatus) {
  if (status === 'success') return 'success' as const;
  if (status === 'partial_success') return 'warning' as const;
  if (status === 'failed') return 'destructive' as const;
  return 'secondary' as const;
}

// Admin-only equivalent of dashboard/HistoryDetailPage.tsx — same record
// shape plus `user_id`, and reachable for ANY user's history record
// (GET /api/v1/admin/history/{history_id}), not just the caller's own.
export default function AdminHistoryDetailPage() {
  const { historyId } = useParams<{ historyId: string }>();
  const navigate = useNavigate();

  const { data: record, isLoading, isError, error, refetch } = useAdminHistoryDetail(historyId);

  const notFound = isError && (error as { statusCode?: number } | undefined)?.statusCode === 404;

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={() => navigate(ROUTES.ADMIN_HISTORY)}>
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to all history
        </Button>
      </div>

      <SectionTitle
        title="Prediction Detail"
        description={historyId ? `Record ${historyId.slice(0, 8)}…` : undefined}
      />

      {isLoading && (
        <Card>
          <div className="space-y-4">
            <Skeleton className="h-5 w-40" />
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-14 w-full" />
              ))}
            </div>
          </div>
        </Card>
      )}

      {!isLoading && notFound && (
        <Card>
          <EmptyState
            icon={<FileWarning className="h-6 w-6" />}
            title="Record not found"
            description="This prediction history record doesn't exist."
            action={{ label: 'Back to all history', onClick: () => navigate(ROUTES.ADMIN_HISTORY) }}
          />
        </Card>
      )}

      {!isLoading && isError && !notFound && (
        <Card>
          <ErrorState message="Couldn't load this prediction record." onRetry={() => refetch()} />
        </Card>
      )}

      {!isLoading && !isError && record && (
        <>
          <Card>
            {record.status === 'partial_success' && (
              <div className="flex items-start gap-2.5 mb-5 p-3 rounded-md bg-amber-500/10 border border-amber-500/20">
                <AlertTriangle className="h-4 w-4 text-amber-400 mt-0.5 shrink-0" />
                <p className="text-sm text-amber-400 font-medium">
                  Partial result — only one model completed. Ensemble agreement wasn't available.
                </p>
              </div>
            )}
            {record.status === 'failed' && (
              <div className="flex items-start gap-2.5 mb-5 p-3 rounded-md bg-destructive/10 border border-destructive/20">
                <AlertTriangle className="h-4 w-4 text-destructive mt-0.5 shrink-0" />
                <p className="text-sm text-destructive font-medium">
                  This prediction failed — no models produced a usable result.
                </p>
              </div>
            )}

            <div className="flex items-start justify-between gap-4 mb-6">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-lg bg-muted flex items-center justify-center text-muted-foreground shrink-0">
                  <ImageIcon className="h-4.5 w-4.5" />
                </div>
                <div>
                  <p className="text-xs text-muted-foreground uppercase tracking-widest font-mono mb-1">
                    Predicted Class
                  </p>
                  <h2 className="text-xl font-bold text-foreground">{formatClassLabel(record.predicted_class)}</h2>
                </div>
              </div>
              <Badge variant={statusBadgeVariant(record.status)} dot className="capitalize">
                {record.status.replace('_', ' ')}
              </Badge>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              {[
                { label: 'Confidence', value: record.status === 'failed' ? '—' : `${record.confidence}%` },
                {
                  label: 'Agreement',
                  value: record.status === 'success' ? `${Math.round(record.agreement_ratio * 100)}%` : '—',
                },
                { label: 'Participating Models', value: record.participating_models },
                {
                  label: 'Processing Time',
                  value:
                    record.processing_time_ms != null ? formatInferenceTime(record.processing_time_ms) : '—',
                },
              ].map((item) => (
                <div key={item.label} className="rounded-md border border-border bg-muted/20 px-3 py-2">
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wide font-mono">{item.label}</p>
                  <p className="text-sm font-semibold text-foreground mt-0.5">{item.value}</p>
                </div>
              ))}
            </div>

            {(record.successful_models.length > 0 || record.failed_models.length > 0) && (
              <div className="mt-4 pt-4 border-t border-border flex flex-wrap gap-2">
                {record.successful_models.map((m) => (
                  <Badge key={m} variant="success" dot>
                    {m}
                  </Badge>
                ))}
                {record.failed_models.map((m) => (
                  <Badge key={m} variant="destructive" dot>
                    {m}
                  </Badge>
                ))}
              </div>
            )}
          </Card>

          {record.individual_predictions.length > 0 && (
            <Card padding="none">
              <div className="flex items-center gap-2 px-4 py-3 border-b border-border">
                <Layers className="h-4 w-4 text-muted-foreground" />
                <h3 className="text-sm font-semibold text-foreground">Individual Model Predictions</h3>
              </div>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Model</TableHead>
                    <TableHead>Prediction</TableHead>
                    <TableHead>Confidence</TableHead>
                    <TableHead>Inference Time</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {record.individual_predictions.map((p) => (
                    <TableRow key={p.model_name}>
                      <TableCell className="font-mono text-xs">{p.model_name}</TableCell>
                      <TableCell>{formatClassLabel(p.prediction)}</TableCell>
                      <TableCell>{p.confidence}%</TableCell>
                      <TableCell className="text-muted-foreground font-mono text-xs">
                        {formatInferenceTime(p.inference_time_ms)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Card>
          )}

          <Card>
            <CardHeader>
              <CardTitle>Owner, Image &amp; Record Metadata</CardTitle>
            </CardHeader>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
              {[
                { label: 'Filename', value: record.image_filename },
                { label: 'Content Type', value: record.image_content_type },
                { label: 'File Size', value: formatFileSize(record.image_size_bytes) },
                { label: 'Dimensions', value: `${record.image_width} × ${record.image_height}` },
                { label: 'Manifest Version', value: record.model_manifest_version ?? '—' },
                { label: 'Created', value: formatDateTime(record.created_at) },
              ].map((item) => (
                <div key={item.label}>
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wide font-mono">{item.label}</p>
                  <p className="text-xs font-medium text-foreground mt-0.5 font-mono truncate">{item.value}</p>
                </div>
              ))}
            </div>
            <div className="mt-4 pt-4 border-t border-border grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px] font-mono text-muted-foreground">
              <span>History ID: {record.history_id}</span>
              <span>User Email: {record.user_email}</span>
              <span>Request ID: {record.request_id}</span>
              <span>Owner User ID: {record.user_id}</span>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
