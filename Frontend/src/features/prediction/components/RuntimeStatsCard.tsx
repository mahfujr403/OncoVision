import { motion } from 'framer-motion';
import { Activity, Clock, Server } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/Badge';
import type { RuntimeStatistics, PredictionMetadata } from '@/types';

interface Props {
  stats: RuntimeStatistics;
  metadata: PredictionMetadata;
  className?: string;
}

function StatRow({ label, value }: { label: string; value: string | number | null }) {
  if (value === null || value === undefined) return null;
  return (
    <div className="flex items-center justify-between gap-4 py-1.5">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className="font-mono text-xs">{value}</span>
    </div>
  );
}

function runtimeStatusBadge(status: RuntimeStatistics['runtime_status']) {
  switch (status) {
    case 'operational':
      return <Badge variant="success" className="text-[10px]">Operational</Badge>;
    case 'degraded':
      return <Badge variant="warning" className="text-[10px]">Degraded</Badge>;
    case 'unavailable':
      return <Badge variant="destructive" className="text-[10px]">Unavailable</Badge>;
  }
}

function ms(val: number | null, label: string) {
  if (val === null) return null;
  return { label, value: `${val.toFixed(1)} ms` };
}

export function RuntimeStatsCard({ stats, metadata, className }: Props) {
  const timings = [
    ms(stats.preprocessing_time_ms, 'Preprocessing'),
    ms(stats.total_inference_time_ms, 'Total Inference'),
    ms(stats.total_execution_time_ms, 'Total Execution'),
    ms(stats.overall_processing_time_ms, 'Overall Processing'),
    { label: 'API Processing', value: `${metadata.processing_time_ms.toFixed(1)} ms` },
  ].filter(Boolean) as { label: string; value: string }[];

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.2 }}
      className={cn('rounded-xl border border-border bg-card p-5 space-y-4', className)}
    >
      <div className="flex items-center gap-2">
        <Activity className="h-4 w-4 text-primary" />
        <h3 className="text-sm font-semibold tracking-tight">Runtime Statistics</h3>
        <div className="ml-auto">{runtimeStatusBadge(stats.runtime_status)}</div>
      </div>

      {/* Model availability */}
      <div className="rounded-lg border border-border/50 bg-secondary/30 p-3 space-y-1">
        <div className="flex items-center gap-1.5 mb-2">
          <Server className="h-3.5 w-3.5 text-muted-foreground" />
          <span className="text-xs font-medium">Model Availability</span>
        </div>
        <StatRow label="Total models" value={stats.total_models} />
        <StatRow label="Loaded" value={stats.loaded_model_count} />
        <StatRow label="Participated" value={stats.participating_models} />
        <StatRow label="Successful predictions" value={stats.successful_predictions} />
        {stats.failed_predictions !== null && stats.failed_predictions > 0 && (
          <StatRow label="Failed predictions" value={stats.failed_predictions} />
        )}
      </div>

      {/* Timing */}
      {timings.length > 0 && (
        <div className="space-y-0.5">
          <div className="flex items-center gap-1.5 mb-2">
            <Clock className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-xs font-medium">Processing Times</span>
          </div>
          {timings.map(({ label, value }) => (
            <StatRow key={label} label={label} value={value} />
          ))}
        </div>
      )}

      {/* Version metadata */}
      <div className="border-t border-border/40 pt-3 space-y-1">
        <StatRow label="API version" value={metadata.api_version} />
        <StatRow label="Backend version" value={metadata.backend_version} />
        {metadata.model_manifest_version && (
          <StatRow label="Model manifest" value={metadata.model_manifest_version} />
        )}
      </div>
    </motion.div>
  );
}
