import type { HistoryFilters, HistoryRecord, PaginatedHistoryResponse } from '@/types/history';
import type { PredictionStatus } from '@/types/prediction';

/**
 * SIMULATION ONLY. See src/types/history.ts for the verification caveat on
 * the pagination envelope shape. Real integration against
 * GET /api/v1/predictions/history and GET /api/v1/predictions/history/{id}
 * is Phase 6 work — this module does not call any network endpoint.
 */

const CLASS_LABELS = [
  'lung_adenocarcinoma',
  'lung_squamous_cell_carcinoma',
  'lung_benign_tissue',
  'colon_adenocarcinoma',
  'colon_benign_tissue',
];

const MODEL_NAMES = ['EfficientNetV2B0_ResNet50_Fusion', 'DenseNet121', 'MobileNetV2'];
const STATUSES: PredictionStatus[] = ['success', 'success', 'success', 'partial_success', 'failed'];

function pick<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}

function id(prefix: string) {
  return `${prefix}-${'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  })}`;
}

function daysAgoIso(days: number) {
  const d = new Date();
  d.setDate(d.getDate() - days);
  d.setHours(Math.floor(Math.random() * 24), Math.floor(Math.random() * 60));
  return d.toISOString();
}

function generateRecord(index: number): HistoryRecord {
  const status = pick(STATUSES);
  const predictedClass = pick(CLASS_LABELS);
  const isFailed = status === 'failed';
  const participating = status === 'partial_success' ? 1 : status === 'failed' ? 0 : 2 + Math.round(Math.random());
  const successfulModels = MODEL_NAMES.slice(0, participating);
  const failedModels = MODEL_NAMES.slice(participating);

  const individualPredictions = isFailed
    ? []
    : successfulModels.map((m) => ({
        model_name: m,
        prediction: Math.random() > 0.15 ? predictedClass : pick(CLASS_LABELS),
        confidence: Math.round((55 + Math.random() * 42) * 10) / 10,
        inference_time_ms: Math.round(150 + Math.random() * 300),
      }));

  return {
    history_id: id('hist'),
    request_id: id('req'),
    status,
    image_filename: `slide_${1000 + index}.${pick(['png', 'jpg', 'tiff'])}`,
    predicted_class: isFailed ? '' : predictedClass,
    confidence: isFailed ? 0 : Math.round((55 + Math.random() * 42) * 10) / 10,
    agreement_ratio:
      status === 'success'
        ? Math.round((0.6 + Math.random() * 0.4) * 100) / 100
        : 0,
    successful_models: successfulModels,
    failed_models: failedModels,
    participating_models: participating,
    individual_predictions: individualPredictions,
    image_content_type: pick(['image/png', 'image/jpeg', 'image/tiff']),
    image_size_bytes: Math.round(400_000 + Math.random() * 6_000_000),
    image_width: pick([768, 1024, 1280, 2048]),
    image_height: pick([768, 1024, 1280, 2048]),
    model_manifest_version: '2.3.0',
    processing_time_ms: Math.round(180 + Math.random() * 900),
    created_at: daysAgoIso(Math.floor(Math.random() * 45)),
  };
}

let cachedDataset: HistoryRecord[] | null = null;

function getDataset(): HistoryRecord[] {
  if (!cachedDataset) {
    cachedDataset = Array.from({ length: 47 }, (_, i) => generateRecord(i)).sort(
      (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    );
  }
  return cachedDataset;
}

export function getAllHistoryRecordsForAnalytics() {
  return getDataset();
}

export async function simulateHistoryListRequest(
  filters: HistoryFilters
): Promise<PaginatedHistoryResponse> {
  await new Promise((res) => setTimeout(res, 500 + Math.random() * 400));

  let items = getDataset();

  if (filters.status !== 'all') {
    items = items.filter((r) => r.status === filters.status);
  }
  if (filters.predicted_class !== 'all') {
    items = items.filter((r) => r.predicted_class === filters.predicted_class);
  }
  if (filters.start_date) {
    const start = new Date(filters.start_date).getTime();
    items = items.filter((r) => new Date(r.created_at).getTime() >= start);
  }
  if (filters.end_date) {
    const end = new Date(filters.end_date).getTime();
    items = items.filter((r) => new Date(r.created_at).getTime() <= end);
  }
  if (filters.min_confidence !== null) {
    items = items.filter((r) => r.confidence >= filters.min_confidence!);
  }
  if (filters.max_confidence !== null) {
    items = items.filter((r) => r.confidence <= filters.max_confidence!);
  }

  const total_items = items.length;
  const total_pages = Math.max(1, Math.ceil(total_items / filters.page_size));
  const page = Math.min(filters.page, total_pages);
  const start = (page - 1) * filters.page_size;
  const pageItems = items.slice(start, start + filters.page_size);

  return {
    items: pageItems,
    page,
    page_size: filters.page_size,
    total_items,
    total_pages,
  };
}

export async function simulateHistoryDetailRequest(historyId: string): Promise<HistoryRecord | null> {
  await new Promise((res) => setTimeout(res, 350 + Math.random() * 300));
  return getDataset().find((r) => r.history_id === historyId) ?? null;
}

export function availableClassLabels(): string[] {
  return CLASS_LABELS;
}
