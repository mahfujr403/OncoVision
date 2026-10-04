import { Cpu, Layers, HardDrive, CheckCircle2, Box, Info } from 'lucide-react';
import { SectionTitle } from '@/components/ui/SectionTitle';
import { Card, StatCard } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { ErrorState } from '@/components/ui/ErrorState';
import { Skeleton } from '@/components/ui/Skeleton';
import { useSystemModels } from '@/hooks/queries/useSystemModels';

function getDiseaseBadgeVariant(
  label: string,
): 'lungAca' | 'lungScc' | 'colonAca' | 'lungBenign' | 'colonBenign' | 'secondary' {
  const norm = label.toLowerCase();
  if (norm.includes('lung') && (norm.includes('adeno') || norm.includes('aca'))) return 'lungAca';
  if (norm.includes('lung') && (norm.includes('squamous') || norm.includes('scc'))) return 'lungScc';
  if (norm.includes('colon') && (norm.includes('adeno') || norm.includes('aca'))) return 'colonAca';
  if (norm.includes('lung') && norm.includes('benign')) return 'lungBenign';
  if (norm.includes('colon') && norm.includes('benign')) return 'colonBenign';
  return 'secondary';
}

export default function AdminModelsPage() {
  const { data, isLoading, isError, refetch } = useSystemModels();

  return (
    <div className="space-y-6">
      {/* Workspace Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <SectionTitle
          title="Model Management"
          description="Live model registry and runtime manifest deployed within the AI inference pipeline."
        />
        {data && (
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="font-mono text-xs px-2.5 py-1">
              <Layers className="h-3.5 w-3.5 mr-1.5 text-primary" />
              <span className="text-text-muted">Manifest</span>
              <span className="ml-1 font-semibold text-text-primary">v{data.manifest_version}</span>
            </Badge>
          </div>
        )}
      </div>

      {isError ? (
        <ErrorState message="Could not retrieve the registered model manifest from the system runtime." onRetry={() => refetch()} />
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
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <Card key={i} className="space-y-4 p-5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Skeleton className="h-9 w-9 rounded-lg" />
                    <div className="space-y-1.5">
                      <Skeleton className="h-4 w-32" />
                      <Skeleton className="h-3 w-16" />
                    </div>
                  </div>
                  <Skeleton className="h-5 w-16 rounded-full" />
                </div>
                <Skeleton className="h-10 w-full" />
                <div className="grid grid-cols-2 gap-2">
                  <Skeleton className="h-8 w-full" />
                  <Skeleton className="h-8 w-full" />
                </div>
              </Card>
            ))}
          </div>
        </div>
      ) : (
        <>
          {/* Registry Overview Statistics */}
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <StatCard
              label="Manifest Version"
              value={`v${data.manifest_version}`}
              icon={<Layers className="h-4 w-4" />}
            />
            <StatCard
              label="Registered Models"
              value={String(data.total_models)}
              icon={<Box className="h-4 w-4" />}
            />
            <StatCard
              label="Pipeline Enabled"
              value={String(data.enabled_models)}
              icon={<CheckCircle2 className="h-4 w-4" />}
            />
            <StatCard
              label="Locally Cached"
              value={String(data.available_models)}
              icon={<HardDrive className="h-4 w-4" />}
            />
          </div>

          {/* Model Registry Cards */}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {data.models.map((m) => (
              <Card
                key={m.id}
                className="space-y-4 p-5 hover:border-primary/40 transition-colors flex flex-col justify-between"
              >
                <div className="space-y-3">
                  {/* Identity & Status */}
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-3">
                      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-surface-raised border border-border text-primary">
                        <Cpu className="h-5 w-5" />
                      </div>
                      <div className="min-w-0">
                        <h3 className="text-sm font-bold text-text-primary truncate" title={m.display_name}>
                          {m.display_name}
                        </h3>
                        <p className="text-[11px] text-text-muted font-mono">
                          ID: {m.id} · <span className="text-primary font-semibold">v{m.version}</span>
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Operational Status Badges */}
                  <div className="flex flex-wrap items-center gap-1.5 pt-1">
                    <Badge variant={m.enabled ? 'success' : 'secondary'} dot className="text-[10px]">
                      {m.enabled ? 'Pipeline Enabled' : 'Disabled'}
                    </Badge>
                    <Badge variant={m.is_cached ? 'info' : 'outline'} className="text-[10px]">
                      {m.is_cached ? 'Cached in Memory' : 'Remote Cold'}
                    </Badge>
                  </div>

                  {/* Description if present */}
                  {m.description && (
                    <p className="text-xs text-text-secondary leading-relaxed line-clamp-2">
                      {m.description}
                    </p>
                  )}

                  {/* Model Specifications Grid */}
                  <div className="grid grid-cols-2 gap-2.5 p-3 rounded-lg bg-surface-raised/40 border border-border-subtle text-xs">
                    <SpecItem label="Framework" value={m.framework} />
                    <SpecItem label="Binary Format" value={m.format} />
                    <SpecItem label="Ensemble Weight" value={m.ensemble_weight.toFixed(2)} />
                    <SpecItem label="Priority Rank" value={`Rank ${m.priority}`} />
                    <SpecItem
                      label="Input Dimensions"
                      value={Array.isArray(m.input_size) ? m.input_size.join(' × ') : String(m.input_size)}
                    />
                    <SpecItem label="Class Count" value={`${m.num_classes} categories`} />
                  </div>
                </div>

                {/* Target Class Labels */}
                {m.class_labels.length > 0 && (
                  <div className="space-y-1.5 border-t border-border pt-3">
                    <span className="text-[10px] text-text-muted uppercase tracking-wider font-mono font-medium block">
                      Target Pathology Classes
                    </span>
                    <div className="flex flex-wrap gap-1">
                      {m.class_labels.map((label) => (
                        <Badge
                          key={label}
                          variant={getDiseaseBadgeVariant(label)}
                          className="text-[10px] px-2 py-0.5"
                        >
                          {label}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </Card>
            ))}
          </div>

          {/* Operational Infrastructure Disclaimer */}
          <div className="flex items-start gap-3 p-4 rounded-lg border border-border bg-surface-raised/50 text-xs text-text-secondary">
            <Info className="h-4 w-4 text-text-muted shrink-0 mt-0.5" />
            <div className="space-y-1">
              <p className="font-semibold text-text-primary">Model Manifest Provenance</p>
              <p className="leading-relaxed">
                Model configurations and weights reflect the live manifest provided by the AI runtime engine.
                Weight distribution and runtime priority are strictly read from the deployed service manifest.
              </p>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function SpecItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span className="text-text-muted text-[10px] uppercase font-mono block tracking-tight">{label}</span>
      <span className="font-mono text-xs font-semibold text-text-primary truncate block mt-0.5">{value}</span>
    </div>
  );
}
