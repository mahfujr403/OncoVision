import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Microscope, Filter, X, ArrowRight, Eye, ChevronRight } from 'lucide-react';
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

const STATUS_OPTIONS: { value: PredictionHistoryStatus; label: string }[] = [
  { value: 'success', label: 'Completed' },
  { value: 'partial_success', label: 'Partial Success' },
  { value: 'failed', label: 'Failed' },
  { value: 'pending', label: 'In Flight' },
];

export default function HistoryPage() {
  const navigate = useNavigate();
  const { page, pageSize, goToPage } = usePagination();
  const [statusFilter, setStatusFilter] = useState<PredictionHistoryStatus | ''>('');
  const [classFilter, setClassFilter] = useState('');
  const [filtersOpen, setFiltersOpen] = useState(false);
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
  const totalRecords = data?.pagination.total_records ?? 0;

  return (
    <div className="space-y-5">
      {/* ── Page Header ── */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-border pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl md:text-2xl font-bold tracking-tight font-display text-text-primary">
              Prediction Case Archive
            </h1>
            <Badge variant="outline" className="font-mono text-[11px] text-text-muted">
              {isLoading ? 'Counting…' : `${totalRecords} cases`}
            </Badge>
          </div>
          <p className="text-xs md:text-sm text-text-muted mt-0.5">
            Archival record of computational pathology evaluations, ensemble consensus, and diagnostic findings.
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <Button
            variant={hasActiveFilters ? 'primary' : 'outline'}
            size="sm"
            onClick={() => setFiltersOpen((v) => !v)}
            className="gap-1.5"
            aria-expanded={filtersOpen}
            aria-label="Toggle case retrieval filters"
          >
            <Filter className="h-3.5 w-3.5" />
            Filters
            {hasActiveFilters && (
              <span className="ml-1 rounded-full bg-surface px-1.5 py-0 text-[10px] font-bold text-text-primary">
                {(statusFilter ? 1 : 0) + (classFilter ? 1 : 0)}
              </span>
            )}
          </Button>

          <Button asChild size="sm" variant="primary" className="gap-1.5 shadow-xs">
            <Link to={ROUTES.PREDICT}>
              <Microscope className="h-4 w-4" />
              New Prediction
            </Link>
          </Button>
        </div>
      </div>

      {/* ── Case Retrieval Toolbar ── */}
      <div className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <SearchBox
            value={pageQuery}
            onChange={setPageQuery}
            placeholder="Search visible cases by filename or finding…"
            className="max-w-md w-full"
            aria-label="Search cases"
          />

          {data && (
            <p className="text-xs font-mono text-text-muted hidden sm:block">
              Page {page} of {data.pagination.total_pages || 1}
            </p>
          )}
        </div>

        {/* Expandable Filter Tray */}
        {filtersOpen && (
          <Card className="p-4 border border-border bg-surface-raised/40">
            <div className="flex flex-wrap items-end gap-4">
              <FilterField label="Operational Status">
                <select
                  value={statusFilter}
                  onChange={(e) => {
                    setStatusFilter(e.target.value as PredictionHistoryStatus | '');
                    goToPage(1);
                  }}
                  aria-label="Filter by operational status"
                  className="h-9 rounded-md border border-border bg-surface px-3 text-xs text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                >
                  <option value="">All Pipeline States</option>
                  {STATUS_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </FilterField>

              <FilterField label="Histopathological Class">
                <select
                  value={classFilter}
                  onChange={(e) => {
                    setClassFilter(e.target.value);
                    goToPage(1);
                  }}
                  aria-label="Filter by histopathological class"
                  className="h-9 rounded-md border border-border bg-surface px-3 text-xs text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                >
                  <option value="">All Tissue Classes</option>
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
                  className="gap-1.5 text-text-muted hover:text-text-primary"
                >
                  <X className="h-3.5 w-3.5" />
                  Reset Filters
                </Button>
              )}
            </div>
          </Card>
        )}

        {/* Active Filter Badges */}
        {hasActiveFilters && (
          <div className="flex flex-wrap items-center gap-2 pt-0.5">
            <span className="text-[11px] font-mono uppercase tracking-wider text-text-muted">
              Active Criteria:
            </span>
            {statusFilter && (
              <Badge variant="secondary" className="gap-1 text-xs">
                Status: {statusFilter.replace('_', ' ')}
                <button
                  onClick={() => setStatusFilter('')}
                  aria-label="Remove status filter"
                  className="hover:text-text-primary"
                >
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            )}
            {classFilter && (
              <Badge variant={getDiseaseBadgeVariant(classFilter)} className="gap-1 text-xs">
                Class: {classFilter}
                <button
                  onClick={() => setClassFilter('')}
                  aria-label="Remove class filter"
                  className="hover:text-text-primary"
                >
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            )}
          </div>
        )}
      </div>

      {/* ── Case Archive Listing ── */}
      <Card padding="none" className="overflow-hidden border border-border bg-surface">
        {isError ? (
          <div className="p-6">
            <ErrorState
              title="Unable to load case archive"
              message="The computational pathology history could not be retrieved from the server."
              onRetry={() => refetch()}
            />
          </div>
        ) : isLoading ? (
          <div className="divide-y divide-border-subtle p-2">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="flex items-center gap-4 px-4 py-3.5">
                <Skeleton className="h-4 w-20" />
                <Skeleton className="h-4 w-36" />
                <Skeleton className="h-5 w-24 rounded-full" />
                <Skeleton className="h-4 w-16" />
                <Skeleton className="h-5 w-20 rounded-full" />
                <Skeleton className="h-4 w-24 ml-auto" />
              </div>
            ))}
          </div>
        ) : visibleItems.length === 0 ? (
          <div className="p-8">
            <EmptyState
              icon={<Microscope className="h-8 w-8 text-text-muted" />}
              title="No pathology evaluations found"
              description={
                pageQuery || hasActiveFilters
                  ? 'No records match your active search or filter criteria. Try broadening your query.'
                  : 'Start your first analysis by uploading a histopathology slide image.'
              }
              action={
                hasActiveFilters
                  ? {
                      label: 'Clear Filters',
                      onClick: () => {
                        setStatusFilter('');
                        setClassFilter('');
                        setPageQuery('');
                      },
                    }
                  : {
                      label: 'New Prediction',
                      onClick: () => navigate(ROUTES.PREDICT),
                    }
              }
            />
          </div>
        ) : (
          <>
            {/* Desktop Table View (md and up) */}
            <div className="hidden md:block overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Case ID</TableHead>
                    <TableHead>Specimen Slide</TableHead>
                    <TableHead>Histopathological Finding</TableHead>
                    <TableHead className="text-right">Confidence</TableHead>
                    <TableHead className="text-right">Agreement</TableHead>
                    <TableHead>Pipeline Status</TableHead>
                    <TableHead>Evaluated</TableHead>
                    <TableHead className="text-right">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {visibleItems.map((h) => (
                    <HistoryTableRow key={h.history_id} item={h} />
                  ))}
                </TableBody>
              </Table>
            </div>

            {/* Mobile Card View (< md) */}
            <div className="md:hidden divide-y divide-border-subtle" role="list">
              {visibleItems.map((h) => (
                <HistoryMobileCard key={h.history_id} item={h} />
              ))}
            </div>
          </>
        )}
      </Card>

      {/* ── Pagination ── */}
      {data && data.pagination.total_pages > 1 && (
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pt-2">
          <p className="text-xs font-mono text-text-muted">
            Showing {(page - 1) * pageSize + 1}–{Math.min(page * pageSize, totalRecords)} of {totalRecords} cases
          </p>
          <Pagination page={page} totalPages={data.pagination.total_pages} onPageChange={goToPage} />
        </div>
      )}
    </div>
  );
}

function HistoryTableRow({ item }: { item: PredictionHistoryItem }) {
  const navigate = useNavigate();
  const diseaseVariant = getDiseaseBadgeVariant(item.predicted_class);
  const statusVariant = getStatusBadgeVariant(item.status);
  const displayClass = formatClassLabel(item.predicted_class);
  const agreementDisplay =
    item.agreement_ratio != null && !Number.isNaN(item.agreement_ratio)
      ? `${Math.round(item.agreement_ratio * 100)}%`
      : '—';

  return (
    <TableRow
      className="cursor-pointer hover:bg-surface-raised/60 transition-colors group"
      onClick={() => navigate(`${ROUTES.HISTORY}/${item.history_id}`)}
    >
      <TableCell className="font-mono text-xs text-text-muted">
        Case #{item.history_id.slice(0, 8)}
      </TableCell>

      <TableCell className="font-medium text-xs text-text-primary max-w-[180px] truncate">
        {item.image_filename}
      </TableCell>

      <TableCell>
        <Badge variant={diseaseVariant} className="text-[11px] font-semibold">
          {displayClass}
        </Badge>
      </TableCell>

      <TableCell className="font-mono tabular-nums font-semibold text-xs text-text-primary text-right">
        {item.confidence}%
      </TableCell>

      <TableCell className="font-mono tabular-nums text-xs text-text-secondary text-right">
        {agreementDisplay}
      </TableCell>

      <TableCell>
        <Badge variant={statusVariant} dot className="text-[10px] capitalize">
          {item.status.replace('_', ' ')}
        </Badge>
      </TableCell>

      <TableCell className="font-mono text-[11px] text-text-muted">
        {formatDateTime(item.created_at)}
      </TableCell>

      <TableCell className="text-right">
        <Button
          variant="ghost"
          size="xs"
          className="text-text-muted group-hover:text-primary gap-1"
          onClick={(e) => {
            e.stopPropagation();
            navigate(`${ROUTES.HISTORY}/${item.history_id}`);
          }}
          aria-label={`View case ${item.history_id.slice(0, 8)}`}
        >
          <Eye className="h-3.5 w-3.5" />
          <ArrowRight className="h-3 w-3" />
        </Button>
      </TableCell>
    </TableRow>
  );
}

function HistoryMobileCard({ item }: { item: PredictionHistoryItem }) {
  const navigate = useNavigate();
  const diseaseVariant = getDiseaseBadgeVariant(item.predicted_class);
  const statusVariant = getStatusBadgeVariant(item.status);
  const displayClass = formatClassLabel(item.predicted_class);
  const agreementDisplay =
    item.agreement_ratio != null && !Number.isNaN(item.agreement_ratio)
      ? `${Math.round(item.agreement_ratio * 100)}%`
      : '—';

  return (
    <div
      onClick={() => navigate(`${ROUTES.HISTORY}/${item.history_id}`)}
      className="p-4 space-y-2.5 cursor-pointer hover:bg-surface-raised/40 transition-colors"
      role="listitem"
    >
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-xs font-semibold text-text-muted">
          Case #{item.history_id.slice(0, 8)}
        </span>
        <Badge variant={statusVariant} dot className="text-[10px] capitalize">
          {item.status.replace('_', ' ')}
        </Badge>
      </div>

      <p className="text-xs font-semibold text-text-primary truncate">
        {item.image_filename}
      </p>

      <div className="flex items-center justify-between gap-2 pt-0.5">
        <Badge variant={diseaseVariant} className="text-[10px] font-semibold">
          {displayClass}
        </Badge>

        <div className="flex items-center gap-3 text-xs font-mono tabular-nums">
          <span className="font-semibold text-text-primary">{item.confidence}% conf</span>
          <span className="text-text-muted">({agreementDisplay} agr)</span>
        </div>
      </div>

      <div className="flex items-center justify-between text-[11px] text-text-muted pt-1 border-t border-border-subtle">
        <span>{formatDateTime(item.created_at)}</span>
        <span className="inline-flex items-center gap-1 text-primary font-medium">
          Review Case <ChevronRight className="h-3 w-3" />
        </span>
      </div>
    </div>
  );
}

function FilterField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-xs font-semibold text-text-muted uppercase tracking-wider">{label}</span>
      {children}
    </div>
  );
}
