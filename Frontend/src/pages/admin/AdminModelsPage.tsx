import { Cpu, Plus } from 'lucide-react';
import { SectionTitle } from '@/components/ui/SectionTitle';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { formatPercent, formatInferenceTime, formatModelParams } from '@/utils/formatters';
import type { ModelArchitecture } from '@/types';

const MODELS = [
  { id: 'm1', name: 'ViT-B16', architecture: 'ViT-B16' as ModelArchitecture, version: '1.2.0', status: 'active', accuracy: 0.991, parameters: 86_000_000, inferenceTimeMs: 820, trainedOn: '2024-06-01' },
  { id: 'm2', name: 'EfficientNetB4', architecture: 'EfficientNetB4' as ModelArchitecture, version: '2.1.0', status: 'active', accuracy: 0.989, parameters: 19_300_000, inferenceTimeMs: 640, trainedOn: '2024-05-15' },
  { id: 'm3', name: 'DenseNet121', architecture: 'DenseNet121' as ModelArchitecture, version: '1.0.3', status: 'active', accuracy: 0.981, parameters: 7_978_856, inferenceTimeMs: 510, trainedOn: '2024-04-20' },
  { id: 'm4', name: 'ResNet50', architecture: 'ResNet50' as ModelArchitecture, version: '3.0.1', status: 'active', accuracy: 0.974, parameters: 25_600_000, inferenceTimeMs: 380, trainedOn: '2024-03-10' },
  { id: 'm5', name: 'InceptionV3', architecture: 'InceptionV3' as ModelArchitecture, version: '1.1.0', status: 'active', accuracy: 0.969, parameters: 23_900_000, inferenceTimeMs: 450, trainedOn: '2024-02-28' },
  { id: 'm6', name: 'VGG16', architecture: 'VGG16' as ModelArchitecture, version: '1.0.0', status: 'active', accuracy: 0.961, parameters: 138_400_000, inferenceTimeMs: 720, trainedOn: '2024-01-05' },
];

export default function AdminModelsPage() {
  return (
    <div className="space-y-5">
      <SectionTitle
        title="Model Management"
        description="Manage the ensemble model registry"
        action={
          <Button size="sm">
            <Plus className="h-3.5 w-3.5" />
            Register model
          </Button>
        }
      />

      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
        {MODELS.map((m) => (
          <Card key={m.id} className="space-y-4 hover:border-primary/30 transition-colors">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-2.5">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
                  <Cpu className="h-4 w-4 text-primary" />
                </div>
                <div>
                  <p className="text-sm font-semibold font-mono">{m.name}</p>
                  <p className="text-[10px] text-muted-foreground">v{m.version}</p>
                </div>
              </div>
              <Badge variant="success" dot className="text-[10px] capitalize">{m.status}</Badge>
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>
                <p className="text-muted-foreground text-[10px]">Accuracy</p>
                <p className="font-mono font-semibold text-primary">{formatPercent(m.accuracy)}</p>
              </div>
              <div>
                <p className="text-muted-foreground text-[10px]">Inference</p>
                <p className="font-mono font-semibold">{formatInferenceTime(m.inferenceTimeMs)}</p>
              </div>
              <div>
                <p className="text-muted-foreground text-[10px]">Parameters</p>
                <p className="font-mono font-semibold">{formatModelParams(m.parameters)}</p>
              </div>
              <div>
                <p className="text-muted-foreground text-[10px]">Trained</p>
                <p className="font-mono font-semibold">{m.trainedOn}</p>
              </div>
            </div>

            <div className="flex gap-2 pt-1 border-t border-border">
              <Button variant="ghost" size="xs" className="flex-1">View metrics</Button>
              <Button variant="outline" size="xs" className="flex-1">Configure</Button>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
