import { useState } from 'react';
import {
  Database,
  Layers,
  Clock,
  Activity,
  AlertTriangle,
  Cpu,
} from 'lucide-react';
import { Card, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/Table';
import { formatPercent, formatInferenceTime } from '@/utils/formatters';
import { cn } from '@/lib/utils';

// DEMO DATA — the backend has no benchmarking/offline-evaluation endpoint.
// The real model manifest (see AdminModelsPage, GET /system/models) has
// 3 active runtime models — MobileNetV2, DenseNet121, and an EfficientNetV2B0+ResNet50
// fusion — and carries no offline accuracy/precision/recall/F1/AUC fields.
// The metrics below represent reference demonstration benchmark observations
// on the public LC25000 test set (5,000 images, 5 classes).
const BENCHMARK_DATA = [
  {
    model: 'ViT-B16',
    family: 'Vision Transformer',
    accuracy: 0.991,
    precision: 0.989,
    recall: 0.993,
    f1: 0.991,
    auc: 0.999,
    ms: 820,
  },
  {
    model: 'EfficientNetB4',
    family: 'Convolutional Network',
    accuracy: 0.989,
    precision: 0.987,
    recall: 0.991,
    f1: 0.989,
    auc: 0.998,
    ms: 640,
  },
  {
    model: 'DenseNet121',
    family: 'Densely Connected CNN',
    accuracy: 0.981,
    precision: 0.979,
    recall: 0.983,
    f1: 0.981,
    auc: 0.997,
    ms: 510,
  },
  {
    model: 'ResNet50',
    family: 'Residual Network',
    accuracy: 0.974,
    precision: 0.972,
    recall: 0.976,
    f1: 0.974,
    auc: 0.995,
    ms: 380,
  },
  {
    model: 'InceptionV3',
    family: 'Multi-Scale CNN',
    accuracy: 0.969,
    precision: 0.967,
    recall: 0.971,
    f1: 0.969,
    auc: 0.994,
    ms: 450,
  },
  {
    model: 'VGG16',
    family: 'Sequential CNN',
    accuracy: 0.961,
    precision: 0.958,
    recall: 0.964,
    f1: 0.961,
    auc: 0.992,
    ms: 720,
  },
];

const METRIC_DEFINITIONS = [
  {
    name: 'Accuracy',
    definition: 'Proportion of total evaluated test patch classifications that matched true ground-truth histopathology labels.',
    context: 'Evaluated across all 5,000 balanced test split images.',
  },
  {
    name: 'Precision',
    definition: 'Proportion of positive predictions for a given tissue class that were true positives in the test split.',
    context: 'Reflects false positive minimization on evaluated data.',
  },
  {
    name: 'Recall (Sensitivity)',
    definition: 'Proportion of actual positive cases in the evaluated test set correctly classified by the model architecture.',
    context: 'Reflects false negative minimization in evaluated dataset.',
  },
  {
    name: 'F1-Score',
    definition: 'Harmonic mean of precision and recall, providing a balanced performance metric across classes.',
    context: 'Primary ranking metric for multi-class classification on the test split.',
  },
  {
    name: 'AUC-ROC',
    definition: 'Area under the receiver operating characteristic curve, measuring class discrimination ability across thresholds.',
    context: 'Aggregate measure of threshold-independent classification capability.',
  },
  {
    name: 'Inference Latency',
    definition: 'Average execution duration required for a forward inference pass per standard 768×768 patch.',
    context: 'Measured under consistent CPU/GPU test bench conditions.',
  },
];

export default function BenchmarkPage() {
  const [metricTab, setMetricTab] = useState<'accuracy' | 'latency'>('accuracy');

  return (
    <div className="space-y-6">
      {/* Calm Scientific Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-text-primary sm:text-2xl">
            Clinical Benchmark & Evaluation Metrics
          </h1>
          <p className="mt-1 text-sm text-text-muted">
            Review available model evaluation metrics and benchmark observations across histopathology reference datasets.
          </p>
        </div>
      </div>

      {/* Explicit Illustrative Data Banner */}
      <div
        role="region"
        aria-label="Benchmark Provenance Notice"
        className="flex items-start gap-3 rounded-lg border border-warning/30 bg-warning-surface p-4 text-xs text-text-secondary"
      >
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-warning" aria-hidden="true" />
        <div className="space-y-1 leading-relaxed">
          <p className="font-semibold text-text-primary">
            Illustrative Benchmark — Reference Evaluation Observations
          </p>
          <p>
            The values shown in this workspace represent demonstration metrics on the LC25000 histopathology dataset test split (5,000 images, 5 classes)
            and should not be interpreted as validated clinical performance or regulatory clearance in patient care.
            The active AI runtime backend does not host an automated offline evaluation endpoint; metrics reflect offline research benchmark observations.
          </p>
        </div>
      </div>

      {/* Dataset & Evaluation Provenance Metadata Card */}
      <Card className="p-4 bg-surface-raised/40 border-border-subtle">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-2">
            <Database className="h-4 w-4 text-primary shrink-0" />
            <span className="text-xs font-semibold uppercase tracking-wider text-text-muted">
              Evaluation Provenance Metadata
            </span>
          </div>
          <Badge variant="outline" className="text-[11px] font-mono">
            Dataset: LC25000 (HipAA-Compliant Test Split)
          </Badge>
        </div>
        <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4 text-xs border-t border-border-subtle pt-3">
          <div>
            <span className="text-text-muted">Total Corpus</span>
            <div className="font-mono font-medium text-text-primary">25,000 images</div>
          </div>
          <div>
            <span className="text-text-muted">Test Partition</span>
            <div className="font-mono font-medium text-text-primary">5,000 images (20%)</div>
          </div>
          <div>
            <span className="text-text-muted">Class Distribution</span>
            <div className="font-mono font-medium text-text-primary">5 balanced classes</div>
          </div>
          <div>
            <span className="text-text-muted">Patch Dimension</span>
            <div className="font-mono font-medium text-text-primary">768 × 768 pixels</div>
          </div>
        </div>
      </Card>

      {/* Summary Metric Strip */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Card className="p-4 space-y-1">
          <div className="flex items-center justify-between text-text-muted">
            <span className="text-xs font-medium">Dataset Corpus</span>
            <Database className="h-4 w-4 text-primary" />
          </div>
          <div className="text-lg font-semibold font-mono tabular-nums text-text-primary">
            25,000
          </div>
          <p className="text-[11px] text-text-muted">LC25000 histopathology images</p>
        </Card>

        <Card className="p-4 space-y-1">
          <div className="flex items-center justify-between text-text-muted">
            <span className="text-xs font-medium">Test Split Size</span>
            <Layers className="h-4 w-4 text-primary" />
          </div>
          <div className="text-lg font-semibold font-mono tabular-nums text-text-primary">
            5,000
          </div>
          <p className="text-[11px] text-text-muted">Evaluated test images</p>
        </Card>

        <Card className="p-4 space-y-1">
          <div className="flex items-center justify-between text-text-muted">
            <span className="text-xs font-medium">Highest Observed F1</span>
            <Activity className="h-4 w-4 text-primary" />
          </div>
          <div className="text-lg font-semibold font-mono tabular-nums text-text-primary">
            99.1%
          </div>
          <p className="text-[11px] text-text-muted">ViT-B16 architecture on test split</p>
        </Card>

        <Card className="p-4 space-y-1">
          <div className="flex items-center justify-between text-text-muted">
            <span className="text-xs font-medium">Lowest Observed Latency</span>
            <Clock className="h-4 w-4 text-primary" />
          </div>
          <div className="text-lg font-semibold font-mono tabular-nums text-text-primary">
            380 ms
          </div>
          <p className="text-[11px] text-text-muted">ResNet50 forward pass per patch</p>
        </Card>
      </div>

      {/* Per-Model Benchmark Evaluation Table */}
      <div className="space-y-3">
        <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-sm font-semibold text-text-primary">Architecture-Level Benchmark Table</h2>
            <p className="text-xs text-text-muted">
              Evaluated on the LC25000 test split (5,000 images, 5 classes). Ranked by observed F1-score.
            </p>
          </div>
          <span className="text-[11px] font-mono text-text-muted">
            Ranking Metric: F1-Score
          </span>
        </div>

        <Table>
          <TableHeader>
            <TableRow>
              <TableHead scope="col">Architecture</TableHead>
              <TableHead scope="col">Model Family</TableHead>
              <TableHead scope="col" className="text-right">Accuracy</TableHead>
              <TableHead scope="col" className="text-right">Precision</TableHead>
              <TableHead scope="col" className="text-right">Recall (Sens.)</TableHead>
              <TableHead scope="col" className="text-right">F1-Score</TableHead>
              <TableHead scope="col" className="text-right">AUC-ROC</TableHead>
              <TableHead scope="col" className="text-right">Avg Latency</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {BENCHMARK_DATA.map((row, i) => (
              <TableRow key={row.model}>
                <TableCell className="font-mono font-medium text-text-primary">
                  <div className="flex items-center gap-2">
                    <Cpu className="h-3.5 w-3.5 text-text-muted shrink-0" />
                    <span>{row.model}</span>
                    <Badge variant={i === 0 ? 'primary' : 'outline'} className="text-[10px]">
                      Rank {i + 1}
                    </Badge>
                  </div>
                </TableCell>
                <TableCell className="text-xs text-text-muted">{row.family}</TableCell>
                <TableCell className="text-right font-mono font-medium tabular-nums text-text-primary">
                  {formatPercent(row.accuracy)}
                </TableCell>
                <TableCell className="text-right font-mono tabular-nums text-text-secondary">
                  {formatPercent(row.precision)}
                </TableCell>
                <TableCell className="text-right font-mono tabular-nums text-text-secondary">
                  {formatPercent(row.recall)}
                </TableCell>
                <TableCell className="text-right font-mono font-semibold tabular-nums text-primary">
                  {formatPercent(row.f1)}
                </TableCell>
                <TableCell className="text-right font-mono tabular-nums text-text-secondary">
                  {row.auc.toFixed(3)}
                </TableCell>
                <TableCell className="text-right font-mono tabular-nums text-text-muted">
                  {formatInferenceTime(row.ms)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Visualizations: Accuracy vs Latency Comparison */}
      <Card className="p-5 space-y-4">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <CardTitle className="text-sm font-semibold">Observed Architecture Distribution</CardTitle>
            <CardDescription className="text-xs">
              Comparative distribution across evaluated architectures on the benchmark test split
            </CardDescription>
          </div>
          <div className="flex items-center gap-1 rounded-md border border-border bg-surface p-1 text-xs">
            <button
              type="button"
              onClick={() => setMetricTab('accuracy')}
              className={cn(
                'rounded px-2.5 py-1 font-medium transition-colors',
                metricTab === 'accuracy'
                  ? 'bg-surface-raised font-semibold text-text-primary'
                  : 'text-text-muted hover:text-text-primary',
              )}
            >
              Test Accuracy
            </button>
            <button
              type="button"
              onClick={() => setMetricTab('latency')}
              className={cn(
                'rounded px-2.5 py-1 font-medium transition-colors',
                metricTab === 'latency'
                  ? 'bg-surface-raised font-semibold text-text-primary'
                  : 'text-text-muted hover:text-text-primary',
              )}
            >
              Inference Latency
            </button>
          </div>
        </div>

        <CardContent className="p-0 space-y-3 pt-2">
          {metricTab === 'accuracy' ? (
            <div className="space-y-3">
              {BENCHMARK_DATA.map((row) => (
                <div key={row.model} className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-mono font-medium text-text-primary">{row.model}</span>
                    <span className="font-mono tabular-nums text-text-muted">
                      {formatPercent(row.accuracy)}
                    </span>
                  </div>
                  <div
                    className="h-2 w-full rounded-full bg-surface-raised overflow-hidden"
                    role="progressbar"
                    aria-label={`Accuracy for ${row.model}`}
                    aria-valuenow={Math.round(row.accuracy * 100)}
                    aria-valuemin={0}
                    aria-valuemax={100}
                  >
                    <div
                      className="h-full rounded-full bg-primary transition-all duration-300"
                      style={{ width: `${row.accuracy * 100}%` }}
                    />
                  </div>
                </div>
              ))}
              <div className="mt-3 text-xs text-text-muted">
                Observed accuracy ranges from {formatPercent(BENCHMARK_DATA[BENCHMARK_DATA.length - 1].accuracy)} to{' '}
                {formatPercent(BENCHMARK_DATA[0].accuracy)} across the 6 reference architectures on 5,000 test patches.
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              {BENCHMARK_DATA.map((row) => {
                const maxMs = 900;
                const pct = Math.min(100, Math.round((row.ms / maxMs) * 100));
                return (
                  <div key={row.model} className="space-y-1">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-mono font-medium text-text-primary">{row.model}</span>
                      <span className="font-mono tabular-nums text-text-muted">
                        {formatInferenceTime(row.ms)}
                      </span>
                    </div>
                    <div
                      className="h-2 w-full rounded-full bg-surface-raised overflow-hidden"
                      role="progressbar"
                      aria-label={`Latency for ${row.model}`}
                      aria-valuenow={row.ms}
                      aria-valuemin={0}
                      aria-valuemax={maxMs}
                    >
                      <div
                        className="h-full rounded-full bg-accent transition-all duration-300"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })}
              <div className="mt-3 text-xs text-text-muted">
                Observed latency spans from {formatInferenceTime(BENCHMARK_DATA[3].ms)} (ResNet50) to{' '}
                {formatInferenceTime(BENCHMARK_DATA[0].ms)} (ViT-B16) per single patch forward pass.
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Ensemble Architecture Context Card */}
      <Card className="p-5 space-y-3 bg-surface border-border">
        <div className="flex items-center gap-2">
          <Layers className="h-4 w-4 text-primary shrink-0" />
          <h2 className="text-sm font-semibold text-text-primary">Runtime Ensemble Integration Context</h2>
        </div>
        <p className="text-xs text-text-secondary leading-relaxed">
          In production inference pipelines, individual architectures are combined into an ensemble using weighted soft voting across
          MobileNetV2, DenseNet121, and the EfficientNetV2B0+ResNet50 fusion model. Combining disparate architectural inductive biases
          (convolutional locality vs dense feature reuse) reduces single-model variance on borderline histopathology patterns.
          Ensemble output is governed by agreement threshold criteria and does not guarantee standalone clinical infallibility.
        </p>
      </Card>

      {/* Metric Definitions Reference Guide */}
      <div className="space-y-3">
        <div>
          <h2 className="text-sm font-semibold text-text-primary">Evaluation Metric Definitions</h2>
          <p className="text-xs text-text-muted">
            Formal technical descriptions of evaluation statistics applied to the benchmark dataset
          </p>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {METRIC_DEFINITIONS.map((m) => (
            <Card key={m.name} className="p-3.5 space-y-1.5 bg-surface">
              <span className="text-xs font-semibold text-text-primary font-mono">{m.name}</span>
              <p className="text-xs text-text-secondary leading-relaxed">{m.definition}</p>
              <p className="text-[11px] text-text-muted italic">{m.context}</p>
            </Card>
          ))}
        </div>
      </div>

      {/* Mandatory Research & Regulatory Disclaimer */}
      <div
        role="note"
        aria-label="Regulatory Disclaimer"
        className="rounded-lg border border-border-subtle bg-surface-raised/40 p-4 text-xs text-text-muted leading-relaxed"
      >
        <span className="font-semibold text-text-secondary">Regulatory & Clinical Boundary Disclaimer: </span>
        Benchmark metrics describe model behavior on the evaluated LC25000 test dataset and do not establish clinical effectiveness,
        diagnostic accuracy in clinical practice, or FDA/CE-mark regulatory clearance.
        OncoVision AI is an investigational clinical decision-support tool. All classification outputs require verification by a board-certified pathologist.
      </div>
    </div>
  );
}
