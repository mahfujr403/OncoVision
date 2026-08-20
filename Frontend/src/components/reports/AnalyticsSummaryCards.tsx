import { ScanLine, CheckCircle2, Gauge, Clock } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import type { AnalyticsSummary } from '@/types/reports';

export function AnalyticsSummaryCards({ summary }: { summary: AnalyticsSummary }) {
  const successRate =
    summary.total_predictions > 0
      ? Math.round(
          ((summary.status_counts.success + summary.status_counts.partial_success) /
            summary.total_predictions) *
            100
        )
      : 0;

  const items = [
    {
      icon: <ScanLine className="w-4 h-4 text-primary" />,
      iconBg: 'bg-primary/10',
      label: 'Total Predictions',
      value: summary.total_predictions.toLocaleString(),
    },
    {
      icon: <CheckCircle2 className="w-4 h-4 text-success" />,
      iconBg: 'bg-success/10',
      label: 'Success Rate',
      value: `${successRate}%`,
    },
    {
      icon: <Gauge className="w-4 h-4 text-accent" />,
      iconBg: 'bg-accent/10',
      label: 'Avg. Confidence',
      value: `${summary.average_confidence.toFixed(1)}%`,
    },
    {
      icon: <Clock className="w-4 h-4 text-warning" />,
      iconBg: 'bg-warning/10',
      label: 'Avg. Processing Time',
      value: `${summary.average_processing_time_ms} ms`,
    },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {items.map((item) => (
        <Card key={item.label} className="flex flex-col gap-3">
          <div className={`w-8 h-8 rounded-md flex items-center justify-center ${item.iconBg}`}>{item.icon}</div>
          <div>
            <p className="text-[11px] text-muted-foreground uppercase tracking-wide font-mono">{item.label}</p>
            <p className="text-xl font-bold text-foreground mt-0.5">{item.value}</p>
          </div>
        </Card>
      ))}
    </div>
  );
}

export default AnalyticsSummaryCards;
