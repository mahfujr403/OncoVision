import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Microscope, Filter, X, ChevronRight, Eye } from 'lucide-react';
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
import { useAdminHistory } from '@/hooks/queries/useAdminHistory';
import { useAdminUsers } from '@/hooks/queries/useAdminUsers';
import { usePagination } from '@/hooks/usePagination';
import { formatDateTime } from '@/utils/formatters';
import { KNOWN_CLASS_LABELS } from '@/constants/app';
import { ROUTES } from '@/constants/routes';
import type { PredictionHistoryStatus } from '@/types';

const STATUS_OPTIONS: { value: PredictionHistoryStatus; label: string }[] = [
  { value: 'success', label: 'Completed' },
  { value: 'partial_success', label: 'Partial Success' },
  { value: 'failed', label: 'Failed' },
  { value: 'pending', label: 'Pending' },
];

function getDiseaseBadgeVariant(
  label: string | null | undefined,
): 'lungAca' | 'lungScc' | 'colonAca' | 'lungBenign' | 'colonBenign' | 'secondary' {
  if (!label) return 'secondary';
  const norm = label.toLowerCase();
  if (norm.includes('lung') && (norm.includes('adeno') || norm.includes('aca'))) return 'lungAca';
  if (norm.includes('lung') && (norm.includes('squamous') || norm.includes('scc'))) return 'lungScc';
  if (norm.includes('colon') && (norm.includes('adeno') || norm.includes('aca'))) return 'colonAca';
  if (norm.includes('lung') && norm.includes('benign')) return 'lungBenign';
  if (norm.includes('colon') && norm.includes('benign')) return 'colonBenign';
  return 'secondary';
}

function formatClassLabel(raw: string | null | undefined): string {
  if (!raw) return 'Pending Analysis';
  return raw
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

function getStatusBadgeVariant(status: PredictionHistoryStatus): 'success' | 'warning' | 'error' | 'secondary' {
  if (status === 'success') return 'success';
  if (status === 'partial_success') return 'warning';
  if (status === 'failed') return 'error';
  return 'secondary';
}

export default function AdminHistoryPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { page, pageSize, goToPage } = usePagination();

  const userIdFilter = searchParams.get('user_id') ?? '';
  const [statusFilter, setStatusFilter] = useState<PredictionHistoryStatus | ''>('');
  const [classFilter, setClassFilter] = useState('');
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [pageQuery, setPageQuery] = useState('');

  // Fetch users list for populating email names in the user selector
  const { data: usersData } = useAdminUsers({ page: 1, page_size: 100 });
  const usersById = new Map((usersData?.items ?? []).map((u) => [u.id, u]));

  const { data, isLoading, isError, refetch } = useAdminHistory({
    page,
    page_size: pageSize,
    user_id: userIdFilter || undefined,
    status: statusFilter || undefined,
    predicted_class: classFilter || undefined,
  });

  const items = data?.items ?? [];
  const visibleItems = pageQuery
    ? items.filter(
        (h) =>
          h.image_filename.toLowerCase().includes(pageQuery.toLowerCase()) ||
          (h.predicted_class ?? '').toLowerCase().includes(pageQuery.toLowerCase()) ||
          h.user_email.toLowerCase().includes(pageQuery.toLowerCase()) ||
          h.history_id.toLowerCase().includes(pageQuery.toLowerCase()),
      )
    : items;

  const hasActiveFilters = Boolean(statusFilter || classFilter || userIdFilter);

  function setUserIdFilter(userId: string) {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (userId) next.set('user_id', userId);
      else next.delete('user_id');
      return next;
    });
    goToPage(1);
  }

  const filteredUser = userIdFilter ? usersById.get(userIdFilter) : undefined;

  return (
    <div className="space-y-6">
      {/* Workspace Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <SectionTitle
          title="Prediction Evaluation Archive"
          description="Administrative record of histopathology inference requests, model findings, and operational pipeline telemetry."
        />
        <div className="flex items-center gap-2">
          {data && (
            <Badge variant="outline" className="font-mono text-xs px-2.5 py-1">
              <Microscope className="h-3.5 w-3.5 mr-1.5 text-primary" />
              <span className="font-semibold text-text-primary tabular-nums">{data.pagination.total_records}</span>
              <span className="ml-1 text-text-muted">Total Evaluations</span>
            </Badge>
          )}
          <Button
            variant={filtersOpen ? 'secondary' : 'outline'}
            size="sm"
            onClick={() => setFiltersOpen((v) => !v)}
            className="gap-1.5"
            aria-expanded={filtersOpen}
            aria-label="Toggle query filters"
          >
            <Filter className="h-3.5 w-3.5" />
            <span>Filters</span>
            {hasActiveFilters && (
              <span className="inline-flex h-2 w-2 rounded-full bg-primary" />
            )}
          </Button>
        </div>
      </div>

      {/* Active Filter Indicators */}
      {userIdFilter && (
        <div className="flex items-center gap-2 p-2.5 rounded-lg border border-border bg-surface-raised text-xs text-text-secondary">
          <span className="text-text-muted">Filtered by Account:</span>
          <Badge variant="secondary" className="font-mono text-xs">
            {filteredUser ? `${filteredUser.full_name} (${filteredUser.email})` : userIdFilter}
          </Badge>
          <Button
            variant="ghost"
            size="xs"
            onClick={() => setUserIdFilter('')}
            className="h-6 px-1.5 gap-1 text-text-muted hover:text-text-primary"
            aria-label="Clear user filter"
          >
            <X className="h-3 w-3" />
            <span>Clear filter</span>
          </Button>
        </div>
      )}

      {/* Collapsible Filter Panel */}
      {filtersOpen && (
        <Card className="p-4 bg-surface-raised/40 border-border">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 items-end">
            <div className="space-y-1.5">
              <label htmlFor="user-filter-select" className="text-xs font-medium text-text-muted">
                User Account
              </label>
              <select
                id="user-filter-select"
                value={userIdFilter}
                onChange={(e) => setUserIdFilter(e.target.value)}
                className="w-full h-9 rounded-md border border-border bg-surface px-3 text-xs text-text-primary focus:outline-none focus:ring-1 focus:ring-primary"
              >
                <option value="">All Platform Accounts</option>
                {(usersData?.items ?? []).map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.full_name} ({u.email})
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-1.5">
              <label htmlFor="status-filter-select" className="text-xs font-medium text-text-muted">
                Pipeline Status
              </label>
              <select
                id="status-filter-select"
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value as PredictionHistoryStatus | '');
                  goToPage(1);
                }}
                className="w-full h-9 rounded-md border border-border bg-surface px-3 text-xs text-text-primary focus:outline-none focus:ring-1 focus:ring-primary"
              >
                <option value="">Any Pipeline Status</option>
                {STATUS_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-1.5">
              <label htmlFor="class-filter-select" className="text-xs font-medium text-text-muted">
                Histopathological Finding
              </label>
              <select
                id="class-filter-select"
                value={classFilter}
                onChange={(e) => {
                  setClassFilter(e.target.value);
                  goToPage(1);
                }}
                className="w-full h-9 rounded-md border border-border bg-surface px-3 text-xs text-text-primary focus:outline-none focus:ring-1 focus:ring-primary"
              >
                <option value="">Any Classification</option>
                {KNOWN_CLASS_LABELS.map((label) => (
                  <option key={label} value={label}>
                    {label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {hasActiveFilters && (
            <div className="mt-4 pt-3 border-t border-border flex justify-end">
              <Button
                variant="ghost"
                size="xs"
                onClick={() => {
                  setStatusFilter('');
                  setClassFilter('');
                  setUserIdFilter('');
                }}
                className="gap-1.5 text-xs text-text-muted hover:text-text-primary"
              >
                <X className="h-3.5 w-3.5" />
                Reset all filters
              </Button>
            </div>
          )}
        </Card>
      )}

      {/* In-Page Quick Filter */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <SearchBox
          value={pageQuery}
          onChange={setPageQuery}
          placeholder="Filter by specimen image, class, user email, or case ID…"
          className="max-w-md w-full"
        />
        {pageQuery && (
          <span className="text-xs text-text-muted font-mono">
            Showing {visibleItems.length} of {items.length} records on page
          </span>
        )}
      </div>

      {/* Main Table / Card Content */}
      <Card padding="none">
        {isError ? (
          <ErrorState message="Could not load platform prediction evaluation archive." onRetry={() => refetch()} />
        ) : isLoading ? (
          <div className="divide-y divide-border p-2">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="flex items-center justify-between gap-4 px-4 py-3.5">
                <div className="flex items-center gap-3">
                  <Skeleton className="h-7 w-16" />
                  <div className="space-y-1">
                    <Skeleton className="h-3.5 w-32" />
                    <Skeleton className="h-3 w-44" />
                  </div>
                </div>
                <div className="hidden sm:flex items-center gap-6">
                  <Skeleton className="h-5 w-28 rounded-full" />
                  <Skeleton className="h-4 w-12" />
                  <Skeleton className="h-4 w-12" />
                  <Skeleton className="h-5 w-20 rounded-full" />
                </div>
                <Skeleton className="h-7 w-16" />
              </div>
            ))}
          </div>
        ) : visibleItems.length === 0 ? (
          <EmptyState
            icon={<Microscope className="h-6 w-6 text-text-muted" />}
            title="No prediction evaluation records found"
            description={
              pageQuery || hasActiveFilters
                ? 'No evaluations match your current query or filter criteria. Try clearing active filters.'
                : 'No diagnostic evaluations have been logged across the platform yet.'
            }
          />
        ) : (
          <>
            {/* Desktop Table */}
            <div className="hidden lg:block">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead scope="col">Case ID</TableHead>
                    <TableHead scope="col">User Account</TableHead>
                    <TableHead scope="col">Specimen Image</TableHead>
                    <TableHead scope="col">Histopathological Finding</TableHead>
                    <TableHead scope="col">Confidence</TableHead>
                    <TableHead scope="col">Agreement</TableHead>
                    <TableHead scope="col">Pipeline Status</TableHead>
                    <TableHead scope="col">Evaluation Date</TableHead>
                    <TableHead scope="col" className="text-right">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {visibleItems.map((item) => {
                    const diseaseVariant = getDiseaseBadgeVariant(item.predicted_class);
                    const statusVariant = getStatusBadgeVariant(item.status);
                    const userEmail = item.user_email || usersById.get(item.user_id)?.email || item.user_id.slice(0, 8);

                    return (
                      <TableRow
                        key={item.history_id}
                        className="cursor-pointer hover:bg-surface-raised/60 transition-colors"
                        onClick={() => navigate(`${ROUTES.ADMIN_HISTORY}/${item.history_id}`)}
                      >
                        <TableCell className="font-mono text-xs text-text-muted">
                          {item.history_id.slice(0, 8)}
                        </TableCell>
                        <TableCell>
                          <button
                            type="button"
                            className="text-xs font-mono text-text-secondary hover:text-primary hover:underline text-left truncate max-w-[160px] block"
                            onClick={(e) => {
                              e.stopPropagation();
                              setUserIdFilter(item.user_id);
                            }}
                            title={`Filter history to ${userEmail}`}
                            aria-label={`Filter archive to user ${userEmail}`}
                          >
                            {userEmail}
                          </button>
                        </TableCell>
                        <TableCell className="text-xs font-medium text-text-primary max-w-[150px] truncate" title={item.image_filename}>
                          {item.image_filename}
                        </TableCell>
                        <TableCell>
                          <Badge variant={diseaseVariant} className="text-xs">
                            {formatClassLabel(item.predicted_class)}
                          </Badge>
                        </TableCell>
                        <TableCell className="font-mono text-xs tabular-nums text-text-primary">
                          {item.status === 'failed' ? (
                            <span className="text-text-muted">—</span>
                          ) : (
                            <span className="font-semibold">{item.confidence}%</span>
                          )}
                        </TableCell>
                        <TableCell className="font-mono text-xs tabular-nums text-text-secondary">
                          {item.status === 'failed' ? (
                            <span className="text-text-muted">—</span>
                          ) : (
                            <span>{Math.round(item.agreement_ratio * 100)}%</span>
                          )}
                        </TableCell>
                        <TableCell>
                          <Badge variant={statusVariant} dot className="text-[10px] capitalize">
                            {item.status.replace('_', ' ')}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-xs font-mono tabular-nums text-text-muted whitespace-nowrap">
                          {formatDateTime(item.created_at)}
                        </TableCell>
                        <TableCell className="text-right">
                          <Button
                            variant="ghost"
                            size="xs"
                            className="gap-1 text-xs"
                            onClick={(e) => {
                              e.stopPropagation();
                              navigate(`${ROUTES.ADMIN_HISTORY}/${item.history_id}`);
                            }}
                            aria-label={`Inspect case evaluation ${item.history_id.slice(0, 8)}`}
                          >
                            <Eye className="h-3.5 w-3.5 text-text-muted" />
                            <span>Inspect</span>
                          </Button>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>

            {/* Mobile / Tablet Responsive Stacked Card View */}
            <div className="divide-y divide-border lg:hidden">
              {visibleItems.map((item) => {
                const diseaseVariant = getDiseaseBadgeVariant(item.predicted_class);
                const statusVariant = getStatusBadgeVariant(item.status);
                const userEmail = item.user_email || usersById.get(item.user_id)?.email || item.user_id.slice(0, 8);

                return (
                  <div
                    key={item.history_id}
                    className="p-4 space-y-3 hover:bg-surface-raised/40 transition-colors cursor-pointer"
                    onClick={() => navigate(`${ROUTES.ADMIN_HISTORY}/${item.history_id}`)}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs text-text-muted">Case #{item.history_id.slice(0, 8)}</span>
                          <Badge variant={statusVariant} dot className="text-[10px] capitalize">
                            {item.status.replace('_', ' ')}
                          </Badge>
                        </div>
                        <p className="text-xs font-semibold text-text-primary mt-1 truncate max-w-[240px]">
                          {item.image_filename}
                        </p>
                      </div>
                      <Badge variant={diseaseVariant} className="text-xs shrink-0">
                        {formatClassLabel(item.predicted_class)}
                      </Badge>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 p-2.5 rounded-md bg-surface-raised/50 border border-border-subtle text-xs font-mono">
                      <div>
                        <span className="text-[10px] text-text-muted uppercase block">Confidence</span>
                        <span className="font-semibold text-text-primary tabular-nums">
                          {item.status === 'failed' ? '—' : `${item.confidence}%`}
                        </span>
                      </div>
                      <div>
                        <span className="text-[10px] text-text-muted uppercase block">Agreement</span>
                        <span className="text-text-secondary tabular-nums">
                          {item.status === 'failed' ? '—' : `${Math.round(item.agreement_ratio * 100)}%`}
                        </span>
                      </div>
                      <div>
                        <span className="text-[10px] text-text-muted uppercase block">Models</span>
                        <span className="text-text-secondary tabular-nums">{item.participating_models}</span>
                      </div>
                      <div>
                        <span className="text-[10px] text-text-muted uppercase block">Evaluated</span>
                        <span className="text-text-muted text-[11px] truncate block">
                          {formatDateTime(item.created_at)}
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center justify-between text-xs pt-1 border-t border-border-subtle">
                      <button
                        type="button"
                        className="font-mono text-[11px] text-text-muted hover:text-primary truncate max-w-[200px]"
                        onClick={(e) => {
                          e.stopPropagation();
                          setUserIdFilter(item.user_id);
                        }}
                      >
                        User: {userEmail}
                      </button>
                      <div className="flex items-center gap-1 text-primary font-medium text-xs">
                        <span>Inspect record</span>
                        <ChevronRight className="h-3.5 w-3.5" />
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </>
        )}
      </Card>

      {/* Pagination Footer */}
      {data && data.pagination.total_pages > 1 && (
        <div className="flex items-center justify-between pt-2">
          <p className="text-xs font-mono text-text-muted">
            Page {page} of {data.pagination.total_pages} ({data.pagination.total_records} total evaluations)
          </p>
          <Pagination page={page} totalPages={data.pagination.total_pages} onPageChange={goToPage} />
        </div>
      )}
    </div>
  );
}
