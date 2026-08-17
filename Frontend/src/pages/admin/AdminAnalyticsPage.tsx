import { StatCard, Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { SectionTitle } from '@/components/ui/SectionTitle';
import { Activity, Users, Microscope, TrendingUp } from 'lucide-react';
import { CANCER_TYPE_LABELS, CANCER_TYPE_COLORS } from '@/constants/app';

const CLASS_DIST = [
  { label: 'lung_aca', count: 3241, pct: 0.32 },
  { label: 'colon_aca', count: 2890, pct: 0.29 },
  { label: 'lung_scc', count: 1876, pct: 0.19 },
  { label: 'lung_benign', count: 1102, pct: 0.11 },
  { label: 'colon_benign', count: 891, pct: 0.09 },
];

const DAILY_PREDICTIONS = [
  { day: 'Mon', count: 142 },
  { day: 'Tue', count: 198 },
  { day: 'Wed', count: 167 },
  { day: 'Thu', count: 214 },
  { day: 'Fri', count: 189 },
  { day: 'Sat', count: 78 },
  { day: 'Sun', count: 52 },
];

const MAX_COUNT = Math.max(...DAILY_PREDICTIONS.map((d) => d.count));

export default function AdminAnalyticsPage() {
  return (
    <div className="space-y-5">
      <SectionTitle title="Analytics" description="Platform-wide usage and prediction statistics" />

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard label="Total Users" value="142" delta="12 this month" deltaPositive icon={<Users className="h-4 w-4" />} />
        <StatCard label="Total Predictions" value="9,986" delta="8.4% this week" deltaPositive icon={<Microscope className="h-4 w-4" />} />
        <StatCard label="Avg. Confidence" value="93.4%" delta="0.8% vs prev. month" deltaPositive icon={<TrendingUp className="h-4 w-4" />} />
        <StatCard label="Active Models" value="6/6" icon={<Activity className="h-4 w-4" />} />
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        {/* Weekly predictions bar chart (manual) */}
        <Card>
          <CardHeader>
            <CardTitle>Predictions This Week</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-end gap-2 h-32">
              {DAILY_PREDICTIONS.map((d) => (
                <div key={d.day} className="flex-1 flex flex-col items-center gap-1">
                  <span className="text-[10px] text-muted-foreground font-mono">{d.count}</span>
                  <div
                    className="w-full rounded-t bg-primary/80 hover:bg-primary transition-colors"
                    style={{ height: `${(d.count / MAX_COUNT) * 100}%` }}
                  />
                  <span className="text-[10px] text-muted-foreground">{d.day}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Class distribution */}
        <Card>
          <CardHeader>
            <CardTitle>Classification Distribution</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {CLASS_DIST.map((c) => (
              <div key={c.label} className="space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-medium">{CANCER_TYPE_LABELS[c.label]}</span>
                  <span className="font-mono text-muted-foreground">{c.count.toLocaleString()} ({(c.pct * 100).toFixed(0)}%)</span>
                </div>
                <div className="h-1.5 w-full rounded-full bg-secondary overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all"
                    style={{ width: `${c.pct * 100}%`, backgroundColor: CANCER_TYPE_COLORS[c.label] }}
                  />
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
