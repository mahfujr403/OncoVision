import { useEffect, useState } from 'react';
import { History as HistoryIcon } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { HistoryFiltersBar } from '@/components/history/HistoryFiltersBar';
import { HistoryTable } from '@/components/history/HistoryTable';
import { HistoryDetailPanel } from '@/components/history/HistoryDetailPanel';
import { simulateHistoryListRequest, simulateHistoryDetailRequest, availableClassLabels } from '@/lib/mockHistory';
import { DEFAULT_HISTORY_FILTERS, type HistoryFilters, type HistoryRecord, type PaginatedHistoryResponse } from '@/types/history';

export function HistoryPage() {
  const [filters, setFilters] = useState<HistoryFilters>(DEFAULT_HISTORY_FILTERS);
  const [data, setData] = useState<PaginatedHistoryResponse | null>(null);
  const [listLoading, setListLoading] = useState(true);
  const [listError, setListError] = useState<unknown>(null);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detailRecord, setDetailRecord] = useState<HistoryRecord | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState(false);

  async function loadList() {
    setListLoading(true);
    setListError(null);
    try {
      const result = await simulateHistoryListRequest(filters);
      setData(result);
    } catch (err) {
      setListError(err);
    } finally {
      setListLoading(false);
    }
  }

  useEffect(() => {
    loadList();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters]);

  async function loadDetail(historyId: string) {
    setDetailLoading(true);
    setDetailError(false);
    try {
      const record = await simulateHistoryDetailRequest(historyId);
      setDetailRecord(record);
    } catch {
      setDetailError(true);
    } finally {
      setDetailLoading(false);
    }
  }

  function handleSelect(record: HistoryRecord) {
    setSelectedId(record.history_id);
    setDetailRecord(record);
    // Still simulate a real detail fetch rather than trusting only the list row.
    loadDetail(record.history_id);
  }

  return (
    <div className="p-6 max-w-[1100px] mx-auto space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-lg bg-primary/10 flex items-center justify-center text-primary shrink-0">
            <HistoryIcon className="w-4.5 h-4.5" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-foreground">Prediction History</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Browse and filter your past AI-assisted predictions.
            </p>
          </div>
        </div>
        <Badge variant="warning" dot className="shrink-0 hidden sm:inline-flex">
          Simulated data — real backend integration in Phase 6
        </Badge>
      </div>

      {selectedId ? (
        <HistoryDetailPanel
          loading={detailLoading}
          error={detailError}
          record={detailRecord}
          onBack={() => setSelectedId(null)}
          onRetry={() => loadDetail(selectedId)}
        />
      ) : (
        <>
          <HistoryFiltersBar filters={filters} classOptions={availableClassLabels()} onChange={setFilters} />
          <HistoryTable
            loading={listLoading}
            error={listError}
            data={data}
            onSelect={handleSelect}
            onPageChange={(page) => setFilters((f) => ({ ...f, page }))}
            onRetry={loadList}
          />
        </>
      )}
    </div>
  );
}

export default HistoryPage;
