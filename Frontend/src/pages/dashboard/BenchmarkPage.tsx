import { SectionTitle } from '@/components/ui/SectionTitle';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { MetricCard } from '@/components/ui/Card';
import { DemoDataBanner } from '@/components/ui/DemoDataBanner';
import { formatPercent, formatInferenceTime } from '@/utils/formatters';

// DEMO DATA — the backend has no benchmarking/offline-evaluation endpoint.
// The real model manifest (see AdminModelsPage, GET /system/models) has
// only 3 models — MobileNetV2, DenseNet121, and an EfficientNetV2B0+ResNet50
// fusion — and carries no accuracy/precision/recall/F1/AUC fields at all.
// Everything below is illustrative only.
const BENCHMARK_DATA = [
  { model: 'ViT-B16', accuracy: 0.991, precision: 0.989, recall: 0.993, f1: 0.991, auc: 0.999, ms: 820 },
  { model: 'EfficientNetB4', accuracy: 0.989, precision: 0.987, recall: 0.991, f1: 0.989, auc: 0.998, ms: 640 },
  { model: 'DenseNet121', accuracy: 0.981, precision: 0.979, recall: 0.983, f1: 0.981, auc: 0.997, ms: 510 },
  { model: 'ResNet50', accuracy: 0.974, precision: 0.972, recall: 0.976, f1: 0.974, auc: 0.995, ms: 380 },
  { model: 'InceptionV3', accuracy: 0.969, precision: 0.967, recall: 0.971, f1: 0.969, auc: 0.994, ms: 450 },
  { model: 'VGG16', accuracy: 0.961, precision: 0.958, recall: 0.964, f1: 0.961, auc: 0.992, ms: 720 },
];

export default function BenchmarkPage() {
  return (
    <div className="space-y-5">
      <SectionTitle
        title="Model Benchmark"
        description="Performance metrics across the LC25000 histopathology dataset"
      />

      <DemoDataBanner feature="model benchmarking" />

      {/* Summary metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricCard title="Dataset Size" value="25,000" unit="images" description="LC25000 dataset" />
        <MetricCard title="Ensemble Accuracy" value="99.1" unit="%" description="Weighted voting" />
        <MetricCard title="Best Model" value="ViT-B16" description="99.1% accuracy" />
        <MetricCard title="Fastest Model" value="ResNet50" description="380ms avg. inference" />
      </div>

      {/* Benchmark table */}
      <Card padding="none">
        <CardHeader className="px-5 pt-5">
          <CardTitle>Per-Model Performance</CardTitle>
          <CardDescription>Evaluated on the LC25000 test split (5,000 images, 5 classes)</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border">
                  {['Model', 'Accuracy', 'Precision', 'Recall', 'F1 Score', 'AUC', 'Inference'].map((h) => (
                    <th key={h} className="px-4 py-2.5 text-left font-medium text-muted-foreground uppercase tracking-wider whitespace-nowrap">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {BENCHMARK_DATA.map((row, i) => (
                  <tr key={row.model} className="hover:bg-muted/20 transition-colors">
                    <td className="px-4 py-3 font-mono font-medium">
                      <div className="flex items-center gap-2">
                        {row.model}
                        {i === 0 && <Badge variant="success" className="text-[10px]">Best</Badge>}
                      </div>
                    </td>
                    <td className="px-4 py-3 font-mono text-primary">{formatPercent(row.accuracy)}</td>
                    <td className="px-4 py-3 font-mono">{formatPercent(row.precision)}</td>
                    <td className="px-4 py-3 font-mono">{formatPercent(row.recall)}</td>
                    <td className="px-4 py-3 font-mono">{formatPercent(row.f1)}</td>
                    <td className="px-4 py-3 font-mono">{formatPercent(row.auc)}</td>
                    <td className="px-4 py-3 font-mono text-muted-foreground">{formatInferenceTime(row.ms)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Accuracy bars */}
      <Card>
        <CardHeader>
          <CardTitle>Accuracy Comparison</CardTitle>
          <CardDescription>Sorted by classification accuracy</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {BENCHMARK_DATA.map((row) => (
            <div key={row.model} className="flex items-center gap-3">
              <span className="w-28 shrink-0 font-mono text-xs">{row.model}</span>
              <div className="flex-1 h-2 rounded-full bg-secondary overflow-hidden">
                <div
                  className="h-full rounded-full bg-primary transition-all duration-500"
                  style={{ width: `${row.accuracy * 100}%` }}
                />
              </div>
              <span className="w-14 text-right font-mono text-xs text-muted-foreground">
                {formatPercent(row.accuracy)}
              </span>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
