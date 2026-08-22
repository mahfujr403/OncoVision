import { Microscope, CheckCircle2, Activity, TrendingUp, ArrowRight, Brain } from 'lucide-react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { StatCard, Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { SectionTitle } from '@/components/ui/SectionTitle';
import { Skeleton } from '@/components/ui/Skeleton';
import { ROUTES } from '@/constants/routes';
import { useAuth } from '@/hooks/useAuth';
import { useAnalytics } from '@/hooks/queries/useAnalytics';
import { useAdminAnalytics } from '@/hooks/queries/useAdminHistory';
import { usePredictionHistory } from '@/hooks/queries/usePredictionHistory';
import { useMonitoring } from '@/hooks/queries/useMonitoring';
import { formatRelativeTime } from '@/utils/formatters';

// NOTE: every number and list on this page previously came from hardcoded
// mock arrays. It's now built entirely on GET /reports/analytics (or, for
// admins, GET /admin/analytics — see below), GET /predictions/history, and
// GET /monitoring — verified against the backend source. "Model Status"
// shows real per-model availability from the AI runtime rather than
// fabricated accuracy percentages, since the backend does not track
// offline accuracy per model.
export default function DashboardPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';

  // Regular users only ever see their own stats (GET /reports/analytics is
  // scoped to current_user.id server-side). Admins see stats aggregated
  // across every user, including other admins and themselves (GET
  // /admin/analytics with no user_id — verified against
  // app/api/v1/admin/analytics.py, which applies no role filter). Both
  // hooks are always called (Rules of Hooks); `enabled` decides which one
  // actually fires its request.
  const selfAnalytics = useAnalytics({ enabled: !isAdmin });
  const adminAnalytics = useAdminAnalytics(undefined, { enabled: isAdmin });
  const analytics = isAdmin ? adminAnalytics : selfAnalytics;

  const recent = usePredictionHistory({ page: 1, page_size: 4 });
  const monitoring = useMonitoring();

  return (
    <div className="space-y-6">
      {/* Welcome */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold font-display">
            Welcome back, {user?.full_name?.split(' ')[0]}
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            {new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })}
          </p>
        </div>
        <Button size="sm" asChild>
          <Link to={ROUTES.PREDICT}>
            <Microscope className="h-3.5 w-3.5" />
            New Prediction
          </Link>
        </Button>
      </div>

      {/* Stats */}
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
          {isAdmin ? 'Platform-wide Stats' : 'Your Stats'}
        </p>
        {isAdmin && (
          <Badge variant="info" className="text-[10px]">
            All users, including admins
          </Badge>
        )}
      </div>
      <motion.div
        className="grid grid-cols-2 lg:grid-cols-4 gap-3"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ staggerChildren: 0.05 }}
      >
        {analytics.isLoading || !analytics.data ? (
          Array.from({ length: 4 }).map((_, i) => (
            <Card key={i} className="space-y-2">
              <Skeleton className="h-3 w-20" />
              <Skeleton className="h-6 w-14" />
            </Card>
          ))
        ) : (
          <>
            <StatCard
              label="Total Predictions"
              value={analytics.data.total_predictions.toLocaleString()}
              icon={<Microscope className="h-4 w-4" />}
            />
            <StatCard
              label="Completed Today"
              value={String(analytics.data.predictions_today)}
              icon={<CheckCircle2 className="h-4 w-4" />}
            />
            <StatCard
              label="Avg. Confidence"
              value={`${analytics.data.average_confidence.toFixed(1)}%`}
              icon={<TrendingUp className="h-4 w-4" />}
            />
            <StatCard
              label="Success Rate"
              value={`${analytics.data.success_rate.toFixed(1)}%`}
              icon={<Activity className="h-4 w-4" />}
            />
          </>
        )}
      </motion.div>

      <div className="grid lg:grid-cols-3 gap-4">
        {/* Recent predictions */}
        <div className="lg:col-span-2 space-y-3">
          <SectionTitle
            title="Recent Predictions"
            description="Your latest histopathology classifications"
            action={
              <Button variant="ghost" size="xs" asChild>
                <Link to={ROUTES.HISTORY}>
                  View all <ArrowRight className="h-3 w-3" />
                </Link>
              </Button>
            }
          />

          <Card padding="none">
            {recent.isLoading ? (
              <div className="divide-y divide-border">
                {Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="flex items-center gap-3 px-4 py-3">
                    <Skeleton className="h-9 w-9 rounded-md" />
                    <div className="flex-1 space-y-1.5">
                      <Skeleton className="h-3 w-32" />
                      <Skeleton className="h-2.5 w-24" />
                    </div>
                  </div>
                ))}
              </div>
            ) : !recent.data || recent.data.items.length === 0 ? (
              <p className="px-4 py-6 text-center text-xs text-muted-foreground">
                No predictions yet — run your first analysis to see it here.
              </p>
            ) : (
              <div className="divide-y divide-border">
                {recent.data.items.map((p) => (
                  <Link
                    to={`${ROUTES.HISTORY}/${p.history_id}`}
                    key={p.history_id}
                    className="flex items-center gap-3 px-4 py-3 hover:bg-muted/20 transition-colors group"
                  >
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-primary/10">
                      <Microscope className="h-4 w-4 text-primary" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium truncate">{p.image_filename}</p>
                      <p className="text-[10px] text-muted-foreground mt-0.5">{p.predicted_class ?? '—'}</p>
                    </div>
                    <div className="shrink-0 text-right space-y-0.5">
                      <Badge
                        variant={p.confidence > 90 ? 'success' : p.confidence > 75 ? 'warning' : 'destructive'}
                        className="text-[10px]"
                      >
                        {p.confidence.toFixed(1)}%
                      </Badge>
                      <p className="text-[10px] text-muted-foreground">{formatRelativeTime(p.created_at)}</p>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </Card>
        </div>

        {/* Model status */}
        <div className="space-y-3">
          <SectionTitle
            title="Model Status"
            description="Live AI runtime state"
            action={
              <Button variant="ghost" size="xs" asChild>
                <Link to={ROUTES.ADMIN_SYSTEM_HEALTH}>
                  Details <ArrowRight className="h-3 w-3" />
                </Link>
              </Button>
            }
          />

          <Card className="space-y-3">
            {monitoring.isLoading || !monitoring.data ? (
              <Skeleton className="h-24 w-full" />
            ) : (
              <>
                <div className="flex items-center gap-2 pb-2 border-b border-border">
                  <div
                    className={`h-2 w-2 rounded-full ${monitoring.data.runtime.is_operational ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`}
                  />
                  <span className="text-xs text-muted-foreground">
                    {monitoring.data.runtime.loaded_model_count}/{monitoring.data.runtime.total_model_count} models
                    loaded
                  </span>
                </div>
                {monitoring.data.runtime.models.map((m) => (
                  <div key={m.model_id} className="flex items-center justify-between">
                    <span className="text-xs font-mono font-medium truncate">{m.display_name}</span>
                    <Badge variant={m.is_available ? 'success' : 'destructive'} dot className="text-[10px] capitalize">
                      {m.state}
                    </Badge>
                  </div>
                ))}
              </>
            )}
          </Card>

          {/* Quick actions */}
          <Card className="space-y-2" padding="sm">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Quick Actions</p>
            <div className="space-y-1">
              {[
                { label: 'New prediction', icon: <Microscope className="h-3.5 w-3.5" />, to: ROUTES.PREDICT },
                { label: 'Compare cases', icon: <Activity className="h-3.5 w-3.5" />, to: ROUTES.COMPARISON },
                { label: 'Run benchmark', icon: <Brain className="h-3.5 w-3.5" />, to: ROUTES.BENCHMARK },
              ].map((a) => (
                <Link
                  key={a.label}
                  to={a.to}
                  className="flex items-center gap-2 rounded-md px-2 py-1.5 text-xs text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
                >
                  {a.icon}
                  {a.label}
                </Link>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
