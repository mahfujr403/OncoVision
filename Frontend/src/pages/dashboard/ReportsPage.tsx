import { useState } from 'react';
import { toast } from 'sonner';
import { BarChart3, Download, FileDown, FileSpreadsheet } from 'lucide-react';
import { SectionTitle } from '@/components/ui/SectionTitle';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { ErrorState } from '@/components/ui/ErrorState';
import { Skeleton } from '@/components/ui/Skeleton';
import { useAnalytics } from '@/hooks/queries/useAnalytics';
import { exportPredictionHistoryCsv, exportPredictionReportPdf } from '@/api/services/reportsService';
import { getClassLabelColor } from '@/constants/app';
import { formatDateTime } from '@/utils/formatters';
import type { ApiError } from '@/types';

// NOTE: the previous version of this page showed a list of "generated
// reports" (titles, formats, download buttons) — none of that existed on
// the backend. The backend only exposes a single live analytics snapshot
// (GET /reports/analytics) plus two on-demand export endpoints. This page
// now reflects exactly that.
export default function ReportsPage() {
  const { data, isLoading, isError, refetch } = useAnalytics();
  const [exporting, setExporting] = useState<'csv' | 'pdf' | null>(null);

  const handleExport = async (format: 'csv' | 'pdf') => {
    setExporting(format);
    try {
      if (format === 'csv') await exportPredictionHistoryCsv();
      else await exportPredictionReportPdf();
      toast.success(`${format.toUpperCase()} export downloaded.`);
    } catch (err) {
      const apiErr = err as ApiError;
      toast.error(apiErr.message ?? `Failed to export ${format.toUpperCase()}.`);
    } finally {
      setExporting(null);
    }
  };

  return (
    <div className="space-y-5">
      <SectionTitle
        title="Reports & Analytics"
        description="Live analytics computed from your prediction history"
        action={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleExport('csv')}
              loading={exporting === 'csv'}
              disabled={exporting !== null}
            >
              <FileSpreadsheet className="h-3.5 w-3.5" />
              Export CSV
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleExport('pdf')}
              loading={exporting === 'pdf'}
              disabled={exporting !== null}
            >
              <FileDown className="h-3.5 w-3.5" />
              Export PDF
            </Button>
          </div>
        }
      />

      {isError ? (
        <ErrorState message="Couldn't load analytics." onRetry={() => refetch()} />
      ) : isLoading || !data ? (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Card key={i} className="space-y-2">
              <Skeleton className="h-3 w-20" />
              <Skeleton className="h-6 w-14" />
            </Card>
          ))}
        </div>
      ) : (
        <>
          {/* Summary metrics */}
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <StatCard label="Total Predictions" value={data.total_predictions.toLocaleString()} />
            <StatCard label="Success Rate" value={`${data.success_rate.toFixed(1)}%`} />
            <StatCard label="Avg. Confidence" value={`${data.average_confidence}%`} />
            <StatCard label="Avg. Agreement" value={`${Math.round(data.average_agreement_ratio * 100)}%`} />
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {/* Class distribution */}
            <Card className="space-y-4">
              <div className="flex items-center gap-2">
                <BarChart3 className="h-4 w-4 text-primary" />
                <h3 className="text-sm font-semibold">Class Distribution</h3>
              </div>
              {Object.keys(data.class_distribution).length === 0 ? (
                <p className="text-xs text-muted-foreground">No predictions yet.</p>
              ) : (
                <DistributionBars distribution={data.class_distribution} colorFor={getClassLabelColor} />
              )}
              {data.most_predicted_class && (
                <p className="text-xs text-muted-foreground">
                  Most predicted: <span className="font-medium text-foreground">{data.most_predicted_class}</span>
                </p>
              )}
            </Card>

            {/* Confidence distribution */}
            <Card className="space-y-4">
              <div className="flex items-center gap-2">
                <BarChart3 className="h-4 w-4 text-primary" />
                <h3 className="text-sm font-semibold">Confidence Distribution</h3>
              </div>
              {Object.keys(data.confidence_distribution).length === 0 ? (
                <p className="text-xs text-muted-foreground">No predictions yet.</p>
              ) : (
                <DistributionBars distribution={data.confidence_distribution} colorFor={() => '#6366f1'} />
              )}
            </Card>
          </div>

          {/* Activity windows + range */}
          <Card className="flex flex-wrap items-center gap-x-8 gap-y-3">
            <TimeStat label="Today" value={data.predictions_today} />
            <TimeStat label="This week" value={data.predictions_this_week} />
            <TimeStat label="This month" value={data.predictions_this_month} />
            {data.first_prediction_date && (
              <TimeStat label="First prediction" value={formatDateTime(data.first_prediction_date)} isText />
            )}
            {data.latest_prediction_date && (
              <TimeStat label="Latest prediction" value={formatDateTime(data.latest_prediction_date)} isText />
            )}
          </Card>

          <p className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
            <Download className="h-3 w-3" />
            Generated {formatDateTime(data.generated_at)} · analytics ID {data.analytics_id}
          </p>
        </>
      )}
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <Card className="space-y-1">
      <p className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</p>
      <p className="text-xl font-bold font-display">{value}</p>
    </Card>
  );
}

function TimeStat({ label, value, isText = false }: { label: string; value: number | string; isText?: boolean }) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</p>
      <p className={isText ? 'text-xs font-medium' : 'text-lg font-bold font-display'}>{value}</p>
    </div>
  );
}

function DistributionBars({
  distribution,
  colorFor,
}: {
  distribution: Record<string, number>;
  colorFor: (key: string) => string;
}) {
  const entries = Object.entries(distribution);
  const max = Math.max(...entries.map(([, v]) => v), 1);
  return (
    <div className="space-y-2.5">
      {entries.map(([key, count]) => (
        <div key={key} className="space-y-1">
          <div className="flex items-center justify-between text-xs">
            <span className="truncate">{key}</span>
            <span className="font-mono text-muted-foreground">{count}</span>
          </div>
          <div className="h-1.5 w-full rounded-full bg-secondary">
            <div
              className="h-1.5 rounded-full"
              style={{ width: `${(count / max) * 100}%`, backgroundColor: colorFor(key) }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
