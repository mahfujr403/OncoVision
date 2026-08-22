import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Microscope, Filter, X } from 'lucide-react';
import { SectionTitle } from '@/components/ui/SectionTitle';
import { SearchBox } from '@/components/ui/SearchBox';
import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorState } from '@/components/ui/ErrorState';
import { Pagination } from '@/components/ui/Pagination';
import { Skeleton } from '@/components/ui/Skeleton';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/Table';
import { Button } from '@/components/ui/Button';
import { usePredictionHistory } from '@/hooks/queries/usePredictionHistory';
import { usePagination } from '@/hooks/usePagination';
import { formatDateTime } from '@/utils/formatters';
import { KNOWN_CLASS_LABELS } from '@/constants/app';
import { ROUTES } from '@/constants/routes';
import type { PredictionHistoryItem, PredictionHistoryStatus } from '@/types';

const STATUS_OPTIONS: { value: PredictionHistoryStatus; label: string }[] = [
  { value: 'success', label: 'Success' },
  { value: 'partial_success', label: 'Partial success' },
  { value: 'failed', label: 'Failed' },
  { value: 'pending', label: 'Pending' },
];

export default function HistoryPage() {
  const { page, pageSize, goToPage } = usePagination();
  const [statusFilter, setStatusFilter] = useState<PredictionHistoryStatus | ''>('');
  const [classFilter, setClassFilter] = useState('');
  const [filtersOpen, setFiltersOpen] = useState(false);
  // The backend has no full-text search on filename (verified against
  // app/api/v1/history/router.py — only status/predicted_class/date/
  // confidence filters exist). This box filters only the currently loaded
  // page rather than pretending to search the whole dataset.
  const [pageQuery, setPageQuery] = useState('');

  const { data, isLoading, isError, refetch } = usePredictionHistory({
    page,
    page_size: pageSize,
    status: statusFilter || undefined,
    predicted_class: classFilter || undefined,
  });

  const items = data?.items ?? [];
  const visibleItems = pageQuery
    ? items.filter(
        (h) =>
          h.image_filename.toLowerCase().includes(pageQuery.toLowerCase()) ||
          (h.predicted_class ?? '').toLowerCase().includes(pageQuery.toLowerCase()),
      )
    : items;

  const hasActiveFilters = Boolean(statusFilter || classFilter);

  return (
    <div className="space-y-5">
      <SectionTitle
        title="Prediction History"
        description={data ? `${data.pagination.total_records} total predictions` : 'Loading…'}
        action={
          <Button variant="outline" size="sm" onClick={() => setFiltersOpen((v) => !v)}>
            <Filter className="h-3.5 w-3.5" />
            Filter
            {hasActiveFilters && <Badge variant="default" className="ml-1 px-1.5">•</Badge>}
          </Button>
        }
      />

      <div className="flex flex-wrap items-center gap-3">
        <SearchBox
          value={pageQuery}
          onChange={setPageQuery}
          placeholder="Filter this page by filename or class…"
          className="max-w-sm"
        />
      </div>

      {filtersOpen && (
        <Card className="flex flex-wrap items-end gap-4">
          <FilterField label="Status">
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value as PredictionHistoryStatus | '');
                goToPage(1);
              }}
              className="h-9 rounded-md border border-border bg-secondary px-3 text-sm"
            >
              <option value="">Any status</option>
              {STATUS_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </FilterField>

          <FilterField label="Predicted class">
            <select
              value={classFilter}
              onChange={(e) => {
                setClassFilter(e.target.value);
                goToPage(1);
              }}
              className="h-9 rounded-md border border-border bg-secondary px-3 text-sm"
            >
              <option value="">Any class</option>
              {KNOWN_CLASS_LABELS.map((label) => (
                <option key={label} value={label}>
                  {label}
                </option>
              ))}
            </select>
          </FilterField>

          {hasActiveFilters && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setStatusFilter('');
                setClassFilter('');
                goToPage(1);
              }}
              className="gap-1"
            >
              <X className="h-3.5 w-3.5" />
              Clear
            </Button>
          )}
        </Card>
      )}

      <Card padding="none">
        {isError ? (
          <ErrorState message="Couldn't load prediction history." onRetry={() => refetch()} />
        ) : isLoading ? (
          <div className="divide-y divide-border">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="flex items-center gap-4 px-4 py-3">
                <Skeleton className="h-3 w-16" />
                <Skeleton className="h-3 w-32" />
                <Skeleton className="h-3 w-28" />
                <Skeleton className="h-5 w-14 rounded-full" />
                <Skeleton className="h-5 w-16 rounded-full" />
                <Skeleton className="h-3 w-24" />
              </div>
            ))}
          </div>
        ) : visibleItems.length === 0 ? (
          <EmptyState
            icon={<Microscope className="h-6 w-6" />}
            title="No predictions found"
            description={
              pageQuery || hasActiveFilters
                ? 'Try a different filter.'
                : 'Run your first prediction to see it here.'
            }
          />
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>Image</TableHead>
                <TableHead>Predicted Class</TableHead>
                <TableHead>Confidence</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Date</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {visibleItems.map((h) => (
                <HistoryRow key={h.history_id} item={h} />
              ))}
            </TableBody>
          </Table>
        )}
      </Card>

      {data && data.pagination.total_pages > 1 && (
        <div className="flex justify-end">
          <Pagination page={page} totalPages={data.pagination.total_pages} onPageChange={goToPage} />
        </div>
      )}
    </div>
  );
}

function HistoryRow({ item }: { item: PredictionHistoryItem }) {
  const navigate = useNavigate();
  return (
    <TableRow className="cursor-pointer" onClick={() => navigate(`${ROUTES.HISTORY}/${item.history_id}`)}>
      <TableCell className="font-mono text-[11px] text-muted-foreground">
        {item.history_id.slice(0, 8)}
      </TableCell>
      <TableCell className="font-medium text-xs max-w-[160px] truncate">{item.image_filename}</TableCell>
      <TableCell className="text-xs">{item.predicted_class ?? '—'}</TableCell>
      <TableCell>
        <Badge
          variant={item.confidence > 90 ? 'success' : item.confidence > 75 ? 'warning' : 'destructive'}
          className="font-mono text-[10px]"
        >
          {item.confidence}%
        </Badge>
      </TableCell>
      <TableCell>
        <Badge
          variant={item.status === 'success' ? 'success' : item.status === 'failed' ? 'destructive' : 'warning'}
          dot
          className="text-[10px] capitalize"
        >
          {item.status.replace('_', ' ')}
        </Badge>
      </TableCell>
      <TableCell className="text-[11px] text-muted-foreground">{formatDateTime(item.created_at)}</TableCell>
    </TableRow>
  );
}

function FilterField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-xs font-medium text-muted-foreground">{label}</span>
      {children}
    </div>
  );
}
