import { useNavigate, useParams, Link } from 'react-router-dom';
import {
  ArrowLeft,
  Microscope,
  Layers,
  AlertTriangle,
  FileWarning,
  ShieldAlert,
  FileText,
  Activity,
} from 'lucide-react';
import { Card, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { ErrorState } from '@/components/ui/ErrorState';
import { EmptyState } from '@/components/ui/EmptyState';
import { Skeleton } from '@/components/ui/Skeleton';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/Table';
import { usePredictionHistoryDetail } from '@/hooks/queries/usePredictionHistory';
import { formatDateTime, formatFileSize, formatInferenceTime } from '@/utils/formatters';
import { ROUTES } from '@/constants/routes';
import { AISummaryCard } from '@/features/prediction';
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

function statusBadgeVariant(status: PredictionHistoryStatus): 'success' | 'warning' | 'error' | 'secondary' {
  if (status === 'success') return 'success';
  if (status === 'partial_success') return 'warning';
  if (status === 'failed') return 'error';
  return 'secondary';
}

export default function HistoryDetailPage() {
  const { historyId } = useParams<{ historyId: string }>();
  const navigate = useNavigate();

  const { data: record, isLoading, isError, error, refetch } = usePredictionHistoryDetail(historyId);

  const notFound = isError && (error as { statusCode?: number } | undefined)?.statusCode === 404;

  return (
    <div className="space-y-6">
      {/* ── Case Navigation & Header ── */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-border pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl md:text-2xl font-bold tracking-tight font-display text-text-primary">
              Pathology Evaluation Record
            </h1>
            <Badge variant="outline" className="font-mono text-[11px] text-text-muted">
              {historyId ? `Case #${historyId.slice(0, 8)}` : 'Record'}
            </Badge>
          </div>
          <p className="text-xs md:text-sm text-text-muted mt-0.5">
            Archival record of computational pathology evidence, individual model inferences, and specimen telemetry.
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate(ROUTES.HISTORY)}
            className="gap-1.5"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to Archive
          </Button>
          <Button asChild size="sm" variant="primary" className="gap-1.5 shadow-xs">
            <Link to={ROUTES.PREDICT}>
              <Microscope className="h-3.5 w-3.5" />
              New Prediction
            </Link>
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
            OncoVision AI computational pathology evaluations are provided solely for research and investigational decision support. Model classifications do not constitute a standalone medical diagnosis and must be interpreted by a certified pathologist in conjunction with complete clinical context.
          </p>
        </div>
      </div>

      {isLoading && (
        <Card className="space-y-4 p-6 border border-border bg-surface">
          <Skeleton className="h-6 w-48" />
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-16 w-full rounded-md" />
            ))}
          </div>
          <Skeleton className="h-32 w-full mt-4" />
        </Card>
      )}

      {!isLoading && notFound && (
        <Card className="border border-border bg-surface">
          <EmptyState
            icon={<FileWarning className="h-8 w-8 text-text-muted" />}
            title="Case Record Not Found"
            description="The requested pathology evaluation record does not exist or you do not have permission to view it."
            action={{ label: 'Return to Case Archive', onClick: () => navigate(ROUTES.HISTORY) }}
          />
        </Card>
      )}

      {!isLoading && isError && !notFound && (
        <Card className="border border-border bg-surface p-6">
          <ErrorState
            title="Failed to Load Case Record"
            message="The computational pathology history record could not be retrieved from the server."
            onRetry={() => refetch()}
          />
        </Card>
      )}

      {!isLoading && !isError && record && (
        <>
          {/* ── Primary Evaluation Summary Card ── */}
          <Card className="border border-border bg-surface overflow-hidden">
            {record.status === 'partial_success' && (
              <div className="flex items-start gap-2.5 p-3.5 mb-5 rounded-md bg-warning-surface border border-warning/20">
                <AlertTriangle className="h-4 w-4 text-warning mt-0.5 shrink-0" />
                <p className="text-xs text-warning font-medium leading-relaxed">
                  Partial ensemble inference: only a subset of models completed evaluation. Cross-architecture consensus was degraded.
                </p>
              </div>
            )}
            {record.status === 'failed' && (
              <div className="flex items-start gap-2.5 p-3.5 mb-5 rounded-md bg-error-surface border border-error/20">
                <AlertTriangle className="h-4 w-4 text-error mt-0.5 shrink-0" />
                <p className="text-xs text-error font-medium leading-relaxed">
                  Evaluation failed: no model architecture produced a valid pathology inference.
                </p>
              </div>
            )}

            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-5 border-b border-border">
              <div className="flex items-center gap-3">
                <div className="h-11 w-11 rounded-lg bg-surface-raised border border-border flex items-center justify-center text-primary shrink-0">
                  <Activity className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-[10px] text-text-muted uppercase tracking-wider font-mono">
                    Histopathological Finding
                  </p>
                  <div className="flex items-center gap-2.5 mt-0.5">
                    <h2 className="text-lg sm:text-xl font-bold font-display text-text-primary">
                      {formatClassLabel(record.predicted_class)}
                    </h2>
                    <Badge
                      variant={getDiseaseBadgeVariant(record.predicted_class)}
                      className="text-xs font-semibold px-2 py-0.5"
                    >
                      {formatClassLabel(record.predicted_class)}
                    </Badge>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2 self-start sm:self-center">
                <Badge variant={statusBadgeVariant(record.status)} dot className="capitalize text-xs font-mono">
                  Pipeline {record.status.replace('_', ' ')}
                </Badge>
              </div>
            </div>

            {/* Evidence Metric Grid */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5 pt-5">
              <div className="rounded-md border border-border bg-surface-raised/40 px-3.5 py-3">
                <p className="text-[10px] text-text-muted uppercase tracking-wider font-mono">Ensemble Confidence</p>
                <p className="text-base sm:text-lg font-bold font-mono tabular-nums text-text-primary mt-1">
                  {record.status === 'failed' ? '—' : `${record.confidence}%`}
                </p>
                <p className="text-[10px] text-text-muted mt-0.5">Posterior probability</p>
              </div>

              <div className="rounded-md border border-border bg-surface-raised/40 px-3.5 py-3">
                <p className="text-[10px] text-text-muted uppercase tracking-wider font-mono">Model Agreement</p>
                <p className="text-base sm:text-lg font-bold font-mono tabular-nums text-text-primary mt-1">
                  {record.status === 'success'
                    ? `${Math.round(record.agreement_ratio * 100)}%`
                    : '—'}
                </p>
                <p className="text-[10px] text-text-muted mt-0.5">Inter-architecture consensus</p>
              </div>

              <div className="rounded-md border border-border bg-surface-raised/40 px-3.5 py-3">
                <p className="text-[10px] text-text-muted uppercase tracking-wider font-mono">Participating Models</p>
                <p className="text-base sm:text-lg font-bold font-mono tabular-nums text-text-primary mt-1">
                  {record.participating_models} architectures
                </p>
                <p className="text-[10px] text-text-muted mt-0.5">Evaluation ensemble</p>
              </div>

              <div className="rounded-md border border-border bg-surface-raised/40 px-3.5 py-3">
                <p className="text-[10px] text-text-muted uppercase tracking-wider font-mono">Inference Latency</p>
                <p className="text-base sm:text-lg font-bold font-mono tabular-nums text-text-primary mt-1">
                  {record.runtime_info.processing_time_ms != null
                    ? formatInferenceTime(record.runtime_info.processing_time_ms)
                    : '—'}
                </p>
                <p className="text-[10px] text-text-muted mt-0.5">End-to-end execution</p>
              </div>
            </div>

            {/* Model Architecture Badges */}
            {(record.successful_models.length > 0 || record.failed_models.length > 0) && (
              <div className="mt-4 pt-4 border-t border-border flex flex-wrap items-center gap-2">
                <span className="text-[11px] font-mono text-text-muted uppercase tracking-wider mr-1">
                  Architectures:
                </span>
                {record.successful_models.map((m) => (
                  <Badge key={m} variant="success" dot className="font-mono text-xs">
                    {m}
                  </Badge>
                ))}
                {record.failed_models.map((m) => (
                  <Badge key={m} variant="error" dot className="font-mono text-xs">
                    {m} (failed)
                  </Badge>
                ))}
              </div>
            )}
          </Card>

          {/* ── AI Clinical Summary & Discussion ── */}
          <AISummaryCard
            predictionId={record.history_id}
            initialSummary={record.ai_summary}
          />

          {/* ── Individual Model Predictions Table ── */}
          {record.individual_predictions.length > 0 && (
            <Card padding="none" className="border border-border bg-surface overflow-hidden">
              <div className="flex items-center justify-between px-4 py-3.5 border-b border-border bg-surface-raised/30">
                <div className="flex items-center gap-2">
                  <Layers className="h-4 w-4 text-primary" />
                  <h3 className="text-sm font-semibold text-text-primary">
                    Cross-Architecture Model Predictions
                  </h3>
                </div>
                <Badge variant="outline" className="font-mono text-[10px] text-text-muted">
                  {record.individual_predictions.length} models
                </Badge>
              </div>

              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Architecture</TableHead>
                      <TableHead>Model Classification</TableHead>
                      <TableHead className="text-right">Confidence</TableHead>
                      <TableHead className="text-right">Inference Latency</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {record.individual_predictions.map((p) => {
                      const modelDiseaseVariant = getDiseaseBadgeVariant(p.prediction);
                      return (
                        <TableRow key={p.model_name}>
                          <TableCell className="font-mono font-medium text-xs text-text-primary">
                            {p.model_name}
                          </TableCell>
                          <TableCell>
                            <Badge variant={modelDiseaseVariant} className="text-[11px] font-semibold">
                              {formatClassLabel(p.prediction)}
                            </Badge>
                          </TableCell>
                          <TableCell className="font-mono tabular-nums font-semibold text-xs text-text-primary text-right">
                            {p.confidence}%
                          </TableCell>
                          <TableCell className="font-mono tabular-nums text-xs text-text-muted text-right">
                            {formatInferenceTime(p.inference_time_ms)}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>
            </Card>
          )}

          {/* ── Image & Specimen Metadata ── */}
          <Card className="border border-border bg-surface">
            <CardHeader className="pb-3 border-b border-border-subtle">
              <div className="flex items-center gap-2">
                <FileText className="h-4 w-4 text-text-muted" />
                <CardTitle className="text-sm font-semibold text-text-primary">
                  Specimen &amp; Execution Metadata
                </CardTitle>
              </div>
            </CardHeader>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 pt-4">
              {[
                { label: 'Specimen Filename', value: record.image_metadata.filename },
                { label: 'MIME Content Type', value: record.image_metadata.content_type },
                { label: 'File Size', value: formatFileSize(record.image_metadata.size_bytes) },
                {
                  label: 'Slide Dimensions',
                  value: `${record.image_metadata.width} × ${record.image_metadata.height} px`,
                },
                { label: 'Manifest Version', value: record.runtime_info.model_manifest_version ?? '—' },
                { label: 'Analysis Timestamp', value: formatDateTime(record.created_at) },
              ].map((item) => (
                <div key={item.label} className="space-y-1">
                  <p className="text-[10px] text-text-muted uppercase tracking-wider font-mono">{item.label}</p>
                  <p className="text-xs font-mono font-medium text-text-primary truncate">{item.value}</p>
                </div>
              ))}
            </div>
            <div className="mt-4 pt-4 border-t border-border-subtle grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px] font-mono text-text-muted">
              <span className="truncate">History ID: {record.history_id}</span>
              <span className="truncate">Request ID: {record.request_id}</span>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
