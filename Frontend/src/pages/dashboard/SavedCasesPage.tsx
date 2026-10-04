import { useState, useMemo } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Bookmark,
  Microscope,
  Star,
  Trash2,
  GitCompare,
  FileText,
  SlidersHorizontal,
  Info,
  Layers,
  Activity,
  LayoutGrid,
  List,
  RotateCcw,
} from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { EmptyState } from '@/components/ui/EmptyState';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { SearchBox } from '@/components/ui/SearchBox';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import { DemoDataBanner } from '@/components/ui/DemoDataBanner';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/Table';
import { useClinicalCases, type ClinicalCase } from '@/hooks/useClinicalCases';
import { formatDate, formatPercent } from '@/utils/formatters';
import { CANCER_TYPE_LABELS } from '@/constants/app';
import { ROUTES } from '@/constants/routes';
import { cn } from '@/lib/utils';

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

function normalizeDiseaseLabel(label: string | null | undefined): string {
  if (!label) return 'Unclassified';
  return CANCER_TYPE_LABELS[label] || label;
}

function getStatusBadgeVariant(
  status: string,
): 'success' | 'warning' | 'info' | 'secondary' {
  switch (status) {
    case 'Verified':
      return 'success';
    case 'Flagged for Review':
      return 'warning';
    case 'Completed':
      return 'info';
    default:
      return 'secondary';
  }
}

export default function SavedCasesPage() {
  const navigate = useNavigate();
  const { cases, toggleFavorite, removeCase, resetToDefaults } = useClinicalCases();

  // Search & filter states
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [viewMode, setViewMode] = useState<'cards' | 'table'>('cards');

  // Removal confirmation dialog state
  const [pendingDeleteCase, setPendingDeleteCase] = useState<ClinicalCase | null>(null);

  // Filtered cases calculation
  const filteredCases = useMemo(() => {
    return cases.filter((c) => {
      // Search matching
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase();
        const matchesImage = c.image.toLowerCase().includes(query);
        const matchesId = c.id.toLowerCase().includes(query);
        const matchesLabel = normalizeDiseaseLabel(c.label).toLowerCase().includes(query);
        const matchesNote = c.note ? c.note.toLowerCase().includes(query) : false;
        if (!matchesImage && !matchesId && !matchesLabel && !matchesNote) {
          return false;
        }
      }

      // Category matching
      if (categoryFilter !== 'all' && c.label !== categoryFilter) {
        return false;
      }

      // Status matching
      if (statusFilter !== 'all' && c.status !== statusFilter) {
        return false;
      }

      return true;
    });
  }, [cases, searchQuery, categoryFilter, statusFilter]);

  const handleConfirmDelete = () => {
    if (pendingDeleteCase) {
      removeCase(pendingDeleteCase.id);
      setPendingDeleteCase(null);
    }
  };

  const handleClearFilters = () => {
    setSearchQuery('');
    setCategoryFilter('all');
    setStatusFilter('all');
  };

  return (
    <div className="space-y-6">
      {/* Calm Scientific Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-xl font-semibold tracking-tight text-text-primary sm:text-2xl">
              Saved Clinical Cases
            </h1>
            <Badge variant="outline" className="font-mono text-[11px] tabular-nums">
              {cases.length} {cases.length === 1 ? 'case' : 'cases'}
            </Badge>
          </div>
          <p className="mt-1 text-sm text-text-muted">
            Cases retained for review, comparison, and longitudinal reference.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button variant="outline" size="sm" asChild>
            <Link to={ROUTES.HISTORY} className="gap-1.5">
              <FileText className="h-3.5 w-3.5" />
              <span>Browse History</span>
            </Link>
          </Button>
          <Button size="sm" asChild>
            <Link to={ROUTES.PREDICT} className="gap-1.5">
              <Microscope className="h-3.5 w-3.5" />
              <span>New Analysis</span>
            </Link>
          </Button>
        </div>
      </div>

      {/* Truthful Data & Workflow Banner */}
      <DemoDataBanner feature="saved cases" />

      {/* Investigational Disclaimer */}
      <div
        role="region"
        aria-label="Clinical Decision Support Disclaimer"
        className="flex items-start gap-3 rounded-lg border border-border-subtle bg-surface-raised/60 p-3.5 text-xs text-text-secondary"
      >
        <Info className="mt-0.5 h-4 w-4 shrink-0 text-text-muted" aria-hidden="true" />
        <div className="space-y-0.5 leading-relaxed">
          <span className="font-semibold text-text-primary">Clinical Decision Support Context: </span>
          Retained cases represent archived AI evaluations for multidisciplinary review and comparative inquiry. Model
          outputs are intended for investigational decision support and must be confirmed by a board-certified pathologist.
        </div>
      </div>

      {/* Search, Filter & Layout Control Bar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border-b border-border pb-4">
        <div className="flex flex-1 flex-col gap-2.5 sm:flex-row sm:items-center">
          <SearchBox
            value={searchQuery}
            onChange={setSearchQuery}
            placeholder="Search by specimen, ID, finding, or note..."
            className="w-full sm:max-w-xs"
          />

          <div className="flex flex-wrap items-center gap-2">
            <select
              aria-label="Filter by histopathology finding"
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="rounded-md border border-border bg-surface px-2.5 py-1.5 text-xs text-text-primary focus-visible:outline-hidden focus-visible:ring-1 focus-visible:ring-primary"
            >
              <option value="all">All Findings</option>
              <option value="lung_aca">Lung Adenocarcinoma</option>
              <option value="lung_scc">Lung Squamous Cell Carcinoma</option>
              <option value="colon_aca">Colon Adenocarcinoma</option>
              <option value="lung_benign">Lung Benign</option>
              <option value="colon_benign">Colon Benign</option>
            </select>

            <select
              aria-label="Filter by review status"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="rounded-md border border-border bg-surface px-2.5 py-1.5 text-xs text-text-primary focus-visible:outline-hidden focus-visible:ring-1 focus-visible:ring-primary"
            >
              <option value="all">All Statuses</option>
              <option value="Completed">Completed</option>
              <option value="Verified">Verified</option>
              <option value="Flagged for Review">Flagged for Review</option>
            </select>

            {(searchQuery || categoryFilter !== 'all' || statusFilter !== 'all') && (
              <Button variant="ghost" size="sm" onClick={handleClearFilters} className="text-xs text-text-muted hover:text-text-primary h-8 px-2">
                Clear filters
              </Button>
            )}
          </div>
        </div>

        {/* View mode toggle (Cards vs Table) */}
        <div className="flex items-center gap-1 rounded-md border border-border bg-surface p-1 self-start sm:self-auto">
          <button
            type="button"
            onClick={() => setViewMode('cards')}
            aria-label="Card grid view"
            aria-pressed={viewMode === 'cards'}
            className={cn(
              'rounded p-1 text-text-muted transition-colors focus-visible:outline-hidden focus-visible:ring-1 focus-visible:ring-primary',
              viewMode === 'cards' && 'bg-surface-raised text-text-primary',
            )}
          >
            <LayoutGrid className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={() => setViewMode('table')}
            aria-label="Structured table view"
            aria-pressed={viewMode === 'table'}
            className={cn(
              'rounded p-1 text-text-muted transition-colors focus-visible:outline-hidden focus-visible:ring-1 focus-visible:ring-primary',
              viewMode === 'table' && 'bg-surface-raised text-text-primary',
            )}
          >
            <List className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      {cases.length === 0 ? (
        <Card className="py-12">
          <EmptyState
            icon={<Bookmark className="h-8 w-8 text-text-muted" />}
            title="No saved clinical cases"
            description="Save any histopathology prediction from history or analysis for follow-up review and comparison."
            action={{
              label: 'Start New Prediction',
              onClick: () => navigate(ROUTES.PREDICT),
            }}
          />
          <div className="mt-4 flex justify-center">
            <Button variant="outline" size="sm" onClick={resetToDefaults} className="gap-1.5 text-xs">
              <RotateCcw className="h-3.5 w-3.5" />
              <span>Restore Sample Cases</span>
            </Button>
          </div>
        </Card>
      ) : filteredCases.length === 0 ? (
        <Card className="py-10">
          <EmptyState
            icon={<SlidersHorizontal className="h-6 w-6 text-text-muted" />}
            title="No matching clinical cases"
            description="No saved cases match your active search and filter criteria."
            action={{
              label: 'Clear Filters',
              onClick: handleClearFilters,
            }}
          />
        </Card>
      ) : viewMode === 'cards' ? (
        /* ==================== CARD GRID VIEW ==================== */
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filteredCases.map((c) => (
            <Card
              key={c.id}
              className="flex flex-col justify-between p-4 space-y-4 hover:border-primary/30 transition-colors"
            >
              {/* Card Header: Specimen & Favorite Action */}
              <div className="space-y-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2.5 min-w-0">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-surface-raised text-primary">
                      <Microscope className="h-4 w-4" />
                    </div>
                    <div className="min-w-0">
                      <h2 className="text-xs font-semibold text-text-primary font-mono truncate" title={c.image}>
                        {c.image}
                      </h2>
                      <div className="flex items-center gap-2 text-[10px] text-text-muted">
                        <span className="font-mono">ID: {c.id}</span>
                        <span>•</span>
                        <span>{formatDate(c.savedAt)}</span>
                      </div>
                    </div>
                  </div>

                  {/* Favorite Toggle Button */}
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleFavorite(c.id);
                    }}
                    aria-label={c.isFavorite ? 'Remove from favorites' : 'Add to favorites'}
                    className="p-1 rounded-md text-text-muted hover:text-text-primary transition-colors focus-visible:outline-hidden focus-visible:ring-1 focus-visible:ring-primary"
                  >
                    <Star
                      className={cn(
                        'h-4 w-4 transition-colors',
                        c.isFavorite ? 'fill-warning text-warning' : 'text-text-muted hover:text-text-primary',
                      )}
                    />
                  </button>
                </div>

                {/* Primary Histopathological Finding */}
                <div className="space-y-1.5 rounded-md border border-border-subtle bg-surface-raised/40 p-2.5">
                  <div className="text-[11px] text-text-muted">Histopathological Finding</div>
                  <div className="flex items-center justify-between gap-1.5">
                    <Badge variant={getDiseaseBadgeVariant(c.label)} dot>
                      {normalizeDiseaseLabel(c.label)}
                    </Badge>
                    <Badge variant={getStatusBadgeVariant(c.status)} className="text-[10px]">
                      {c.status}
                    </Badge>
                  </div>
                </div>

                {/* Quantitative Supporting Evidence */}
                <div className="grid grid-cols-2 gap-2 text-xs border-b border-border-subtle pb-3">
                  <div className="space-y-0.5">
                    <div className="flex items-center gap-1 text-[11px] text-text-muted">
                      <Activity className="h-3 w-3 text-text-muted" />
                      <span>Model Confidence</span>
                    </div>
                    <div className="font-mono font-semibold tabular-nums text-text-primary">
                      {formatPercent(c.confidence)}
                    </div>
                  </div>

                  <div className="space-y-0.5">
                    <div className="flex items-center gap-1 text-[11px] text-text-muted">
                      <Layers className="h-3 w-3 text-text-muted" />
                      <span>Model Agreement</span>
                    </div>
                    <div className="font-mono font-semibold tabular-nums text-text-primary">
                      {c.agreementRatio !== undefined ? formatPercent(c.agreementRatio) : '—'}
                    </div>
                  </div>
                </div>

                {/* Clinical Review Note */}
                {c.note && (
                  <p className="text-xs text-text-secondary leading-relaxed bg-surface-raised/20 rounded p-2 border border-border-subtle">
                    {c.note}
                  </p>
                )}
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-between gap-2 border-t border-border-subtle pt-3">
                <div className="flex items-center gap-1.5">
                  <Button variant="outline" size="sm" asChild className="h-7 text-xs px-2.5">
                    <Link to={`${ROUTES.HISTORY}/${c.id}`}>View Details</Link>
                  </Button>
                  <Button variant="ghost" size="sm" asChild className="h-7 text-xs px-2 text-text-muted hover:text-text-primary" title="Compare in Model Comparison">
                    <Link to={`${ROUTES.COMPARISON}?caseId=${c.id}`}>
                      <GitCompare className="h-3.5 w-3.5" />
                      <span className="sr-only">Compare case {c.id}</span>
                    </Link>
                  </Button>
                </div>

                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setPendingDeleteCase(c)}
                  aria-label={`Remove case ${c.image} from saved cases`}
                  className="h-7 px-2 text-text-muted hover:text-error hover:bg-error-surface transition-colors"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </div>
            </Card>
          ))}
        </div>
      ) : (
        /* ==================== STRUCTURED TABLE VIEW ==================== */
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead scope="col">Specimen / Case ID</TableHead>
              <TableHead scope="col">Histopathological Finding</TableHead>
              <TableHead scope="col" className="text-right">Confidence</TableHead>
              <TableHead scope="col" className="text-right">Model Agreement</TableHead>
              <TableHead scope="col">Review Status</TableHead>
              <TableHead scope="col">Retained Date</TableHead>
              <TableHead scope="col" className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredCases.map((c) => (
              <TableRow key={c.id}>
                <TableCell className="font-mono text-xs">
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => toggleFavorite(c.id)}
                      aria-label={c.isFavorite ? 'Remove from favorites' : 'Add to favorites'}
                      className="text-text-muted hover:text-text-primary transition-colors"
                    >
                      <Star
                        className={cn(
                          'h-3.5 w-3.5',
                          c.isFavorite ? 'fill-warning text-warning' : 'text-text-muted',
                        )}
                      />
                    </button>
                    <div>
                      <div className="font-medium text-text-primary truncate max-w-[180px]" title={c.image}>
                        {c.image}
                      </div>
                      <div className="text-[10px] text-text-muted">ID: {c.id}</div>
                    </div>
                  </div>
                </TableCell>
                <TableCell>
                  <Badge variant={getDiseaseBadgeVariant(c.label)} dot>
                    {normalizeDiseaseLabel(c.label)}
                  </Badge>
                </TableCell>
                <TableCell className="text-right font-mono font-medium tabular-nums text-text-primary">
                  {formatPercent(c.confidence)}
                </TableCell>
                <TableCell className="text-right font-mono tabular-nums text-text-secondary">
                  {c.agreementRatio !== undefined ? formatPercent(c.agreementRatio) : '—'}
                </TableCell>
                <TableCell>
                  <Badge variant={getStatusBadgeVariant(c.status)} className="text-[10px]">
                    {c.status}
                  </Badge>
                </TableCell>
                <TableCell className="text-xs text-text-muted">
                  {formatDate(c.savedAt)}
                </TableCell>
                <TableCell className="text-right">
                  <div className="flex items-center justify-end gap-1">
                    <Button variant="outline" size="sm" asChild className="h-7 text-xs px-2">
                      <Link to={`${ROUTES.HISTORY}/${c.id}`}>Details</Link>
                    </Button>
                    <Button variant="ghost" size="sm" asChild className="h-7 text-xs px-2 text-text-muted hover:text-text-primary">
                      <Link to={`${ROUTES.COMPARISON}?caseId=${c.id}`} title="Compare in Model Comparison">
                        <GitCompare className="h-3.5 w-3.5" />
                        <span className="sr-only">Compare case {c.id}</span>
                      </Link>
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setPendingDeleteCase(c)}
                      aria-label={`Remove case ${c.image}`}
                      className="h-7 px-2 text-text-muted hover:text-error hover:bg-error-surface transition-colors"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      {/* Case Removal Confirmation Dialog */}
      <ConfirmDialog
        open={Boolean(pendingDeleteCase)}
        onClose={() => setPendingDeleteCase(null)}
        onConfirm={handleConfirmDelete}
        title="Remove Saved Case"
        description={
          pendingDeleteCase
            ? `Are you sure you want to remove ${pendingDeleteCase.image} (ID: ${pendingDeleteCase.id}) from your saved cases? You can re-pin it from prediction history anytime.`
            : undefined
        }
        confirmLabel="Remove Case"
        cancelLabel="Cancel"
        destructive
      />
    </div>
  );
}
