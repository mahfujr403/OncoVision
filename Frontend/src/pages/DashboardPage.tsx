import { useState } from 'react';
import { ScanLine, Server, Activity, Clock, ArrowRight, Plus, Inbox } from 'lucide-react';
import type { User, PageId } from '@/types';
import { Card, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { SkeletonCard } from '@/components/ui/Skeleton';
import { EmptyState } from '@/components/ui/EmptyState';

interface DashboardPageProps {
  user: User;
  onNavigate: (page: PageId) => void;
}

function StatusCard({
  icon,
  title,
  children,
  iconBg,
}: {
  icon: React.ReactNode;
  title: string;
  children: React.ReactNode;
  iconBg: string;
}) {
  return (
    <Card className="flex flex-col gap-4">
      <CardHeader className="mb-0">
        <CardTitle>{title}</CardTitle>
        <div className={`w-8 h-8 rounded-md flex items-center justify-center shrink-0 ${iconBg}`}>
          {icon}
        </div>
      </CardHeader>
      {children}
    </Card>
  );
}

export function DashboardPage({ user, onNavigate }: DashboardPageProps) {
  const [showSkeleton] = useState(true);

  const greeting = () => {
    const h = new Date().getHours();
    if (h < 12) return 'Good morning';
    if (h < 17) return 'Good afternoon';
    return 'Good evening';
  };

  return (
    <div className="p-6 max-w-[1280px] mx-auto space-y-8">
      {/* Welcome header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground">
            {greeting()}, {user.name.split(' ')[0]}
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            OncoVision AI — Lung &amp; Colon Histopathology Analysis Platform
          </p>
        </div>
        <Button
          variant="primary"
          size="md"
          icon={<Plus className="w-4 h-4" />}
          onClick={() => onNavigate('predict')}
          className="shrink-0 hidden sm:inline-flex"
        >
          New Prediction
        </Button>
      </div>

      {/* Summary cards */}
      <div>
        <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-4">
          Overview
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
          {/* Recent Predictions — disconnected */}
          <StatusCard
            title="Recent Predictions"
            icon={<ScanLine className="w-4 h-4 text-primary" />}
            iconBg="bg-primary/10"
          >
            <div className="space-y-1.5">
              <p className="text-[11px] text-muted-foreground font-mono uppercase tracking-wide">Status</p>
              <Badge variant="offline" dot>Connect to backend</Badge>
              <p className="text-xs text-muted-foreground">Load prediction activity from backend to see results here.</p>
            </div>
          </StatusCard>

          {/* Model Availability — unavailable */}
          <StatusCard
            title="Model Availability"
            icon={<Server className="w-4 h-4 text-muted-foreground" />}
            iconBg="bg-muted"
          >
            <div className="space-y-1.5">
              <p className="text-[11px] text-muted-foreground font-mono uppercase tracking-wide">Models</p>
              <Badge variant="offline" dot>System data unavailable</Badge>
              <p className="text-xs text-muted-foreground font-mono">
                MobileNetV2 · DenseNet121 · EfficientNetV2B0+
              </p>
            </div>
          </StatusCard>

          {/* Analysis Activity — skeleton */}
          {showSkeleton ? (
            <SkeletonCard />
          ) : (
            <StatusCard
              title="Analysis Activity"
              icon={<Activity className="w-4 h-4 text-success" />}
              iconBg="bg-success/10"
            >
              <p className="text-xs text-muted-foreground">No data available.</p>
            </StatusCard>
          )}

          {/* System Status */}
          <StatusCard
            title="System Status"
            icon={<Clock className="w-4 h-4 text-warning" />}
            iconBg="bg-warning/10"
          >
            <div className="space-y-1.5">
              <p className="text-[11px] text-muted-foreground font-mono uppercase tracking-wide">Backend</p>
              <Badge variant="warning" dot>Awaiting backend data</Badge>
              <p className="text-xs text-muted-foreground">Connect to backend to load system information.</p>
            </div>
          </StatusCard>
        </div>
      </div>

      {/* Quick action + recent activity */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-5">
        {/* Quick action */}
        <Card className="lg:col-span-2 flex flex-col gap-5">
          <div>
            <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center mb-4">
              <ScanLine className="w-5 h-5 text-primary" />
            </div>
            <h3 className="text-base font-semibold text-foreground">Start New Prediction</h3>
            <p className="text-sm text-muted-foreground mt-1.5 leading-relaxed">
              Upload a supported histopathology image to begin AI-assisted analysis. Supported formats:{' '}
              <span className="font-mono text-xs">JPG · PNG · TIFF</span>
            </p>
          </div>
          <div className="flex items-center gap-2 pt-1 border-t border-border">
            <Button
              variant="primary"
              size="sm"
              onClick={() => onNavigate('predict')}
              icon={<ArrowRight className="w-3.5 h-3.5" />}
            >
              Go to Predict
            </Button>
            <Button variant="ghost" size="sm" onClick={() => onNavigate('history')}>
              View History
            </Button>
          </div>
        </Card>

        {/* Recent activity */}
        <Card className="lg:col-span-3 flex flex-col" padding="none">
          <div className="flex items-center justify-between px-5 py-4 border-b border-border">
            <h3 className="text-sm font-semibold text-foreground">Recent Activity</h3>
            <button
              onClick={() => onNavigate('history')}
              className="text-xs text-primary hover:underline font-medium"
            >
              View all
            </button>
          </div>

          <div className="flex-1">
            <EmptyState
              icon={<Inbox className="w-5 h-5" />}
              title="No predictions yet"
              description="Analyze your first histopathology image to see activity here."
              action={{ label: 'Start Prediction', onClick: () => onNavigate('predict') }}
              compact
            />
          </div>
        </Card>
      </div>

      {/* Models info footer */}
      <div className="rounded-lg border border-border bg-muted/30 px-5 py-4">
        <p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-widest mb-2">
          Platform Information
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {[
            { label: 'Model Engine', value: 'Ensemble + Single' },
            { label: 'Target Classes', value: 'Lung · Colon' },
            { label: 'Data Source', value: 'Backend API' },
            { label: 'Status', value: 'Under Development' },
          ].map((item) => (
            <div key={item.label}>
              <p className="text-[10px] text-muted-foreground uppercase tracking-wide font-mono">
                {item.label}
              </p>
              <p className="text-xs font-medium text-foreground mt-0.5 font-mono">{item.value}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default DashboardPage;
