import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Microscope, Filter, X, ChevronDown } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { SectionTitle } from '@/components/ui/SectionTitle';
import { SearchBox } from '@/components/ui/SearchBox';
import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';
import { EmptyState } from '@/components/ui/EmptyState';
import { Pagination } from '@/components/ui/Pagination';
import { Skeleton } from '@/components/ui/Skeleton';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/Table';
import { Button } from '@/components/ui/Button';
import { ErrorState } from '@/components/ui/ErrorState';
import { useSearch } from '@/hooks/useSearch';
import { usePagination } from '@/hooks/usePagination';
import { formatDateTime } from '@/utils/formatters';
import { useHistoryList } from '@/features/history/hooks/useHistoryQueries';
import type { BackendPredictionStatus } from '@/types';
import type { PredictionHistoryFilters } from '@/features/history/types';

const STATUS_OPTIONS: { label: string; value: BackendPredictionStatus | '' }[] = [
  { label: 'All statuses', value: '' },
  { label: 'Success', value: 'success' },
  { label: 'Partial success', value: 'partial_success' },
  { label: 'Failed', value: 'failed' },
  { label: 'Pending', value: 'pending' },
];

function statusBadgeVariant(status: BackendPredictionStatus) {
  switch (status) {
    case 'success': return 'success' as const;
    case 'partial_success': return 'warning' as const;
    case 'failed': return 'destructive' as const;
    default: return 'default' as const;
  }
}

function statusLabel(status: BackendPredictionStatus) {
  return status.replace('_', ' ');
}

function SkeletonTableRows() {
  return (
    <>
      {Array.from({ length: 8 }).map((_, i) => (
        <TableRow key={i} aria-hidden>
          <TableCell><Skeleton className="h-3 w-20" /></TableCell>
          <TableCell><Skeleton className="h-3 w-40" /></TableCell>
          <TableCell><Skeleton className="h-3 w-28" /></TableCell>
          <TableCell><Skeleton className="h-5 w-16 rounded-full" /></TableCell>
          <TableCell><Skeleton className="h-5 w-20 rounded-full" /></TableCell>
          <TableCell><Skeleton className="h-3 w-28" /></TableCell>
        </TableRow>
      ))}
    </>
  );
}

export default function HistoryPage() {
  const navigate = useNavigate();
  const { query: predictedClass, debouncedQuery: debouncedClass, handleSearch, clearSearch } = useSearch();
  const { page, pageSize, goToPage, reset: resetPage } = usePagination({ initialPageSize: 20 });

  const [showFilters, setShowFilters] = useState(false);
  const [status, setStatus] = useState<BackendPredictionStatus | ''>('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [minConf, setMinConf] = useState('');
  const [maxConf, setMaxConf] = useState('');

  const hasActiveFilters =
    Boolean(status) || Boolean(debouncedClass) || Boolean(startDate) ||
    Boolean(endDate) || Boolean(minConf) || Boolean(maxConf);

  const filters: PredictionHistoryFilters = {
    page,
    page_size: pageSize,
    ...(status ? { status } : {}),
    ...(debouncedClass ? { predicted_class: debouncedClass } : {}),
    ...(startDate ? { start_date: startDate } : {}),
    ...(endDate ? { end_date: endDate } : {}),
    ...(minConf !== '' ? { min_confidence: parseFloat(minConf) } : {}),
    ...(maxConf !== '' ? { max_confidence: parseFloat(maxConf) } : {}),
  };

  const { data, isLoading, isError, error, isFetching } = useHistoryList(filters);

  const clearFilters = useCallback(() => {
    setStatus('');
    clearSearch();
    setStartDate('');
    setEndDate('');
    setMinConf('');
    setMaxConf('');
    resetPage();
  }, [clearSearch, resetPage]);

  const handleFilterChange = useCallback(() => resetPage(), [resetPage]);

  const pagination = data?.pagination;
  const items = data?.items ?? [];
  const totalRecords = pagination?.total_records ?? 0;
  const totalPages = pagination?.total_pages ?? 1;

  const errorMsg = (error as { message?: string })?.message ?? 'Failed to load prediction history.';

  return (
    <div className="space-y-5">
      <SectionTitle
        title="Prediction History"
        description={
          isLoading ? 'Loading…' :
          hasActiveFilters ? `${totalRecords} result${totalRecords !== 1 ? 's' : ''} matching filters` :
          `${totalRecords} total prediction${totalRecords !== 1 ? 's' : ''}`
        }
        action={
          <Button
            variant={showFilters || hasActiveFilters ? 'default' : 'outline'}
            size="sm"
            onClick={() => setShowFilters((v) => !v)}
            aria-expanded={showFilters}
            aria-controls="history-filters"
          >
            <Filter className="h-3.5 w-3.5 mr-1.5" />
            Filter
            {hasActiveFilters && (
              <span className="ml-1.5 flex h-4 w-4 items-center justify-center rounded-full bg-primary-foreground text-primary text-[10px] font-bold">
                {[status, debouncedClass, startDate, endDate, minConf, maxConf].filter(Boolean).length}
              </span>
            )}
            <ChevronDown className={`h-3 w-3 ml-1 transition-transform ${showFilters ? 'rotate-180' : ''}`} />
          </Button>
        }
      />

      {/* Search */}
      <div className="flex items-center gap-3">
        <SearchBox
          value={predictedClass}
          onChange={(v) => { handleSearch(v); handleFilterChange(); }}
          placeholder="Filter by predicted class…"
          className="max-w-sm"
        />
        {isFetching && !isLoading && (
          <span className="text-[11px] text-muted-foreground animate-pulse">Updating…</span>
        )}
        {hasActiveFilters && (
          <Button variant="ghost" size="sm" onClick={clearFilters} className="text-muted-foreground gap-1">
            <X className="h-3.5 w-3.5" /> Clear filters
          </Button>
        )}
      </div>

      {/* Filter panel */}
      <AnimatePresence>
        {showFilters && (
          <motion.div
            id="history-filters"
            key="filters"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="rounded-lg border border-border bg-card p-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {/* Status */}
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground">Status</label>
                <select
                  value={status}
                  onChange={(e) => { setStatus(e.target.value as BackendPredictionStatus | ''); handleFilterChange(); }}
                  className="h-8 w-full rounded-md border border-border bg-secondary px-3 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
                  aria-label="Filter by status"
                >
                  {STATUS_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </div>

              {/* Confidence range */}
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground">Min confidence (%)</label>
                <input
                  type="number"
                  min={0}
                  max={100}
                  step={1}
                  value={minConf}
                  onChange={(e) => { setMinConf(e.target.value); handleFilterChange(); }}
                  placeholder="0"
                  className="h-8 w-full rounded-md border border-border bg-secondary px-3 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
                  aria-label="Minimum confidence"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground">Max confidence (%)</label>
                <input
                  type="number"
                  min={0}
                  max={100}
                  step={1}
                  value={maxConf}
                  onChange={(e) => { setMaxConf(e.target.value); handleFilterChange(); }}
                  placeholder="100"
                  className="h-8 w-full rounded-md border border-border bg-secondary px-3 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
                  aria-label="Maximum confidence"
                />
              </div>

              {/* Date range */}
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground">From date</label>
                <input
                  type="datetime-local"
                  value={startDate}
                  onChange={(e) => { setStartDate(e.target.value ? new Date(e.target.value).toISOString() : ''); handleFilterChange(); }}
                  className="h-8 w-full rounded-md border border-border bg-secondary px-3 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
                  aria-label="Start date"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground">To date</label>
                <input
                  type="datetime-local"
                  value={endDate}
                  onChange={(e) => { setEndDate(e.target.value ? new Date(e.target.value).toISOString() : ''); handleFilterChange(); }}
                  className="h-8 w-full rounded-md border border-border bg-secondary px-3 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
                  aria-label="End date"
                />
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Table */}
      {isError ? (
        <ErrorState
          title="Failed to load history"
          message={errorMsg}
          onRetry={() => window.location.reload()}
        />
      ) : (
        <Card padding="none">
          {!isLoading && items.length === 0 ? (
            <EmptyState
              icon={<Microscope className="h-6 w-6" />}
              title={hasActiveFilters ? 'No results match your filters' : 'No predictions yet'}
              description={
                hasActiveFilters
                  ? 'Try adjusting or clearing the active filters.'
                  : 'Run your first prediction to see it here.'
              }
              action={
                hasActiveFilters
                  ? { label: 'Clear filters', onClick: clearFilters }
                  : undefined
              }
            />
          ) : (
            <Table aria-label="Prediction history" aria-busy={isLoading}>
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
                {isLoading ? (
                  <SkeletonTableRows />
                ) : (
                  items.map((item) => (
                    <TableRow
                      key={item.history_id}
                      className="cursor-pointer"
                      onClick={() => navigate(`/dashboard/history/${item.history_id}`)}
                      role="link"
                      tabIndex={0}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          navigate(`/dashboard/history/${item.history_id}`);
                        }
                      }}
                      aria-label={`View prediction ${item.history_id.slice(0, 8)}`}
                    >
                      <TableCell className="font-mono text-[11px] text-muted-foreground">
                        {item.history_id.slice(0, 8)}…
                      </TableCell>
                      <TableCell className="font-medium text-xs max-w-[180px] truncate">
                        {item.image_filename}
                      </TableCell>
                      <TableCell className="text-xs">
                        {item.predicted_class ?? <span className="text-muted-foreground/50">—</span>}
                      </TableCell>
                      <TableCell>
                        {item.predicted_class ? (
                          <Badge
                            variant={
                              item.confidence >= 80 ? 'success' :
                              item.confidence >= 60 ? 'warning' : 'destructive'
                            }
                            className="font-mono text-[10px]"
                          >
                            {item.confidence.toFixed(1)}%
                          </Badge>
                        ) : (
                          <span className="text-muted-foreground/50 text-xs">—</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={statusBadgeVariant(item.status)}
                          dot
                          className="text-[10px] capitalize"
                        >
                          {statusLabel(item.status)}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-[11px] text-muted-foreground whitespace-nowrap">
                        {formatDateTime(item.created_at)}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          )}
        </Card>
      )}

      {/* Pagination */}
      {!isError && totalPages > 1 && (
        <div className="flex items-center justify-between gap-4">
          <p className="text-xs text-muted-foreground">
            Page {page} of {totalPages} — {totalRecords} total
          </p>
          <Pagination
            page={page}
            totalPages={totalPages}
            onPageChange={goToPage}
          />
        </div>
      )}
    </div>
  );
}
