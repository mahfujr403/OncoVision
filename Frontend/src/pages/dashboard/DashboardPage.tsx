import {
  Microscope, CheckCircle2, Activity, TrendingUp,
  ArrowRight, Brain, Zap,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { StatCard, Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { SectionTitle } from '@/components/ui/SectionTitle';
import { ROUTES } from '@/constants/routes';
import { useAuth } from '@/hooks/useAuth';
import { formatRelativeTime, formatPercent } from '@/utils/formatters';

const RECENT_PREDICTIONS = [
  { id: 'p1', image: 'slide_001.tiff', label: 'Lung Adenocarcinoma', confidence: 0.973, status: 'completed', createdAt: new Date(Date.now() - 1000 * 60 * 15).toISOString() },
  { id: 'p2', image: 'colon_biopsy_04.jpg', label: 'Colon Benign', confidence: 0.891, status: 'completed', createdAt: new Date(Date.now() - 1000 * 60 * 80).toISOString() },
  { id: 'p3', image: 'lung_sq_case7.png', label: 'Lung Squamous Cell Carcinoma', confidence: 0.944, status: 'completed', createdAt: new Date(Date.now() - 1000 * 60 * 240).toISOString() },
  { id: 'p4', image: 'h_e_stain_28.tiff', label: 'Colon Adenocarcinoma', confidence: 0.812, status: 'completed', createdAt: new Date(Date.now() - 1000 * 60 * 480).toISOString() },
];

const MODEL_STATS = [
  { name: 'ResNet50', accuracy: 0.974, status: 'active' },
  { name: 'EfficientNetB4', accuracy: 0.989, status: 'active' },
  { name: 'DenseNet121', accuracy: 0.981, status: 'active' },
  { name: 'ViT-B16', accuracy: 0.991, status: 'active' },
];

export default function DashboardPage() {
  const { user } = useAuth();

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
      <motion.div
        className="grid grid-cols-2 lg:grid-cols-4 gap-3"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ staggerChildren: 0.05 }}
      >
        <StatCard
          label="Total Predictions"
          value="1,248"
          delta="12% this week"
          deltaPositive
          icon={<Microscope className="h-4 w-4" />}
        />
        <StatCard
          label="Completed Today"
          value="34"
          delta="8 pending"
          icon={<CheckCircle2 className="h-4 w-4" />}
        />
        <StatCard
          label="Avg. Confidence"
          value="93.7%"
          delta="1.2% vs last month"
          deltaPositive
          icon={<TrendingUp className="h-4 w-4" />}
        />
        <StatCard
          label="Avg. Inference"
          value="0.74s"
          delta="4ms faster"
          deltaPositive
          icon={<Zap className="h-4 w-4" />}
        />
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
            <div className="divide-y divide-border">
              {RECENT_PREDICTIONS.map((p) => (
                <div key={p.id} className="flex items-center gap-3 px-4 py-3 hover:bg-muted/20 transition-colors group">
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-primary/10">
                    <Microscope className="h-4 w-4 text-primary" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium truncate">{p.image}</p>
                    <p className="text-[10px] text-muted-foreground mt-0.5">{p.label}</p>
                  </div>
                  <div className="shrink-0 text-right space-y-0.5">
                    <Badge
                      variant={p.confidence > 0.9 ? 'success' : p.confidence > 0.75 ? 'warning' : 'destructive'}
                      className="text-[10px]"
                    >
                      {formatPercent(p.confidence)}
                    </Badge>
                    <p className="text-[10px] text-muted-foreground">{formatRelativeTime(p.createdAt)}</p>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>

        {/* Model status */}
        <div className="space-y-3">
          <SectionTitle
            title="Model Status"
            description="Active ensemble models"
            action={
              <Button variant="ghost" size="xs" asChild>
                <Link to={ROUTES.BENCHMARK}>
                  Benchmark <ArrowRight className="h-3 w-3" />
                </Link>
              </Button>
            }
          />

          <Card className="space-y-3">
            <div className="flex items-center gap-2 pb-2 border-b border-border">
              <div className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-xs text-muted-foreground">All systems operational</span>
            </div>
            {MODEL_STATS.map((m) => (
              <div key={m.name} className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-medium">{m.name}</span>
                  <Badge variant="success" dot className="text-[10px]">
                    {formatPercent(m.accuracy)}
                  </Badge>
                </div>
                <div className="h-1.5 w-full rounded-full bg-secondary overflow-hidden">
                  <div
                    className="h-full rounded-full bg-primary transition-all"
                    style={{ width: `${m.accuracy * 100}%` }}
                  />
                </div>
              </div>
            ))}
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
