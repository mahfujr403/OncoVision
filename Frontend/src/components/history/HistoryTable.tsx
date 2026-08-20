import { ChevronLeft, ChevronRight, Inbox } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorState } from '@/components/ui/ErrorState';
import { SkeletonTableRow } from '@/components/ui/Skeleton';
import type { HistoryRecord, PaginatedHistoryResponse } from '@/types/history';
import type { HistoryStatus } from '@/types/history';

function formatClassLabel(raw: string): string {
  if (!raw) return '—';
  return raw
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

function StatusBadge({ status }: { status: HistoryStatus }) {
  if (status === 'success') return <Badge variant="success" dot>Success</Badge>;
  if (status === 'partial_success') return <Badge variant="warning" dot>Partial</Badge>;
  if (status === 'failed') return <Badge variant="destructive" dot>Failed</Badge>;
  return <Badge variant="offline" dot>Pending</Badge>;
}

interface HistoryTableProps {
  loading: boolean;
  error: unknown;
  data: PaginatedHistoryResponse | null;
  onSelect: (record: HistoryRecord) => void;
  onPageChange: (page: number) => void;
  onRetry: () => void;
}

export function HistoryTable({ loading, error, data, onSelect, onPageChange, onRetry }: HistoryTableProps) {
  if (error) {
    return (
      <Card>
        <ErrorState
          variant="full"
          title="Couldn't load prediction history"
          message="An unexpected error occurred while loading your history. Please try again."
          onRetry={onRetry}
        />
      </Card>
    );
  }

  if (loading) {
    return (
      <Card padding="none">
        <div className="px-5 pt-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <SkeletonTableRow key={i} />
          ))}
        </div>
      </Card>
    );
  }

  if (!data || data.items.length === 0) {
    return (
      <Card>
        <EmptyState
          icon={<Inbox className="w-5 h-5" />}
          title="No predictions found"
          description="No history records match the current filters."
        />
      </Card>
    );
  }

  return (
    <Card padding="none">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-[11px] text-muted-foreground uppercase tracking-wide font-mono border-b border-border">
              <th className="px-5 py-2.5 font-medium">Date</th>
              <th className="px-5 py-2.5 font-medium">Image</th>
              <th className="px-5 py-2.5 font-medium">Predicted Class</th>
              <th className="px-5 py-2.5 font-medium">Confidence</th>
              <th className="px-5 py-2.5 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((record) => (
              <tr
                key={record.history_id}
                onClick={() => onSelect(record)}
                tabIndex={0}
                role="button"
                onKeyDown={(e) => {
                  if (e.key === 'Enter') onSelect(record);
                }}
                className="border-b border-border last:border-0 cursor-pointer hover:bg-muted/30 transition-colors focus-visible:outline-none focus-visible:bg-muted/40"
              >
                <td className="px-5 py-3 text-muted-foreground font-mono text-xs whitespace-nowrap">
                  {new Date(record.created_at).toLocaleString()}
                </td>
                <td className="px-5 py-3 font-mono text-xs text-foreground truncate max-w-[160px]">
                  {record.image_filename}
                </td>
                <td className="px-5 py-3 text-foreground">{formatClassLabel(record.predicted_class)}</td>
                <td className="px-5 py-3 text-foreground">
                  {record.status === 'failed' ? '—' : `${record.confidence.toFixed(1)}%`}
                </td>
                <td className="px-5 py-3">
                  <StatusBadge status={record.status} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between px-5 py-3 border-t border-border">
        <p className="text-xs text-muted-foreground">
          Page {data.page} of {data.total_pages} · {data.total_items} total
        </p>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            icon={<ChevronLeft className="w-3.5 h-3.5" />}
            disabled={data.page <= 1}
            onClick={() => onPageChange(data.page - 1)}
          >
            Prev
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={data.page >= data.total_pages}
            onClick={() => onPageChange(data.page + 1)}
          >
            Next
            <ChevronRight className="w-3.5 h-3.5 ml-1.5" />
          </Button>
        </div>
      </div>
    </Card>
  );
}

export default HistoryTable;
