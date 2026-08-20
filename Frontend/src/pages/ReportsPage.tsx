import { useEffect, useState } from 'react';
import { BarChart3 } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';
import { SkeletonCard } from '@/components/ui/Skeleton';
import { ErrorState } from '@/components/ui/ErrorState';
import { AnalyticsSummaryCards } from '@/components/reports/AnalyticsSummaryCards';
import {
  StatusBreakdownCard,
  ClassDistributionCard,
  ConfidenceDistributionCard,
} from '@/components/reports/DistributionCards';
import { ExportPanel } from '@/components/reports/ExportPanel';
import { simulateAnalyticsRequest } from '@/lib/mockReports';
import type { AnalyticsSummary } from '@/types/reports';

export function ReportsPage() {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const result = await simulateAnalyticsRequest();
      setSummary(result);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="p-6 max-w-[1100px] mx-auto space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-lg bg-primary/10 flex items-center justify-center text-primary shrink-0">
            <BarChart3 className="w-4.5 h-4.5" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-foreground">Reports &amp; Analytics</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Summary statistics across your prediction history.
            </p>
          </div>
        </div>
        <Badge variant="warning" dot className="shrink-0 hidden sm:inline-flex">
          Simulated data — analytics schema unverified, see notes
        </Badge>
      </div>

      {Boolean(error) && (
        <Card>
          <ErrorState
            variant="full"
            title="Couldn't load analytics"
            message="An unexpected error occurred while loading report data. Please try again."
            onRetry={load}
          />
        </Card>
      )}

      {loading && !error && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      )}

      {!loading && !error && summary && (
        <>
          <AnalyticsSummaryCards summary={summary} />

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            <StatusBreakdownCard summary={summary} />
            <ConfidenceDistributionCard summary={summary} />
          </div>

          <ClassDistributionCard summary={summary} />

          <ExportPanel />
        </>
      )}

      <div className="sm:hidden">
        <Badge variant="warning" dot>
          Simulated data — analytics schema unverified
        </Badge>
      </div>
    </div>
  );
}

export default ReportsPage;
