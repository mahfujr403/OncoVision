import { getAllHistoryRecordsForAnalytics } from './mockHistory';
import type { AnalyticsSummary } from '@/types/reports';
import type { PredictionStatus } from '@/types/prediction';

/** SIMULATION ONLY — see the header comment in src/types/reports.ts. */
export async function simulateAnalyticsRequest(): Promise<AnalyticsSummary> {
  await new Promise((res) => setTimeout(res, 500 + Math.random() * 400));

  const records = getAllHistoryRecordsForAnalytics();
  const nonFailed = records.filter((r) => r.status !== 'failed');

  const statusCounts: Record<PredictionStatus, number> = {
    success: 0,
    partial_success: 0,
    failed: 0,
    pending: 0,
  };
  for (const r of records) statusCounts[r.status] += 1;

  const classCounts = new Map<string, number>();
  for (const r of nonFailed) {
    classCounts.set(r.predicted_class, (classCounts.get(r.predicted_class) ?? 0) + 1);
  }
  const class_distribution = Array.from(classCounts.entries())
    .map(([predicted_class, count]) => ({ predicted_class, count }))
    .sort((a, b) => b.count - a.count);

  const buckets = [
    { label: '0–20%', min: 0, max: 20 },
    { label: '20–40%', min: 20, max: 40 },
    { label: '40–60%', min: 40, max: 60 },
    { label: '60–80%', min: 60, max: 80 },
    { label: '80–100%', min: 80, max: 100.01 },
  ];
  const confidence_distribution = buckets.map((b) => ({
    bucket_label: b.label,
    count: nonFailed.filter((r) => r.confidence >= b.min && r.confidence < b.max).length,
  }));

  const average_confidence =
    nonFailed.length > 0
      ? Math.round((nonFailed.reduce((sum, r) => sum + r.confidence, 0) / nonFailed.length) * 10) / 10
      : 0;
  const average_processing_time_ms =
    records.length > 0
      ? Math.round(records.reduce((sum, r) => sum + r.processing_time_ms, 0) / records.length)
      : 0;

  return {
    total_predictions: records.length,
    status_counts: statusCounts,
    average_confidence,
    average_processing_time_ms,
    class_distribution,
    confidence_distribution,
  };
}

/** Client-side CSV built from the same simulated dataset shown on screen. */
export function buildSimulatedCsv(): string {
  const records = getAllHistoryRecordsForAnalytics();
  const header = [
    'history_id',
    'created_at',
    'status',
    'predicted_class',
    'confidence',
    'agreement_ratio',
    'participating_models',
    'processing_time_ms',
  ];
  const rows = records.map((r) =>
    [
      r.history_id,
      r.created_at,
      r.status,
      r.predicted_class,
      r.confidence,
      r.agreement_ratio,
      r.participating_models,
      r.processing_time_ms,
    ].join(',')
  );
  return [header.join(','), ...rows].join('\n');
}
