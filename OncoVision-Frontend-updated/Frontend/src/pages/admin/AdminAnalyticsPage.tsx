import { Activity, Users, Microscope, TrendingUp } from 'lucide-react';
import { StatCard, Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { SectionTitle } from '@/components/ui/SectionTitle';
import { ErrorState } from '@/components/ui/ErrorState';
import { Skeleton } from '@/components/ui/Skeleton';
import { useAnalytics } from '@/hooks/queries/useAnalytics';
import { useAdminUsers } from '@/hooks/queries/useAdminUsers';
import { useMonitoring } from '@/hooks/queries/useMonitoring';
import { getClassLabelColor } from '@/constants/app';

// NOTE: GET /api/v1/reports/analytics is not scoped per-user, so this
// admin view is built on the same underlying data as the user-facing
// Reports page — the value-add here is combining it with admin-only
// context (total registered users, live model runtime) in one place. The
// previous version of this page had a fabricated "Predictions This Week"
// daily bar chart; the backend has no per-day breakdown endpoint, so that
// chart has been removed rather than faked.
export default function AdminAnalyticsPage() {
  const analytics = useAnalytics();
  const users = useAdminUsers({ page: 1, page_size: 1 });
  const monitoring = useMonitoring();

  const isLoading = analytics.isLoading || users.isLoading || monitoring.isLoading;
  const isError = analytics.isError || users.isError || monitoring.isError;

  return (
    <div className="space-y-5">
      <SectionTitle title="Analytics" description="Platform-wide usage and prediction statistics" />

      {isError ? (
        <ErrorState
          message="Couldn't load analytics."
          onRetry={() => {
            analytics.refetch();
            users.refetch();
            monitoring.refetch();
          }}
        />
      ) : isLoading || !analytics.data ? (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Card key={i} className="space-y-2">
              <Skeleton className="h-3 w-20" />
              <Skeleton className="h-6 w-14" />
            </Card>
          ))}
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <StatCard
              label="Total Users"
              value={users.data ? String(users.data.pagination.total_records) : '—'}
              icon={<Users className="h-4 w-4" />}
            />
            <StatCard
              label="Total Predictions"
              value={analytics.data.total_predictions.toLocaleString()}
              icon={<Microscope className="h-4 w-4" />}
            />
            <StatCard
              label="Avg. Confidence"
              value={`${analytics.data.average_confidence.toFixed(1)}%`}
              icon={<TrendingUp className="h-4 w-4" />}
            />
            <StatCard
              label="Active Models"
              value={
                monitoring.data
                  ? `${monitoring.data.runtime.loaded_model_count}/${monitoring.data.runtime.total_model_count}`
                  : '—'
              }
              icon={<Activity className="h-4 w-4" />}
            />
          </div>

          <div className="grid md:grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <CardTitle>Predictions This Period</CardTitle>
              </CardHeader>
              <CardContent className="grid grid-cols-3 gap-3 text-center">
                <PeriodStat label="Today" value={analytics.data.predictions_today} />
                <PeriodStat label="This Week" value={analytics.data.predictions_this_week} />
                <PeriodStat label="This Month" value={analytics.data.predictions_this_month} />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Classification Distribution</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {Object.keys(analytics.data.class_distribution).length === 0 ? (
                  <p className="text-xs text-muted-foreground">No predictions yet.</p>
                ) : (
                  Object.entries(analytics.data.class_distribution).map(([label, count]) => {
                    const total = analytics.data!.total_predictions || 1;
                    const pct = (count / total) * 100;
                    return (
                      <div key={label} className="space-y-1">
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-medium">{label}</span>
                          <span className="font-mono text-muted-foreground">
                            {count.toLocaleString()} ({pct.toFixed(0)}%)
                          </span>
                        </div>
                        <div className="h-1.5 w-full rounded-full bg-secondary overflow-hidden">
                          <div
                            className="h-full rounded-full transition-all"
                            style={{ width: `${pct}%`, backgroundColor: getClassLabelColor(label) }}
                          />
                        </div>
                      </div>
                    );
                  })
                )}
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}

function PeriodStat({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <p className="text-lg font-bold font-display">{value}</p>
      <p className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</p>
    </div>
  );
}
