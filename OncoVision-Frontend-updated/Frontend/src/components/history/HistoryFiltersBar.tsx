import { Card } from '@/components/ui/Card';
import type { HistoryFilters } from '@/types/history';

function formatClassLabel(raw: string): string {
  return raw
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

interface HistoryFiltersBarProps {
  filters: HistoryFilters;
  classOptions: string[];
  onChange: (filters: HistoryFilters) => void;
}

const selectClass =
  'h-9 rounded border border-border bg-background px-2.5 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-ring';
const inputClass =
  'h-9 rounded border border-border bg-background px-2.5 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-ring';
const labelClass = 'text-[11px] font-medium text-muted-foreground mb-1 block';

export function HistoryFiltersBar({ filters, classOptions, onChange }: HistoryFiltersBarProps) {
  function set<K extends keyof HistoryFilters>(key: K, value: HistoryFilters[K]) {
    onChange({ ...filters, [key]: value, page: key === 'page' ? (value as number) : 1 });
  }

  return (
    <Card padding="sm">
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <div>
          <label className={labelClass}>Status</label>
          <select
            className={selectClass + ' w-full'}
            value={filters.status}
            onChange={(e) => set('status', e.target.value as HistoryFilters['status'])}
          >
            <option value="all">All</option>
            <option value="success">Success</option>
            <option value="partial_success">Partial success</option>
            <option value="failed">Failed</option>
            <option value="pending">Pending</option>
          </select>
        </div>

        <div>
          <label className={labelClass}>Predicted class</label>
          <select
            className={selectClass + ' w-full'}
            value={filters.predicted_class}
            onChange={(e) => set('predicted_class', e.target.value)}
          >
            <option value="all">All</option>
            {classOptions.map((c) => (
              <option key={c} value={c}>
                {formatClassLabel(c)}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className={labelClass}>From</label>
          <input
            type="date"
            className={inputClass + ' w-full'}
            value={filters.start_date ?? ''}
            onChange={(e) => set('start_date', e.target.value || null)}
          />
        </div>

        <div>
          <label className={labelClass}>To</label>
          <input
            type="date"
            className={inputClass + ' w-full'}
            value={filters.end_date ?? ''}
            onChange={(e) => set('end_date', e.target.value || null)}
          />
        </div>

        <div>
          <label className={labelClass}>Min confidence %</label>
          <input
            type="number"
            min={0}
            max={100}
            className={inputClass + ' w-full'}
            value={filters.min_confidence ?? ''}
            onChange={(e) => set('min_confidence', e.target.value === '' ? null : Number(e.target.value))}
          />
        </div>

        <div>
          <label className={labelClass}>Max confidence %</label>
          <input
            type="number"
            min={0}
            max={100}
            className={inputClass + ' w-full'}
            value={filters.max_confidence ?? ''}
            onChange={(e) => set('max_confidence', e.target.value === '' ? null : Number(e.target.value))}
          />
        </div>
      </div>
    </Card>
  );
}

export default HistoryFiltersBar;
