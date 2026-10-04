import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, ImageIcon, Layers, AlertTriangle, FileWarning, FileText } from 'lucide-react';
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
  if (!raw) return 'Pending Analysis';
  return raw
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

function getStatusBadgeVariant(status: PredictionHistoryStatus): 'success' | 'warning' | 'error' | 'secondary' {
  if (status === 'success') return 'success';
  if (status === 'partial_success') return 'warning';
  if (status === 'failed') return 'error';
  return 'secondary';
}

export default function AdminHistoryDetailPage() {
  const { historyId } = useParams<{ historyId: string }>();
  const navigate = useNavigate();

  const { data: record, isLoading, isError, error, refetch } = useAdminHistoryDetail(historyId);

  const notFound = isError && (error as { statusCode?: number } | undefined)?.statusCode === 404;

  return (
    <div className="space-y-6">
      {/* Navigation Return */}
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => navigate(ROUTES.ADMIN_HISTORY)}
          className="gap-2 text-xs text-text-secondary hover:text-text-primary"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>Back to Evaluation Archive</span>
        </Button>
      </div>

      {/* Header */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <SectionTitle
          title="Case Evaluation Record"
          description={historyId ? `Inspection record for evaluation ID ${historyId}` : undefined}
        />
        {record && (
          <div className="flex items-center gap-2">
            <Badge variant={getStatusBadgeVariant(record.status)} dot className="text-xs capitalize px-2.5 py-1">
              Pipeline: {record.status.replace('_', ' ')}
            </Badge>
          </div>
        )}
      </div>

      {/* Loading Skeleton */}
      {isLoading && (
        <Card className="space-y-6 p-6">
          <div className="flex items-center gap-4">
            <Skeleton className="h-12 w-12 rounded-lg" />
            <div className="space-y-2">
              <Skeleton className="h-4 w-28" />
              <Skeleton className="h-6 w-52" />
            </div>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-16 w-full rounded-lg" />
            ))}
          </div>
        </Card>
      )}

      {/* Not Found State */}
      {!isLoading && notFound && (
        <Card>
          <EmptyState
            icon={<FileWarning className="h-6 w-6 text-text-muted" />}
            title="Evaluation record not found"
            description="The requested prediction history identifier does not exist in the administrative archive."
            action={{ label: 'Return to Archive', onClick: () => navigate(ROUTES.ADMIN_HISTORY) }}
          />
        </Card>
      )}

      {/* Error State */}
      {!isLoading && isError && !notFound && (
        <Card>
          <ErrorState message="Could not retrieve the specified evaluation detail record." onRetry={() => refetch()} />
        </Card>
      )}

      {/* Loaded Evaluation Record */}
      {!isLoading && !isError && record && (
        <>
          {/* Main Case Finding Card */}
          <Card className="p-6 space-y-6">
            {/* Operational Warning Alerts for Failures / Partial states */}
            {record.status === 'partial_success' && (
              <div className="flex items-start gap-3 p-3.5 rounded-lg bg-warning-surface border border-warning/25 text-warning text-xs">
                <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
                <div>
                  <p className="font-semibold">Partial Model Inference Notice</p>
                  <p className="mt-0.5 text-text-secondary">
                    Only a subset of ensemble models completed execution. Full multi-model consensus was unavailable.
                  </p>
                </div>
              </div>
            )}
            {record.status === 'failed' && (
              <div className="flex items-start gap-3 p-3.5 rounded-lg bg-error-surface border border-error/25 text-error text-xs">
                <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
                <div>
                  <p className="font-semibold">Pipeline Execution Failure</p>
                  <p className="mt-0.5 text-text-secondary">
                    Inference failed during runtime execution. No valid classification was produced by the ensemble.
                  </p>
                </div>
              </div>
            )}

            {/* Disease Classification Header */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-6 border-b border-border">
              <div className="flex items-center gap-3.5">
                <div className="h-12 w-12 rounded-lg bg-surface-raised border border-border flex items-center justify-center text-text-muted shrink-0">
                  <ImageIcon className="h-6 w-6 text-primary" />
                </div>
                <div>
                  <span className="text-[10px] text-text-muted uppercase tracking-widest font-mono font-semibold block mb-0.5">
                    Histopathological Classification
                  </span>
                  <div className="flex flex-wrap items-center gap-2.5">
                    <h2 className="text-xl font-bold text-text-primary tracking-tight">
                      {formatClassLabel(record.predicted_class)}
                    </h2>
                    <Badge variant={getDiseaseBadgeVariant(record.predicted_class)} className="text-xs">
                      Categorical Finding
                    </Badge>
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant={getStatusBadgeVariant(record.status)} dot className="text-xs capitalize font-mono">
                  {record.status.replace('_', ' ')}
                </Badge>
              </div>
            </div>

            {/* Evidence & Metrics Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div className="p-3 rounded-lg border border-border bg-surface-raised/40">
                <span className="text-[10px] text-text-muted uppercase tracking-wide font-mono block">
                  Model Confidence
                </span>
                <span className="text-base font-semibold text-text-primary font-mono tabular-nums mt-1 block">
                  {record.status === 'failed' ? '—' : `${record.confidence}%`}
                </span>
                <span className="text-[10px] text-text-muted mt-0.5 block">Weighted ensemble probability</span>
              </div>

              <div className="p-3 rounded-lg border border-border bg-surface-raised/40">
                <span className="text-[10px] text-text-muted uppercase tracking-wide font-mono block">
                  Ensemble Agreement
                </span>
                <span className="text-base font-semibold text-text-secondary font-mono tabular-nums mt-1 block">
                  {record.status === 'success' ? `${Math.round(record.agreement_ratio * 100)}%` : '—'}
                </span>
                <span className="text-[10px] text-text-muted mt-0.5 block">Inter-model concordance</span>
              </div>

              <div className="p-3 rounded-lg border border-border bg-surface-raised/40">
                <span className="text-[10px] text-text-muted uppercase tracking-wide font-mono block">
                  Participating Models
                </span>
                <span className="text-base font-semibold text-text-primary font-mono tabular-nums mt-1 block">
                  {record.participating_models}
                </span>
                <span className="text-[10px] text-text-muted mt-0.5 block">Active runtime estimators</span>
              </div>

              <div className="p-3 rounded-lg border border-border bg-surface-raised/40">
                <span className="text-[10px] text-text-muted uppercase tracking-wide font-mono block">
                  Processing Time
                </span>
                <span className="text-base font-semibold text-text-primary font-mono tabular-nums mt-1 block">
                  {record.processing_time_ms != null ? formatInferenceTime(record.processing_time_ms) : '—'}
                </span>
                <span className="text-[10px] text-text-muted mt-0.5 block">Total pipeline duration</span>
              </div>
            </div>

            {/* Model Execution Status Chips */}
            {(record.successful_models.length > 0 || record.failed_models.length > 0) && (
              <div className="space-y-2 pt-2">
                <span className="text-xs font-medium text-text-muted">Model Runtime Execution Manifest</span>
                <div className="flex flex-wrap gap-2">
                  {record.successful_models.map((m) => (
                    <Badge key={m} variant="success" dot className="font-mono text-xs">
                      {m} (Completed)
                    </Badge>
                  ))}
                  {record.failed_models.map((m) => (
                    <Badge key={m} variant="error" dot className="font-mono text-xs">
                      {m} (Failed)
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </Card>

          {/* Individual Model Predictions Breakdown */}
          {record.individual_predictions.length > 0 && (
            <Card padding="none">
              <div className="flex items-center justify-between px-5 py-3.5 border-b border-border bg-surface-raised/30">
                <div className="flex items-center gap-2">
                  <Layers className="h-4 w-4 text-primary" />
                  <h3 className="text-sm font-semibold text-text-primary">Individual Estimator Inference</h3>
                </div>
                <span className="text-xs font-mono text-text-muted">
                  {record.individual_predictions.length} constituent predictions
                </span>
              </div>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead scope="col">Model Architecture</TableHead>
                    <TableHead scope="col">Predicted Finding</TableHead>
                    <TableHead scope="col">Confidence</TableHead>
                    <TableHead scope="col" className="text-right">Execution Latency</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {record.individual_predictions.map((p) => {
                    const diseaseVariant = getDiseaseBadgeVariant(p.prediction);
                    return (
                      <TableRow key={p.model_name}>
                        <TableCell className="font-mono text-xs font-medium text-text-primary">
                          {p.model_name}
                        </TableCell>
                        <TableCell>
                          <Badge variant={diseaseVariant} className="text-xs">
                            {formatClassLabel(p.prediction)}
                          </Badge>
                        </TableCell>
                        <TableCell className="font-mono text-xs tabular-nums text-text-primary font-semibold">
                          {p.confidence}%
                        </TableCell>
                        <TableCell className="text-right text-xs font-mono tabular-nums text-text-muted">
                          {formatInferenceTime(p.inference_time_ms)}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </Card>
          )}

          {/* Technical Metadata Record Card */}
          <Card className="p-5 space-y-4">
            <CardHeader className="p-0 pb-2">
              <div className="flex items-center gap-2">
                <FileText className="h-4 w-4 text-text-muted" />
                <CardTitle className="text-sm">Specimen &amp; Runtime Metadata</CardTitle>
              </div>
            </CardHeader>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
              <div className="space-y-0.5">
                <span className="text-[10px] text-text-muted uppercase tracking-wide font-mono block">Image Filename</span>
                <span className="text-xs font-medium font-mono text-text-primary truncate block" title={record.image_filename}>
                  {record.image_filename}
                </span>
              </div>
              <div className="space-y-0.5">
                <span className="text-[10px] text-text-muted uppercase tracking-wide font-mono block">MIME Content Type</span>
                <span className="text-xs font-medium font-mono text-text-secondary block">
                  {record.image_content_type}
                </span>
              </div>
              <div className="space-y-0.5">
                <span className="text-[10px] text-text-muted uppercase tracking-wide font-mono block">File Size</span>
                <span className="text-xs font-medium font-mono text-text-secondary block">
                  {formatFileSize(record.image_size_bytes)}
                </span>
              </div>
              <div className="space-y-0.5">
                <span className="text-[10px] text-text-muted uppercase tracking-wide font-mono block">Dimensions (W × H)</span>
                <span className="text-xs font-medium font-mono text-text-secondary block">
                  {record.image_width} × {record.image_height} px
                </span>
              </div>
              <div className="space-y-0.5">
                <span className="text-[10px] text-text-muted uppercase tracking-wide font-mono block">Manifest Version</span>
                <span className="text-xs font-medium font-mono text-text-secondary block">
                  {record.model_manifest_version ?? '—'}
                </span>
              </div>
              <div className="space-y-0.5">
                <span className="text-[10px] text-text-muted uppercase tracking-wide font-mono block">Evaluation Timestamp</span>
                <span className="text-xs font-medium font-mono text-text-secondary block">
                  {formatDateTime(record.created_at)}
                </span>
              </div>
            </div>

            <div className="mt-4 pt-3 border-t border-border grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px] font-mono text-text-muted">
              <div className="flex items-center gap-1.5 truncate">
                <span className="text-text-muted/70">History ID:</span>
                <span className="text-text-secondary truncate">{record.history_id}</span>
              </div>
              <div className="flex items-center gap-1.5 truncate">
                <span className="text-text-muted/70">User Email:</span>
                <span className="text-text-secondary truncate">{record.user_email}</span>
              </div>
              <div className="flex items-center gap-1.5 truncate">
                <span className="text-text-muted/70">Request ID:</span>
                <span className="text-text-secondary truncate">{record.request_id}</span>
              </div>
              <div className="flex items-center gap-1.5 truncate">
                <span className="text-text-muted/70">User ID:</span>
                <span className="text-text-secondary truncate">{record.user_id}</span>
              </div>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
