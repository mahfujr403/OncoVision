import { useState, useCallback } from 'react';
import { FileText, Download, BarChart2, AlertCircle, Microscope } from 'lucide-react';
import { motion } from 'framer-motion';
import { toast } from 'sonner';
import { SectionTitle } from '@/components/ui/SectionTitle';
import { Card, CardHeader, CardTitle, CardContent, StatCard } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorState } from '@/components/ui/ErrorState';
import { Skeleton } from '@/components/ui/Skeleton';
import { Badge } from '@/components/ui/Badge';
import { useReportsAnalytics } from '@/features/reports/hooks/useReportsQueries';
import { reportsService } from '@/features/reports/services/reportsService';
import type { AnalyticsData } from '@/features/reports/types';
import { cn } from '@/lib/utils';

// ── Generic analytics renderers ───────────────────────────────────────────────
// Field names from the backend are not confirmed (source not available in this
// environment). The renderers below handle whatever the API actually returns:
// scalar numbers/strings become MetricCards; objects/arrays become bar charts.

function isDistribution(val: unknown): val is Record<string, number> {
  return (
    typeof val === 'object' &&
    val !== null &&
    !Array.isArray(val) &&
    Object.values(val).every((v) => typeof v === 'number')
  );
}

function isNumericArray(val: unknown): val is Array<{ [key: string]: unknown }> {
  return Array.isArray(val) && val.length > 0 && typeof val[0] === 'object';
}

function formatValue(val: unknown): string {
  if (val === null || val === undefined) return '—';
  if (typeof val === 'number') {
    return Number.isInteger(val) ? String(val) : val.toFixed(2);
  }
  if (typeof val === 'string') return val;
  return '—';
}

function humanLabel(key: string): string {
  return key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

// CSS bar chart — no library required
function DistributionBar({
  label,
  items,
}: {
  label: string;
  items: Record<string, number>;
}) {
  const entries = Object.entries(items).sort(([, a], [, b]) => b - a);
  const max = Math.max(...entries.map(([, v]) => v), 1);

  return (
    <Card className="p-5" role="region" aria-label={label}>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-semibold">{humanLabel(label)}</CardTitle>
      </CardHeader>
      <CardContent>
        <div
          className="space-y-2.5"
          role="table"
          aria-label={`${humanLabel(label)} distribution`}
        >
          {/* sr-only header row */}
          <div className="sr-only" role="row">
            <span role="columnheader">Category</span>
            <span role="columnheader">Count</span>
            <span role="columnheader">Proportion</span>
          </div>
          {entries.map(([key, val]) => {
            const pct = Math.round((val / max) * 100);
            return (
              <div
                key={key}
                className="flex items-center gap-3"
                role="row"
                aria-label={`${humanLabel(key)}: ${val}`}
              >
                <span
                  className="w-28 shrink-0 text-[11px] text-muted-foreground truncate capitalize"
                  role="cell"
                  title={humanLabel(key)}
                >
                  {humanLabel(key)}
                </span>
                <div
                  className="flex-1 h-2 rounded-full bg-secondary overflow-hidden"
                  role="cell"
                  aria-hidden
                >
                  <motion.div
                    className="h-full rounded-full bg-primary/70"
                    initial={{ width: 0 }}
                    animate={{ width: `${pct}%` }}
                    transition={{ duration: 0.6, ease: 'easeOut' }}
                  />
                </div>
                <span
                  className="w-10 shrink-0 text-right font-mono text-xs"
                  role="cell"
                >
                  {val}
                </span>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

// Scalar stat grid
function ScalarGrid({ scalars }: { scalars: [string, unknown][] }) {
  if (scalars.length === 0) return null;
  return (
    <div
      className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
      role="list"
      aria-label="Summary metrics"
    >
      {scalars.map(([key, val]) => (
        <div key={key} role="listitem">
          <StatCard
            label={humanLabel(key)}
            value={formatValue(val)}
            icon={<BarChart2 className="h-4 w-4" />}
          />
        </div>
      ))}
    </div>
  );
}

// Determine if analytics returned any meaningful data at all
function isEmptyAnalytics(data: AnalyticsData): boolean {
  return Object.keys(data).length === 0;
}

function SkeletonGrid() {
  return (
    <div className="space-y-6" aria-busy="true" aria-label="Loading analytics">
      <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Card key={i}>
            <Skeleton className="h-3 w-24 mb-3" />
            <Skeleton className="h-7 w-16" />
          </Card>
        ))}
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        {[1, 2].map((i) => (
          <Card key={i} className="p-5 space-y-3">
            <Skeleton className="h-4 w-32" />
            {Array.from({ length: 4 }).map((_, j) => (
              <div key={j} className="flex items-center gap-3">
                <Skeleton className="h-2.5 w-24 shrink-0" />
                <Skeleton className="h-2 flex-1 rounded-full" />
                <Skeleton className="h-2.5 w-8 shrink-0" />
              </div>
            ))}
          </Card>
        ))}
      </div>
    </div>
  );
}

// ── Export button with loading + error state ──────────────────────────────────
function ExportButton({
  format,
  onExport,
}: {
  format: 'CSV' | 'PDF';
  onExport: () => Promise<void>;
}) {
  const [state, setState] = useState<'idle' | 'loading'>('idle');

  const handleClick = useCallback(async () => {
    setState('loading');
    try {
      await onExport();
      toast.success(`${format} downloaded successfully.`);
    } catch (err) {
      const msg = (err as { message?: string })?.message ?? `${format} export failed.`;
      toast.error(msg);
    } finally {
      setState('idle');
    }
  }, [format, onExport]);

  return (
    <Button
      variant="outline"
      size="sm"
      onClick={handleClick}
      disabled={state === 'loading'}
      aria-busy={state === 'loading'}
      aria-label={`Export ${format}`}
    >
      {state === 'loading' ? (
        <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent" />
      ) : (
        <Download className="h-3.5 w-3.5" />
      )}
      <Badge variant="secondary" className="text-[10px] uppercase ml-1">
        {format}
      </Badge>
    </Button>
  );
}

// ── Analytics renderer ────────────────────────────────────────────────────────
function AnalyticsDashboard({ data }: { data: AnalyticsData }) {
  const entries = Object.entries(data);

  const scalars = entries.filter(
    ([, v]) =>
      typeof v === 'number' || typeof v === 'string',
  );

  const distributions = entries.filter(([, v]) => isDistribution(v)) as [
    string,
    Record<string, number>,
  ][];

  const arrays = entries.filter(([, v]) => isNumericArray(v));

  const isEmpty = isEmptyAnalytics(data);

  if (isEmpty) {
    return (
      <Card>
        <EmptyState
          icon={<Microscope className="h-6 w-6" />}
          title="No analytics yet"
          description="Run your first prediction to see aggregate analytics here."
        />
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Scalar metrics */}
      <ScalarGrid scalars={scalars} />

      {/* Distribution bar charts */}
      {distributions.length > 0 && (
        <div className="grid gap-4 lg:grid-cols-2">
          {distributions.map(([key, val]) => (
            <DistributionBar key={key} label={key} items={val} />
          ))}
        </div>
      )}

      {/* Array-based charts (e.g. time-series) — rendered as tables */}
      {arrays.length > 0 &&
        arrays.map(([key, val]) => {
          const rows = val as Record<string, unknown>[];
          const cols = rows.length > 0 ? Object.keys(rows[0]) : [];
          return (
            <Card key={key} className="overflow-hidden">
              <CardHeader className="px-5 pt-5 pb-2">
                <CardTitle className="text-sm font-semibold">{humanLabel(key)}</CardTitle>
              </CardHeader>
              <CardContent className="overflow-x-auto pb-5 px-5">
                <table className="w-full text-xs" aria-label={humanLabel(key)}>
                  <thead>
                    <tr className="border-b border-border">
                      {cols.map((col) => (
                        <th
                          key={col}
                          className="pb-2 pr-4 text-left font-medium text-muted-foreground uppercase tracking-wider whitespace-nowrap"
                        >
                          {humanLabel(col)}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((row, i) => (
                      <tr key={i} className="border-b border-border/50 last:border-0">
                        {cols.map((col) => (
                          <td key={col} className="py-2 pr-4 font-mono">
                            {formatValue(row[col])}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </CardContent>
            </Card>
          );
        })}

      {/* Disclaimer */}
      <p className="text-[11px] text-muted-foreground/50 leading-relaxed flex items-center gap-1.5">
        <AlertCircle className="h-3 w-3 shrink-0" />
        Analytics reflect AI-assisted predictions only. Figures do not constitute clinical validation
        or diagnostic performance guarantees.
      </p>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────
export default function ReportsPage() {
  const { data, isLoading, isError, error, refetch } = useReportsAnalytics();

  const errorMsg = (error as { message?: string })?.message ?? 'Failed to load analytics.';

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-6"
    >
      <SectionTitle
        title="Reports & Analytics"
        description="Aggregate AI prediction analytics for your account"
        action={
          <div className="flex items-center gap-2">
            <ExportButton format="CSV" onExport={reportsService.exportCsv} />
            <ExportButton format="PDF" onExport={reportsService.exportPdf} />
          </div>
        }
      />

      {/* Main content */}
      {isLoading ? (
        <SkeletonGrid />
      ) : isError ? (
        <ErrorState
          title="Failed to load analytics"
          message={errorMsg}
          onRetry={() => void refetch()}
        />
      ) : data ? (
        <AnalyticsDashboard data={data} />
      ) : null}

      {/* Export note */}
      {!isLoading && !isError && (
        <div
          className={cn(
            'flex items-start gap-2.5 rounded-lg border border-border/50 bg-muted/30 px-4 py-3',
          )}
        >
          <FileText className="h-4 w-4 text-muted-foreground shrink-0 mt-0.5" />
          <p className="text-xs text-muted-foreground leading-relaxed">
            CSV and PDF exports include all predictions within your account's history. Export
            processing is handled server-side — large datasets may take a moment to generate.
          </p>
        </div>
      )}
    </motion.div>
  );
}
