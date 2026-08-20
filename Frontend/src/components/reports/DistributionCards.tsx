import { Card, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import type { AnalyticsSummary } from '@/types/reports';

function formatClassLabel(raw: string): string {
  return raw
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

function HorizontalBarRow({
  label,
  count,
  max,
  barClassName = 'bg-primary',
}: {
  label: string;
  count: number;
  max: number;
  barClassName?: string;
}) {
  const pct = max > 0 ? Math.round((count / max) * 100) : 0;
  return (
    <div>
      <div className="flex items-center justify-between text-xs mb-1">
        <span className="text-foreground font-medium">{label}</span>
        <span className="text-muted-foreground font-mono">{count}</span>
      </div>
      <div className="w-full h-2 rounded-full bg-muted overflow-hidden">
        <div className={`h-full rounded-full ${barClassName}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export function StatusBreakdownCard({ summary }: { summary: AnalyticsSummary }) {
  const { status_counts } = summary;
  const max = Math.max(...Object.values(status_counts), 1);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Status Breakdown</CardTitle>
      </CardHeader>
      <div className="space-y-3">
        <HorizontalBarRow label="Success" count={status_counts.success} max={max} barClassName="bg-success" />
        <HorizontalBarRow
          label="Partial Success"
          count={status_counts.partial_success}
          max={max}
          barClassName="bg-warning"
        />
        <HorizontalBarRow label="Failed" count={status_counts.failed} max={max} barClassName="bg-destructive" />
        {status_counts.pending > 0 && (
          <HorizontalBarRow label="Pending" count={status_counts.pending} max={max} barClassName="bg-muted-foreground" />
        )}
      </div>
    </Card>
  );
}

export function ClassDistributionCard({ summary }: { summary: AnalyticsSummary }) {
  const max = Math.max(...summary.class_distribution.map((c) => c.count), 1);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Class Distribution</CardTitle>
        <Badge variant="outline">Predicted class</Badge>
      </CardHeader>
      {summary.class_distribution.length === 0 ? (
        <p className="text-sm text-muted-foreground">No predictions to summarize yet.</p>
      ) : (
        <div className="space-y-3">
          {summary.class_distribution.map((c) => (
            <HorizontalBarRow
              key={c.predicted_class}
              label={formatClassLabel(c.predicted_class)}
              count={c.count}
              max={max}
            />
          ))}
        </div>
      )}
    </Card>
  );
}

export function ConfidenceDistributionCard({ summary }: { summary: AnalyticsSummary }) {
  const max = Math.max(...summary.confidence_distribution.map((b) => b.count), 1);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Confidence Distribution</CardTitle>
      </CardHeader>
      <div className="flex items-end gap-3 h-32">
        {summary.confidence_distribution.map((b) => {
          const heightPct = max > 0 ? Math.round((b.count / max) * 100) : 0;
          return (
            <div key={b.bucket_label} className="flex-1 flex flex-col items-center justify-end h-full gap-2">
              <span className="text-[11px] font-mono text-muted-foreground">{b.count}</span>
              <div
                className="w-full bg-accent rounded-t-sm min-h-[3px]"
                style={{ height: `${heightPct}%` }}
              />
              <span className="text-[10px] text-muted-foreground font-mono">{b.bucket_label}</span>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
