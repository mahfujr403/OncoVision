import { useState, useMemo } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import {
  GitCompare,
  Cpu,
  Layers,
  Activity,
  Clock,
  Info,
  Microscope,
  SlidersHorizontal,
  FileText,
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/Table';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorState } from '@/components/ui/ErrorState';
import { Skeleton } from '@/components/ui/Skeleton';
import { DemoDataBanner } from '@/components/ui/DemoDataBanner';
import { usePredictionHistory, usePredictionHistoryDetail } from '@/hooks/queries/usePredictionHistory';
import { useSystemModels } from '@/hooks/queries/useSystemModels';
import { formatPercent, formatInferenceTime, formatDateTime } from '@/utils/formatters';
import { ROUTES } from '@/constants/routes';
import { cn } from '@/lib/utils';

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

function normalizeDiseaseLabel(label: string | null | undefined): string {
  if (!label) return 'Unclassified';
  const map: Record<string, string> = {
    lung_aca: 'Lung Adenocarcinoma',
    lung_scc: 'Lung Squamous Cell Carcinoma',
    lung_benign: 'Lung Benign Tissue',
    colon_aca: 'Colon Adenocarcinoma',
    colon_benign: 'Colon Benign Tissue',
  };
  return map[label] || label;
}

export default function ComparisonPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedCaseId = searchParams.get('caseId');
  const [activeTab, setActiveTab] = useState<'architecture' | 'cross-case'>('architecture');

  // History query to get real evaluated cases
  const {
    data: historyData,
    isLoading: isHistoryLoading,
    isError: isHistoryError,
    refetch: refetchHistory,
  } = usePredictionHistory({ page: 1, page_size: 20 });

  // System models manifest query to get registered architectures
  const { data: systemModelsData } = useSystemModels();

  const cases = historyData?.items ?? [];

  // Determine active case for single-case architecture comparison
  const selectedCaseId = useMemo(() => {
    if (requestedCaseId && cases.some((c) => c.history_id === requestedCaseId)) {
      return requestedCaseId;
    }
    return cases[0]?.history_id;
  }, [requestedCaseId, cases]);

  // Fetch full detail for the selected case
  const {
    data: caseDetail,
    isLoading: isDetailLoading,
    isError: isDetailError,
    refetch: refetchDetail,
  } = usePredictionHistoryDetail(selectedCaseId);

  // Cross-case slot states
  const [slotAId, setSlotAId] = useState<string>('');
  const [slotBId, setSlotBId] = useState<string>('');

  const effectiveSlotAId = slotAId || cases[0]?.history_id || '';
  const effectiveSlotBId = slotBId || (cases.length > 1 ? cases[1]?.history_id : '');

  const { data: slotADetail } = usePredictionHistoryDetail(effectiveSlotAId || undefined);
  const { data: slotBDetail } = usePredictionHistoryDetail(effectiveSlotBId || undefined);

  // Model filter state for architecture breakdown
  const [architectureFilter, setArchitectureFilter] = useState<string>('all');

  const individualPredictions = caseDetail?.individual_predictions ?? [];
  const filteredPredictions = useMemo(() => {
    if (architectureFilter === 'all') return individualPredictions;
    return individualPredictions.filter((p) => p.model_name.toLowerCase() === architectureFilter.toLowerCase());
  }, [individualPredictions, architectureFilter]);

  const uniqueArchitectures = useMemo(() => {
    const set = new Set<string>();
    individualPredictions.forEach((p) => set.add(p.model_name));
    return Array.from(set);
  }, [individualPredictions]);

  // Handle case selection
  const handleSelectCase = (historyId: string) => {
    setSearchParams({ caseId: historyId });
  };

  return (
    <div className="space-y-6">
      {/* Calm Scientific Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-semibold tracking-tight text-text-primary sm:text-2xl">
              Model & Architecture Comparison
            </h1>
            {systemModelsData && (
              <Badge variant="outline" className="hidden sm:inline-flex text-[10px] font-mono">
                Manifest v{systemModelsData.manifest_version}
              </Badge>
            )}
          </div>
          <p className="mt-1 text-sm text-text-muted">
            Compare available inference architectures and their observed prediction behavior across clinical evaluations.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button variant="outline" size="sm" asChild>
            <Link to={ROUTES.HISTORY} className="gap-1.5">
              <FileText className="h-3.5 w-3.5" />
              <span>Browse History</span>
            </Link>
          </Button>
          <Button size="sm" asChild>
            <Link to={ROUTES.PREDICT} className="gap-1.5">
              <Microscope className="h-3.5 w-3.5" />
              <span>New Analysis</span>
            </Link>
          </Button>
        </div>
      </div>

      {/* Investigational Research Disclaimer Banner */}
      <div
        role="region"
        aria-label="Investigational Disclaimer"
        className="flex items-start gap-3 rounded-lg border border-border-subtle bg-surface-raised/60 p-3.5 text-xs text-text-secondary"
      >
        <Info className="mt-0.5 h-4 w-4 shrink-0 text-text-muted" aria-hidden="true" />
        <div className="space-y-0.5 leading-relaxed">
          <span className="font-semibold text-text-primary">Investigational Evaluation Context: </span>
          Model comparisons report observed architecture predictions, posterior confidence scores, and cross-model agreement distributions.
          Comparative metrics do not establish clinical superiority or standalone diagnostic effectiveness.
        </div>
      </div>

      {/* Workspace Tabs: Single-Case Architecture Breakdown vs Cross-Case Evaluation */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border-b border-border pb-3">
        <div className="flex items-center gap-1 rounded-lg border border-border bg-surface p-1 text-xs">
          <button
            type="button"
            onClick={() => setActiveTab('architecture')}
            className={cn(
              'flex items-center gap-1.5 rounded-md px-3 py-1.5 font-medium transition-colors focus-visible:outline-hidden focus-visible:ring-1 focus-visible:ring-primary',
              activeTab === 'architecture'
                ? 'bg-surface-raised font-semibold text-text-primary shadow-xs'
                : 'text-text-muted hover:text-text-primary',
            )}
          >
            <Cpu className="h-3.5 w-3.5" />
            <span>Architecture Breakdown</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('cross-case')}
            className={cn(
              'flex items-center gap-1.5 rounded-md px-3 py-1.5 font-medium transition-colors focus-visible:outline-hidden focus-visible:ring-1 focus-visible:ring-primary',
              activeTab === 'cross-case'
                ? 'bg-surface-raised font-semibold text-text-primary shadow-xs'
                : 'text-text-muted hover:text-text-primary',
            )}
          >
            <GitCompare className="h-3.5 w-3.5" />
            <span>Cross-Case Comparison</span>
          </button>
        </div>

        {/* Case selector for architecture mode */}
        {activeTab === 'architecture' && cases.length > 0 && (
          <div className="flex items-center gap-2 text-xs">
            <span className="text-text-muted font-medium shrink-0">Evaluated Specimen:</span>
            <select
              id="case-selector"
              aria-label="Select evaluated specimen"
              value={selectedCaseId || ''}
              onChange={(e) => handleSelectCase(e.target.value)}
              className="rounded-md border border-border bg-surface px-2.5 py-1.5 text-xs text-text-primary focus-visible:outline-hidden focus-visible:ring-1 focus-visible:ring-primary"
            >
              {cases.map((c) => (
                <option key={c.history_id} value={c.history_id}>
                  {c.image_filename} — {normalizeDiseaseLabel(c.predicted_class)} ({formatPercent(c.confidence)})
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* History Loading / Error States */}
      {isHistoryLoading ? (
        <div className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Card key={i} className="p-4 space-y-2">
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-6 w-16" />
                <Skeleton className="h-3 w-32" />
              </Card>
            ))}
          </div>
          <Card className="p-6">
            <Skeleton className="h-56 w-full" />
          </Card>
        </div>
      ) : isHistoryError ? (
        <ErrorState
          title="Unable to load comparison data"
          message="Could not retrieve evaluated cases from prediction history."
          onRetry={() => refetchHistory()}
        />
      ) : cases.length === 0 ? (
        <Card className="py-12">
          <EmptyState
            icon={<GitCompare className="h-8 w-8 text-text-muted" />}
            title="No evaluated cases available"
            description="Run a histopathology prediction analysis first. Architecture comparison requires evaluated case records with individual model outputs."
            action={{
              label: 'Run Analysis in Prediction Workspace',
              onClick: () => {},
            }}
          />
        </Card>
      ) : activeTab === 'architecture' ? (
        /* ==================== TAB 1: ARCHITECTURE BREAKDOWN ==================== */
        <div className="space-y-6">
          {/* Detail Loading / Error State */}
          {isDetailLoading ? (
            <Card className="p-6 space-y-4">
              <Skeleton className="h-6 w-48" />
              <div className="grid gap-3 sm:grid-cols-3">
                <Skeleton className="h-24 w-full" />
                <Skeleton className="h-24 w-full" />
                <Skeleton className="h-24 w-full" />
              </div>
            </Card>
          ) : isDetailError || !caseDetail ? (
            <ErrorState
              title="Unable to load specimen evaluation"
              message="Could not load individual architecture metrics for the selected case."
              onRetry={() => refetchDetail()}
            />
          ) : (
            <>
              {/* Specimen Context Banner */}
              <div className="flex flex-col gap-2 rounded-lg border border-border bg-surface p-4 text-xs sm:flex-row sm:items-center sm:justify-between">
                <div className="flex flex-wrap items-center gap-3">
                  <div className="flex items-center gap-1.5 font-medium text-text-primary">
                    <Microscope className="h-4 w-4 text-primary" />
                    <span>Specimen:</span>
                    <span className="font-mono text-text-secondary">{caseDetail.image_metadata.filename}</span>
                  </div>
                  <span className="text-border">|</span>
                  <div className="flex items-center gap-1.5 text-text-muted">
                    <Clock className="h-3.5 w-3.5" />
                    <span>Analyzed {formatDateTime(caseDetail.created_at)}</span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-text-muted">Ensemble Finding:</span>
                  <Badge variant={getDiseaseBadgeVariant(caseDetail.predicted_class)} dot>
                    {normalizeDiseaseLabel(caseDetail.predicted_class)}
                  </Badge>
                </div>
              </div>

              {/* Analytical Summary Metric Cards */}
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <Card className="p-4 space-y-1">
                  <div className="flex items-center justify-between text-text-muted">
                    <span className="text-xs font-medium">Ensemble Consensus</span>
                    <Layers className="h-4 w-4 text-primary" />
                  </div>
                  <div className="text-lg font-semibold font-mono tabular-nums text-text-primary">
                    {formatPercent(caseDetail.agreement_ratio)}
                  </div>
                  <p className="text-[11px] text-text-muted">
                    Cross-architecture agreement ratio ({caseDetail.successful_models.length} of {caseDetail.participating_models} models)
                  </p>
                </Card>

                <Card className="p-4 space-y-1">
                  <div className="flex items-center justify-between text-text-muted">
                    <span className="text-xs font-medium">Ensemble Confidence</span>
                    <Activity className="h-4 w-4 text-primary" />
                  </div>
                  <div className="text-lg font-semibold font-mono tabular-nums text-text-primary">
                    {formatPercent(caseDetail.confidence)}
                  </div>
                  <p className="text-[11px] text-text-muted">
                    Posterior probability for consensus classification
                  </p>
                </Card>

                <Card className="p-4 space-y-1">
                  <div className="flex items-center justify-between text-text-muted">
                    <span className="text-xs font-medium">Participating Models</span>
                    <Cpu className="h-4 w-4 text-primary" />
                  </div>
                  <div className="text-lg font-semibold font-mono tabular-nums text-text-primary">
                    {caseDetail.participating_models}
                  </div>
                  <p className="text-[11px] text-text-muted">
                    Active architectures in runtime pipeline
                  </p>
                </Card>

                <Card className="p-4 space-y-1">
                  <div className="flex items-center justify-between text-text-muted">
                    <span className="text-xs font-medium">Total Pipeline Latency</span>
                    <Clock className="h-4 w-4 text-primary" />
                  </div>
                  <div className="text-lg font-semibold font-mono tabular-nums text-text-primary">
                    {caseDetail.runtime_info.processing_time_ms
                      ? formatInferenceTime(caseDetail.runtime_info.processing_time_ms)
                      : 'N/A'}
                  </div>
                  <p className="text-[11px] text-text-muted">
                    End-to-end inference and fusion execution
                  </p>
                </Card>
              </div>

              {/* Architecture Filter Chips if multiple models */}
              {uniqueArchitectures.length > 1 && (
                <div className="flex items-center gap-2 text-xs">
                  <SlidersHorizontal className="h-3.5 w-3.5 text-text-muted" />
                  <span className="text-text-muted font-medium">Filter Architecture:</span>
                  <div className="flex flex-wrap gap-1">
                    <button
                      type="button"
                      onClick={() => setArchitectureFilter('all')}
                      className={cn(
                        'rounded-md px-2.5 py-1 text-xs font-medium transition-colors',
                        architectureFilter === 'all'
                          ? 'bg-primary-surface text-primary border border-primary/20'
                          : 'bg-surface text-text-secondary border border-border hover:bg-surface-raised',
                      )}
                    >
                      All ({individualPredictions.length})
                    </button>
                    {uniqueArchitectures.map((arch) => (
                      <button
                        key={arch}
                        type="button"
                        onClick={() => setArchitectureFilter(arch)}
                        className={cn(
                          'rounded-md px-2.5 py-1 text-xs font-medium transition-colors font-mono',
                          architectureFilter === arch
                            ? 'bg-primary-surface text-primary border border-primary/20'
                            : 'bg-surface text-text-secondary border border-border hover:bg-surface-raised',
                        )}
                      >
                        {arch}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Analytical Model Cards Grid */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h2 className="text-sm font-semibold text-text-primary">Individual Architecture Evidence</h2>
                  <span className="text-xs text-text-muted">
                    {filteredPredictions.length} {filteredPredictions.length === 1 ? 'model' : 'models'} observed
                  </span>
                </div>

                {filteredPredictions.length === 0 ? (
                  <Card className="p-8 text-center text-xs text-text-muted">
                    No individual model predictions were recorded for this case. Individual predictions require the pipeline to run with model telemetry enabled.
                  </Card>
                ) : (
                  <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                    {filteredPredictions.map((entry) => {
                      const agreed =
                        caseDetail.predicted_class &&
                        entry.prediction.toLowerCase() === caseDetail.predicted_class.toLowerCase();

                      return (
                        <Card key={entry.model_name} className="flex flex-col justify-between p-4 space-y-4">
                          {/* Card Header: Architecture & Operational Status */}
                          <div className="flex items-start justify-between gap-2">
                            <div className="flex items-center gap-2">
                              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-surface-raised text-primary">
                                <Cpu className="h-4 w-4" />
                              </div>
                              <div>
                                <h3 className="text-sm font-semibold text-text-primary font-mono">
                                  {entry.model_name}
                                </h3>
                                <p className="text-[11px] text-text-muted">Deep Inference Model</p>
                              </div>
                            </div>
                            <Badge variant="success" dot className="text-[10px]">
                              Completed
                            </Badge>
                          </div>

                          {/* Observed Finding */}
                          <div className="space-y-1 rounded-md border border-border-subtle bg-surface-raised/40 p-2.5">
                            <div className="text-[11px] text-text-muted">Observed Classification</div>
                            <div className="flex items-center gap-1.5">
                              <Badge variant={getDiseaseBadgeVariant(entry.prediction)} dot>
                                {normalizeDiseaseLabel(entry.prediction)}
                              </Badge>
                            </div>
                          </div>

                          {/* Numerical Metrics */}
                          <div className="grid grid-cols-2 gap-2 text-xs">
                            <div className="space-y-0.5">
                              <span className="text-[11px] text-text-muted">Confidence</span>
                              <div className="font-mono font-semibold tabular-nums text-text-primary">
                                {formatPercent(entry.confidence)}
                              </div>
                            </div>
                            <div className="space-y-0.5">
                              <span className="text-[11px] text-text-muted">Inference Latency</span>
                              <div className="font-mono font-semibold tabular-nums text-text-primary">
                                {formatInferenceTime(entry.inference_time_ms)}
                              </div>
                            </div>
                          </div>

                          {/* Consensus Contribution */}
                          <div className="border-t border-border-subtle pt-2.5 text-[11px] text-text-secondary flex items-center justify-between">
                            <span>Consensus Contribution:</span>
                            <span className={cn('font-medium', agreed ? 'text-success' : 'text-warning')}>
                              {agreed ? 'Concurred with ensemble' : 'Divergent prediction'}
                            </span>
                          </div>
                        </Card>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Model Comparison Table */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-sm font-semibold text-text-primary">Comparative Architecture Table</h2>
                    <p className="text-xs text-text-muted">
                      Direct side-by-side technical evaluation across participating models for this specimen
                    </p>
                  </div>
                </div>

                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead scope="col">Architecture</TableHead>
                      <TableHead scope="col">Observed Finding</TableHead>
                      <TableHead scope="col" className="text-right">Confidence</TableHead>
                      <TableHead scope="col" className="text-right">Latency</TableHead>
                      <TableHead scope="col">Consensus Contribution</TableHead>
                      <TableHead scope="col" className="text-center">Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredPredictions.map((entry) => {
                      const agreed =
                        caseDetail.predicted_class &&
                        entry.prediction.toLowerCase() === caseDetail.predicted_class.toLowerCase();

                      return (
                        <TableRow key={entry.model_name}>
                          <TableCell className="font-mono font-medium text-text-primary">
                            <div className="flex items-center gap-2">
                              <Cpu className="h-3.5 w-3.5 text-text-muted shrink-0" />
                              <span>{entry.model_name}</span>
                            </div>
                          </TableCell>
                          <TableCell>
                            <Badge variant={getDiseaseBadgeVariant(entry.prediction)} dot>
                              {normalizeDiseaseLabel(entry.prediction)}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-right font-mono font-medium tabular-nums text-text-primary">
                            {formatPercent(entry.confidence)}
                          </TableCell>
                          <TableCell className="text-right font-mono tabular-nums text-text-muted">
                            {formatInferenceTime(entry.inference_time_ms)}
                          </TableCell>
                          <TableCell>
                            <span className={cn('text-xs font-medium', agreed ? 'text-success' : 'text-warning')}>
                              {agreed ? 'Concurred' : 'Divergent'}
                            </span>
                          </TableCell>
                          <TableCell className="text-center">
                            <Badge variant="success" className="text-[10px]">
                              Available
                            </Badge>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>

              {/* Confidence Distribution & Comparison Visualization */}
              {filteredPredictions.length > 0 && (
                <Card className="p-5 space-y-4">
                  <CardHeader className="p-0">
                    <CardTitle className="text-sm font-semibold">Observed Confidence Distribution</CardTitle>
                    <CardDescription className="text-xs">
                      Horizontal comparison of observed posterior probability by model architecture
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="p-0 space-y-3">
                    {filteredPredictions.map((entry) => (
                      <div key={entry.model_name} className="space-y-1">
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-mono font-medium text-text-primary">{entry.model_name}</span>
                          <span className="font-mono tabular-nums text-text-muted">
                            {formatPercent(entry.confidence)}
                          </span>
                        </div>
                        <div
                          className="h-2 w-full rounded-full bg-surface-raised overflow-hidden"
                          role="progressbar"
                          aria-label={`Confidence for ${entry.model_name}`}
                          aria-valuenow={Math.round(entry.confidence * 100)}
                          aria-valuemin={0}
                          aria-valuemax={100}
                        >
                          <div
                            className="h-full rounded-full bg-primary transition-all duration-300"
                            style={{ width: `${Math.min(100, Math.max(0, entry.confidence * 100))}%` }}
                          />
                        </div>
                      </div>
                    ))}

                    <div className="mt-4 rounded-md border border-border-subtle bg-surface-raised/40 p-3 text-xs text-text-muted">
                      <span className="font-medium text-text-primary">Comparative Observation: </span>
                      {caseDetail.agreement_ratio === 1
                        ? 'All evaluated architectures concurred on the classified finding with consistent probability margins.'
                        : 'Partial divergence observed across architectures. Check individual classification labels for differential weighting.'}
                    </div>
                  </CardContent>
                </Card>
              )}
            </>
          )}
        </div>
      ) : (
        /* ==================== TAB 2: CROSS-CASE COMPARISON ==================== */
        <div className="space-y-6">
          <DemoDataBanner feature="batch multi-case comparison" />

          {/* Slot Selection Controls */}
          <div className="grid gap-4 md:grid-cols-2">
            {/* Slot A Selector Card */}
            <Card className="p-4 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wider text-text-muted">Slot A Specimen</span>
                <Badge variant="secondary" className="text-[10px]">Reference 1</Badge>
              </div>
              <select
                aria-label="Select Slot A Specimen"
                value={effectiveSlotAId}
                onChange={(e) => setSlotAId(e.target.value)}
                className="w-full rounded-md border border-border bg-surface px-3 py-2 text-xs text-text-primary focus-visible:outline-hidden focus-visible:ring-1 focus-visible:ring-primary"
              >
                {cases.map((c) => (
                  <option key={c.history_id} value={c.history_id}>
                    {c.image_filename} — {normalizeDiseaseLabel(c.predicted_class)} ({formatPercent(c.confidence)})
                  </option>
                ))}
              </select>
            </Card>

            {/* Slot B Selector Card */}
            <Card className="p-4 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wider text-text-muted">Slot B Specimen</span>
                <Badge variant="secondary" className="text-[10px]">Reference 2</Badge>
              </div>
              <select
                aria-label="Select Slot B Specimen"
                value={effectiveSlotBId}
                onChange={(e) => setSlotBId(e.target.value)}
                className="w-full rounded-md border border-border bg-surface px-3 py-2 text-xs text-text-primary focus-visible:outline-hidden focus-visible:ring-1 focus-visible:ring-primary"
              >
                {cases.map((c) => (
                  <option key={c.history_id} value={c.history_id}>
                    {c.image_filename} — {normalizeDiseaseLabel(c.predicted_class)} ({formatPercent(c.confidence)})
                  </option>
                ))}
              </select>
            </Card>
          </div>

          {/* Side-by-Side Comparison Grid */}
          <div className="grid gap-4 md:grid-cols-2 min-h-[360px]">
            {/* Case A Card */}
            <Card className="flex flex-col justify-between p-5 space-y-4">
              <div className="space-y-3">
                <div className="flex items-start justify-between">
                  <div>
                    <span className="text-[10px] font-semibold uppercase tracking-wider text-text-muted">Case A</span>
                    <h3 className="text-sm font-semibold text-text-primary font-mono truncate max-w-[240px]">
                      {slotADetail?.image_metadata.filename || 'Loading...'}
                    </h3>
                  </div>
                  {slotADetail && (
                    <Badge variant={getDiseaseBadgeVariant(slotADetail.predicted_class)} dot>
                      {normalizeDiseaseLabel(slotADetail.predicted_class)}
                    </Badge>
                  )}
                </div>

                {slotADetail ? (
                  <div className="space-y-2 text-xs">
                    <div className="flex justify-between border-b border-border-subtle py-1.5">
                      <span className="text-text-muted">Confidence</span>
                      <span className="font-mono font-medium tabular-nums text-text-primary">
                        {formatPercent(slotADetail.confidence)}
                      </span>
                    </div>
                    <div className="flex justify-between border-b border-border-subtle py-1.5">
                      <span className="text-text-muted">Agreement Ratio</span>
                      <span className="font-mono font-medium tabular-nums text-text-primary">
                        {formatPercent(slotADetail.agreement_ratio)}
                      </span>
                    </div>
                    <div className="flex justify-between border-b border-border-subtle py-1.5">
                      <span className="text-text-muted">Evaluated At</span>
                      <span className="text-text-secondary">{formatDateTime(slotADetail.created_at)}</span>
                    </div>
                    <div className="flex justify-between border-b border-border-subtle py-1.5">
                      <span className="text-text-muted">Participating Architectures</span>
                      <span className="font-mono tabular-nums text-text-primary">{slotADetail.participating_models}</span>
                    </div>
                    <div className="flex justify-between py-1.5">
                      <span className="text-text-muted">Pipeline Latency</span>
                      <span className="font-mono tabular-nums text-text-primary">
                        {slotADetail.runtime_info.processing_time_ms
                          ? formatInferenceTime(slotADetail.runtime_info.processing_time_ms)
                          : 'N/A'}
                      </span>
                    </div>
                  </div>
                ) : (
                  <Skeleton className="h-32 w-full" />
                )}
              </div>

              {slotADetail && (
                <Button variant="outline" size="sm" asChild className="w-full">
                  <Link to={`${ROUTES.HISTORY}/${slotADetail.history_id}`}>View Case Detail</Link>
                </Button>
              )}
            </Card>

            {/* Case B Card */}
            <Card className="flex flex-col justify-between p-5 space-y-4">
              <div className="space-y-3">
                <div className="flex items-start justify-between">
                  <div>
                    <span className="text-[10px] font-semibold uppercase tracking-wider text-text-muted">Case B</span>
                    <h3 className="text-sm font-semibold text-text-primary font-mono truncate max-w-[240px]">
                      {slotBDetail?.image_metadata.filename || 'Loading...'}
                    </h3>
                  </div>
                  {slotBDetail && (
                    <Badge variant={getDiseaseBadgeVariant(slotBDetail.predicted_class)} dot>
                      {normalizeDiseaseLabel(slotBDetail.predicted_class)}
                    </Badge>
                  )}
                </div>

                {slotBDetail ? (
                  <div className="space-y-2 text-xs">
                    <div className="flex justify-between border-b border-border-subtle py-1.5">
                      <span className="text-text-muted">Confidence</span>
                      <span className="font-mono font-medium tabular-nums text-text-primary">
                        {formatPercent(slotBDetail.confidence)}
                      </span>
                    </div>
                    <div className="flex justify-between border-b border-border-subtle py-1.5">
                      <span className="text-text-muted">Agreement Ratio</span>
                      <span className="font-mono font-medium tabular-nums text-text-primary">
                        {formatPercent(slotBDetail.agreement_ratio)}
                      </span>
                    </div>
                    <div className="flex justify-between border-b border-border-subtle py-1.5">
                      <span className="text-text-muted">Evaluated At</span>
                      <span className="text-text-secondary">{formatDateTime(slotBDetail.created_at)}</span>
                    </div>
                    <div className="flex justify-between border-b border-border-subtle py-1.5">
                      <span className="text-text-muted">Participating Architectures</span>
                      <span className="font-mono tabular-nums text-text-primary">{slotBDetail.participating_models}</span>
                    </div>
                    <div className="flex justify-between py-1.5">
                      <span className="text-text-muted">Pipeline Latency</span>
                      <span className="font-mono tabular-nums text-text-primary">
                        {slotBDetail.runtime_info.processing_time_ms
                          ? formatInferenceTime(slotBDetail.runtime_info.processing_time_ms)
                          : 'N/A'}
                      </span>
                    </div>
                  </div>
                ) : (
                  <Skeleton className="h-32 w-full" />
                )}
              </div>

              {slotBDetail && (
                <Button variant="outline" size="sm" asChild className="w-full">
                  <Link to={`${ROUTES.HISTORY}/${slotBDetail.history_id}`}>View Case Detail</Link>
                </Button>
              )}
            </Card>
          </div>

          {/* Comparative Matrix Table */}
          <Card className="space-y-3 p-5">
            <CardHeader className="p-0">
              <CardTitle className="text-sm font-semibold">Comparative Evidence Matrix</CardTitle>
              <CardDescription className="text-xs">
                Side-by-side parameter evaluation across the selected specimens
              </CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead scope="col">Evaluation Parameter</TableHead>
                    <TableHead scope="col">Slot A Value</TableHead>
                    <TableHead scope="col">Slot B Value</TableHead>
                    <TableHead scope="col">Comparative Finding</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  <TableRow>
                    <TableCell className="font-medium text-text-primary">Classified Finding</TableCell>
                    <TableCell>
                      {slotADetail ? (
                        <Badge variant={getDiseaseBadgeVariant(slotADetail.predicted_class)} dot>
                          {normalizeDiseaseLabel(slotADetail.predicted_class)}
                        </Badge>
                      ) : (
                        '—'
                      )}
                    </TableCell>
                    <TableCell>
                      {slotBDetail ? (
                        <Badge variant={getDiseaseBadgeVariant(slotBDetail.predicted_class)} dot>
                          {normalizeDiseaseLabel(slotBDetail.predicted_class)}
                        </Badge>
                      ) : (
                        '—'
                      )}
                    </TableCell>
                    <TableCell className="text-xs">
                      {slotADetail && slotBDetail ? (
                        slotADetail.predicted_class === slotBDetail.predicted_class ? (
                          <span className="text-text-secondary">Identical classification category</span>
                        ) : (
                          <span className="text-warning font-medium">Distinct classification category</span>
                        )
                      ) : (
                        '—'
                      )}
                    </TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell className="font-medium text-text-primary">Confidence Score</TableCell>
                    <TableCell className="font-mono tabular-nums">
                      {slotADetail ? formatPercent(slotADetail.confidence) : '—'}
                    </TableCell>
                    <TableCell className="font-mono tabular-nums">
                      {slotBDetail ? formatPercent(slotBDetail.confidence) : '—'}
                    </TableCell>
                    <TableCell className="text-xs text-text-muted">
                      {slotADetail && slotBDetail
                        ? `Δ ${(Math.abs(slotADetail.confidence - slotBDetail.confidence) * 100).toFixed(1)}%`
                        : '—'}
                    </TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell className="font-medium text-text-primary">Consensus Agreement</TableCell>
                    <TableCell className="font-mono tabular-nums">
                      {slotADetail ? formatPercent(slotADetail.agreement_ratio) : '—'}
                    </TableCell>
                    <TableCell className="font-mono tabular-nums">
                      {slotBDetail ? formatPercent(slotBDetail.agreement_ratio) : '—'}
                    </TableCell>
                    <TableCell className="text-xs text-text-muted">
                      {slotADetail && slotBDetail
                        ? slotADetail.agreement_ratio === slotBDetail.agreement_ratio
                          ? 'Equivalent consensus ratio'
                          : 'Variable consensus level'
                        : '—'}
                    </TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell className="font-medium text-text-primary">Inference Latency</TableCell>
                    <TableCell className="font-mono tabular-nums">
                      {slotADetail?.runtime_info.processing_time_ms
                        ? formatInferenceTime(slotADetail.runtime_info.processing_time_ms)
                        : '—'}
                    </TableCell>
                    <TableCell className="font-mono tabular-nums">
                      {slotBDetail?.runtime_info.processing_time_ms
                        ? formatInferenceTime(slotBDetail.runtime_info.processing_time_ms)
                        : '—'}
                    </TableCell>
                    <TableCell className="text-xs text-text-muted">
                      {slotADetail?.runtime_info.processing_time_ms && slotBDetail?.runtime_info.processing_time_ms
                        ? `${Math.abs(slotADetail.runtime_info.processing_time_ms - slotBDetail.runtime_info.processing_time_ms)}ms difference`
                        : '—'}
                    </TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
