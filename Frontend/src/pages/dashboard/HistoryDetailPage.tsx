import { useParams, useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, Image, Clock, Server, CheckCircle2, XCircle, Users, BarChart3, ShieldCheck } from 'lucide-react';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Card, CardContent } from '@/components/ui/Card';
import { Skeleton } from '@/components/ui/Skeleton';
import { SectionTitle } from '@/components/ui/SectionTitle';
import { IndividualModelsCard } from '@/features/prediction/components/IndividualModelsCard';
import { ROUTES } from '@/constants/routes';
import { useHistoryDetail } from '@/features/history/hooks/useHistoryQueries';
import { formatDateTime } from '@/utils/formatters';
import { cn } from '@/lib/utils';
import type { BackendPredictionStatus } from '@/types';

function statusMeta(status: BackendPredictionStatus) {
  switch (status) {
    case 'success':
      return { label: 'Success', variant: 'success' as const, color: 'text-emerald-400', icon: <CheckCircle2 className="h-4 w-4" /> };
    case 'partial_success':
      return { label: 'Partial Success', variant: 'warning' as const, color: 'text-amber-400', icon: <CheckCircle2 className="h-4 w-4" /> };
    case 'failed':
      return { label: 'Failed', variant: 'destructive' as const, color: 'text-destructive', icon: <XCircle className="h-4 w-4" /> };
    default:
      return { label: 'Pending', variant: 'default' as const, color: 'text-muted-foreground', icon: <Clock className="h-4 w-4" /> };
  }
}

function ConfidenceBar({ value }: { value: number }) {
  const clamped = Math.min(100, Math.max(0, value));
  const color = clamped >= 80 ? 'bg-emerald-500' : clamped >= 60 ? 'bg-amber-500' : 'bg-rose-500';
  return (
    <div className="relative h-2 w-full rounded-full bg-secondary overflow-hidden">
      <motion.div
        className={cn('h-full rounded-full', color)}
        initial={{ width: 0 }}
        animate={{ width: `${clamped}%` }}
        transition={{ duration: 0.7, ease: 'easeOut' }}
      />
    </div>
  );
}

function MetaRow({ label, value }: { label: string; value: string | number | null | undefined }) {
  if (value === null || value === undefined) return null;
  return (
    <div className="flex items-center justify-between gap-4 py-1.5">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className="font-mono text-xs">{value}</span>
    </div>
  );
}

function DetailSkeleton() {
  return (
    <div className="space-y-5">
      <Skeleton className="h-8 w-64" />
      <div className="grid gap-5 lg:grid-cols-[1fr_320px]">
        <div className="space-y-5">
          <Skeleton className="h-48 rounded-xl" />
          <Skeleton className="h-32 rounded-xl" />
        </div>
        <Skeleton className="h-64 rounded-xl" />
      </div>
    </div>
  );
}

export default function HistoryDetailPage() {
  const { historyId } = useParams<{ historyId: string }>();
  const navigate = useNavigate();
  const { data, isLoading, isError, error } = useHistoryDetail(historyId ?? '');

  const statusCode = (error as { statusCode?: number })?.statusCode;
  const errorMsg = (error as { message?: string })?.message;

  if (isLoading) return <DetailSkeleton />;

  if (isError) {
    const isNotFound = statusCode === 404;
    return (
      <div className="space-y-5">
        <Button variant="ghost" size="sm" onClick={() => navigate(ROUTES.HISTORY)} className="gap-1.5 text-muted-foreground">
          <ArrowLeft className="h-3.5 w-3.5" /> Back to History
        </Button>
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-14 text-center">
            <div className="flex h-14 w-14 items-center justify-center rounded-full bg-muted">
              <XCircle className="h-7 w-7 text-muted-foreground" />
            </div>
            <p className="text-sm font-medium">
              {isNotFound ? 'Prediction record not found' : 'Failed to load prediction'}
            </p>
            <p className="text-xs text-muted-foreground max-w-xs leading-relaxed">
              {isNotFound
                ? 'This record does not exist or you do not have access to it.'
                : (errorMsg ?? 'An unexpected error occurred.')}
            </p>
            <Button variant="outline" size="sm" asChild className="mt-1">
              <Link to={ROUTES.HISTORY}>Return to History</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!data) return null;

  const meta = statusMeta(data.status);
  const hasResult = data.predicted_class !== null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-6"
    >
      {/* Back + header */}
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={() => navigate(ROUTES.HISTORY)} className="gap-1.5 text-muted-foreground shrink-0">
          <ArrowLeft className="h-3.5 w-3.5" /> Back
        </Button>
        <SectionTitle
          title="Prediction Detail"
          description={`Record ${data.history_id.slice(0, 8)}… · ${formatDateTime(data.created_at)}`}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_320px] xl:grid-cols-[1fr_360px]">
        {/* Left */}
        <div className="space-y-5">

          {/* Status + result card */}
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35 }}
            className="rounded-xl border border-border bg-card p-5 space-y-5"
            role="region"
            aria-label="Prediction result"
          >
            {/* Header */}
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-2.5">
                <div className={cn('flex h-9 w-9 items-center justify-center rounded-full ring-1', meta.color,
                  data.status === 'success' ? 'ring-emerald-500/30 bg-emerald-500/10' :
                  data.status === 'partial_success' ? 'ring-amber-500/30 bg-amber-500/10' :
                  data.status === 'failed' ? 'ring-destructive/30 bg-destructive/10' :
                  'ring-border bg-secondary'
                )}>
                  {meta.icon}
                </div>
                <div>
                  <h2 className="text-sm font-semibold tracking-tight">AI Prediction</h2>
                  <p className="text-[11px] text-muted-foreground mt-0.5">{formatDateTime(data.created_at)}</p>
                </div>
              </div>
              <Badge variant={meta.variant} className="shrink-0 text-[10px]">
                {data.status.replace('_', ' ').toUpperCase()}
              </Badge>
            </div>

            {/* Predicted class */}
            {hasResult ? (
              <div className="space-y-4">
                <div className="rounded-lg border border-border/60 bg-secondary/40 p-4">
                  <p className="text-[10px] uppercase tracking-widest text-muted-foreground/60 mb-1">Predicted Class</p>
                  <p className="text-xl font-bold tracking-tight leading-none">{data.predicted_class}</p>
                  <p className="text-[11px] text-muted-foreground mt-1.5">AI-assisted analysis — not a clinical diagnosis</p>
                </div>

                <div className="space-y-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="flex items-center gap-1.5 text-muted-foreground">
                      <BarChart3 className="h-3.5 w-3.5" /> Model Confidence
                    </span>
                    <span className="font-mono font-semibold">{data.confidence.toFixed(1)}%</span>
                  </div>
                  <ConfidenceBar value={data.confidence} />
                </div>

                <div className="space-y-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="flex items-center gap-1.5 text-muted-foreground">
                      <ShieldCheck className="h-3.5 w-3.5" /> Model Agreement
                    </span>
                    <span className="font-mono font-semibold">{(data.agreement_ratio * 100).toFixed(0)}%</span>
                  </div>
                  <ConfidenceBar value={data.agreement_ratio * 100} />
                </div>

                <div className="flex items-center gap-2 flex-wrap">
                  <div className="flex items-center gap-1.5 rounded-md border border-border/50 bg-secondary/60 px-2.5 py-1.5">
                    <Users className="h-3 w-3 text-muted-foreground" />
                    <span className="text-[11px] text-muted-foreground">
                      {data.successful_models.length}/{data.participating_models} models succeeded
                    </span>
                  </div>
                  {data.failed_models.length > 0 && (
                    <div className="flex items-center gap-1.5 rounded-md border border-destructive/30 bg-destructive/10 px-2.5 py-1.5">
                      <XCircle className="h-3 w-3 text-destructive" />
                      <span className="text-[11px] text-destructive">
                        {data.failed_models.length} model{data.failed_models.length !== 1 ? 's' : ''} failed
                      </span>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="rounded-lg border border-border/40 bg-secondary/30 p-4">
                <p className="text-sm font-medium text-muted-foreground">
                  {data.status === 'partial_success'
                    ? 'No ensemble result produced — see individual model breakdown below.'
                    : 'No result available for this prediction.'}
                </p>
              </div>
            )}

            <p className="text-[10px] text-muted-foreground/50 leading-relaxed border-t border-border/40 pt-3">
              This AI prediction is intended for research assistance only. It does not constitute a
              clinical diagnosis. Always confirm findings with a qualified pathologist.
            </p>
          </motion.div>

          {/* Individual models */}
          {data.individual_predictions && data.individual_predictions.length > 0 && (
            <IndividualModelsCard models={data.individual_predictions} />
          )}
        </div>

        {/* Right sidebar */}
        <div className="space-y-4 lg:sticky lg:top-6 lg:self-start">
          {/* Image metadata */}
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, delay: 0.1 }}
            className="rounded-xl border border-border bg-card p-4 space-y-3"
          >
            <div className="flex items-center gap-2">
              <Image className="h-4 w-4 text-primary" />
              <h3 className="text-sm font-semibold">Image Metadata</h3>
            </div>
            <div className="space-y-0.5">
              <MetaRow label="Filename" value={data.image_metadata.filename} />
              <MetaRow label="Format" value={data.image_metadata.content_type} />
              <MetaRow
                label="Size"
                value={`${(data.image_metadata.size_bytes / 1024 / 1024).toFixed(2)} MB`}
              />
              <MetaRow
                label="Dimensions"
                value={
                  data.image_metadata.width && data.image_metadata.height
                    ? `${data.image_metadata.width} × ${data.image_metadata.height} px`
                    : null
                }
              />
            </div>
          </motion.div>

          {/* Runtime info */}
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, delay: 0.15 }}
            className="rounded-xl border border-border bg-card p-4 space-y-3"
          >
            <div className="flex items-center gap-2">
              <Server className="h-4 w-4 text-primary" />
              <h3 className="text-sm font-semibold">Runtime Info</h3>
            </div>
            <div className="space-y-0.5">
              <MetaRow
                label="Processing time"
                value={
                  data.runtime_info.processing_time_ms !== null
                    ? `${data.runtime_info.processing_time_ms.toFixed(1)} ms`
                    : null
                }
              />
              <MetaRow label="Model manifest" value={data.runtime_info.model_manifest_version} />
            </div>
            {data.runtime_info.processing_time_ms === null && data.runtime_info.model_manifest_version === null && (
              <p className="text-xs text-muted-foreground/50">Runtime details not recorded for this prediction.</p>
            )}
          </motion.div>

          {/* Record IDs */}
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, delay: 0.2 }}
            className="rounded-xl border border-border bg-card p-4 space-y-2"
          >
            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Record IDs</h3>
            <div className="space-y-1.5">
              <div>
                <p className="text-[10px] text-muted-foreground/60 mb-0.5">History ID</p>
                <p className="font-mono text-[11px] break-all">{data.history_id}</p>
              </div>
              <div>
                <p className="text-[10px] text-muted-foreground/60 mb-0.5">Request ID</p>
                <p className="font-mono text-[11px] break-all">{data.request_id}</p>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </motion.div>
  );
}
