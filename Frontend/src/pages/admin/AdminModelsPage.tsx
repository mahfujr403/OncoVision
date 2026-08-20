import { Cpu, Layers } from 'lucide-react';
import { SectionTitle } from '@/components/ui/SectionTitle';
import { Card, StatCard } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { ErrorState } from '@/components/ui/ErrorState';
import { Skeleton } from '@/components/ui/Skeleton';
import { useSystemModels } from '@/hooks/queries/useSystemModels';

// NOTE: the previous version of this page showed 6 fabricated models
// (ViT-B16, EfficientNetB4, ResNet50, InceptionV3, VGG16 — none of which
// exist in the backend's model manifest) with fake accuracy/parameter
// counts and a fake "trained on" date, plus non-existent "Register
// model"/"Configure" actions (there is no model-management CRUD endpoint).
// This page now reflects exactly GET /api/v1/system/models, verified
// against app/ml/metadata/metadata_service.py — the real 3-model manifest,
// with only the fields the backend actually returns: framework, ensemble
// weight, input size, class labels, priority, enabled/cached state. There
// is no accuracy/precision/recall/F1/AUC anywhere in this response — the
// backend does not track offline evaluation metrics per model today.
export default function AdminModelsPage() {
  const { data, isLoading, isError, refetch } = useSystemModels();

  return (
    <div className="space-y-5">
      <SectionTitle title="Model Registry" description="Live model manifest served by the AI runtime" />

      {isError ? (
        <ErrorState message="Couldn't load the model registry." onRetry={() => refetch()} />
      ) : isLoading || !data ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Card key={i} className="space-y-3">
              <Skeleton className="h-9 w-9 rounded-lg" />
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-3 w-full" />
            </Card>
          ))}
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <StatCard label="Manifest Version" value={data.manifest_version} icon={<Layers className="h-4 w-4" />} />
            <StatCard label="Total Models" value={String(data.total_models)} icon={<Cpu className="h-4 w-4" />} />
            <StatCard label="Enabled" value={String(data.enabled_models)} />
            <StatCard label="Available (cached)" value={String(data.available_models)} />
          </div>

          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {data.models.map((m) => (
              <Card key={m.id} className="space-y-4 hover:border-primary/30 transition-colors">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2.5">
                    <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
                      <Cpu className="h-4 w-4 text-primary" />
                    </div>
                    <div>
                      <p className="text-sm font-semibold">{m.display_name}</p>
                      <p className="text-[10px] text-muted-foreground font-mono">v{m.version}</p>
                    </div>
                  </div>
                  <div className="flex flex-col items-end gap-1">
                    <Badge variant={m.enabled ? 'success' : 'secondary'} dot className="text-[10px]">
                      {m.enabled ? 'Enabled' : 'Disabled'}
                    </Badge>
                    <Badge variant={m.is_cached ? 'info' : 'outline'} className="text-[10px]">
                      {m.is_cached ? 'Cached locally' : 'Not cached'}
                    </Badge>
                  </div>
                </div>

                {m.description && <p className="text-xs text-muted-foreground">{m.description}</p>}

                <div className="grid grid-cols-2 gap-2 text-xs">
                  <Field label="Framework" value={m.framework} />
                  <Field label="Format" value={m.format} />
                  <Field label="Ensemble weight" value={m.ensemble_weight.toFixed(2)} />
                  <Field label="Priority" value={String(m.priority)} />
                  <Field
                    label="Input size"
                    value={Array.isArray(m.input_size) ? m.input_size.join('×') : String(m.input_size)}
                  />
                  <Field label="Classes" value={String(m.num_classes)} />
                </div>

                {m.class_labels.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 border-t border-border pt-3">
                    {m.class_labels.map((label) => (
                      <Badge key={label} variant="secondary" className="text-[10px]">
                        {label}
                      </Badge>
                    ))}
                  </div>
                )}
              </Card>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-muted-foreground text-[10px]">{label}</p>
      <p className="font-mono font-semibold">{value}</p>
    </div>
  );
}
