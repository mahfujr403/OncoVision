import { Zap, Server, Cpu, Clock, Activity } from 'lucide-react';
import { SectionTitle } from '@/components/ui/SectionTitle';
import { Card, CardHeader, CardTitle, CardContent, StatCard } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { formatInferenceTime } from '@/utils/formatters';

const SERVICES = [
  { name: 'API Gateway', status: 'healthy', latency: 12, uptime: 99.98 },
  { name: 'ML Inference Engine', status: 'healthy', latency: 820, uptime: 99.91 },
  { name: 'Image Preprocessor', status: 'healthy', latency: 34, uptime: 99.99 },
  { name: 'Report Generator', status: 'healthy', latency: 280, uptime: 99.87 },
  { name: 'Notification Service', status: 'degraded', latency: 450, uptime: 97.42 },
  { name: 'PostgreSQL', status: 'healthy', latency: 3, uptime: 99.99 },
];

export default function AdminSystemHealthPage() {
  const allHealthy = SERVICES.every((s) => s.status === 'healthy');

  return (
    <div className="space-y-5">
      <SectionTitle
        title="System Health"
        description="Real-time service status and infrastructure metrics"
        action={
          <Badge variant={allHealthy ? 'success' : 'warning'} dot>
            {allHealthy ? 'All systems operational' : 'Degraded performance'}
          </Badge>
        }
      />

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard label="Uptime" value="99.94%" delta="30-day average" deltaPositive icon={<Zap className="h-4 w-4" />} />
        <StatCard label="Requests / min" value="1,248" delta="12% above baseline" deltaPositive icon={<Activity className="h-4 w-4" />} />
        <StatCard label="Queue Depth" value="4" icon={<Clock className="h-4 w-4" />} />
        <StatCard label="Avg. Inference" value="740ms" delta="18ms faster" deltaPositive icon={<Cpu className="h-4 w-4" />} />
      </div>

      {/* Services */}
      <Card>
        <CardHeader>
          <CardTitle>Service Status</CardTitle>
        </CardHeader>
        <CardContent className="divide-y divide-border">
          {SERVICES.map((s) => (
            <div key={s.name} className="flex items-center gap-4 py-3">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-muted">
                <Server className="h-4 w-4 text-muted-foreground" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium">{s.name}</p>
                <p className="text-xs text-muted-foreground">Latency: {formatInferenceTime(s.latency)}</p>
              </div>
              <div className="text-right space-y-0.5">
                <Badge
                  variant={s.status === 'healthy' ? 'success' : s.status === 'degraded' ? 'warning' : 'destructive'}
                  dot
                  className="text-[10px] capitalize"
                >
                  {s.status}
                </Badge>
                <p className="text-[10px] text-muted-foreground">{s.uptime}% uptime</p>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Resource usage */}
      <div className="grid md:grid-cols-3 gap-4">
        {[
          { label: 'CPU Usage', value: 34, color: 'bg-primary' },
          { label: 'Memory Usage', value: 61, color: 'bg-accent' },
          { label: 'GPU Utilization', value: 78, color: 'bg-emerald-400' },
        ].map((r) => (
          <Card key={r.label} className="space-y-3">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium">{r.label}</p>
              <span className="font-mono text-lg font-bold">{r.value}%</span>
            </div>
            <div className="h-2 w-full rounded-full bg-secondary overflow-hidden">
              <div className={`h-full rounded-full ${r.color}`} style={{ width: `${r.value}%` }} />
            </div>
            <p className="text-xs text-muted-foreground">
              {r.value < 50 ? 'Normal' : r.value < 80 ? 'Moderate' : 'High'} utilization
            </p>
          </Card>
        ))}
      </div>
    </div>
  );
}
