import { ShieldAlert, Terminal } from 'lucide-react';
import { SectionTitle } from '@/components/ui/SectionTitle';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { SearchBox } from '@/components/ui/SearchBox';
import { EmptyState } from '@/components/ui/EmptyState';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/Table';
import { DemoDataBanner } from '@/components/ui/DemoDataBanner';
import { useSearch } from '@/hooks/useSearch';
import { formatDateTime } from '@/utils/formatters';

// DEMO DATA — The FastAPI backend does not currently have a persistent
// audit-log endpoint. The records below illustrate the target operational
// trace schema and event classification for compliance review.
const AUDIT_LOGS = [
  { id: 'al-0941', user: 'dr.chen@memorial.org', action: 'LOGIN', resource: 'auth/session', status: 'success', ip: '10.0.0.12', timestamp: new Date(Date.now() - 1000 * 60 * 5).toISOString() },
  { id: 'al-0942', user: 'dr.chen@memorial.org', action: 'CREATE_PREDICTION', resource: 'predictions/case-1248', status: 'success', ip: '10.0.0.12', timestamp: new Date(Date.now() - 1000 * 60 * 15).toISOString() },
  { id: 'al-0943', user: 'dr.park@nyu.edu', action: 'DOWNLOAD_REPORT', resource: 'reports/rep-001.pdf', status: 'success', ip: '192.168.1.44', timestamp: new Date(Date.now() - 1000 * 60 * 60).toISOString() },
  { id: 'al-0944', user: 'unknown', action: 'LOGIN_ATTEMPT', resource: 'auth/session', status: 'failed', ip: '203.0.113.5', timestamp: new Date(Date.now() - 1000 * 60 * 90).toISOString() },
  { id: 'al-0945', user: 'admin@oncovision.ai', action: 'UPDATE_MODEL_CONFIG', resource: 'models/ensemble_cfg', status: 'success', ip: '10.0.0.1', timestamp: new Date(Date.now() - 1000 * 60 * 180).toISOString() },
  { id: 'al-0946', user: 'dr.hassan@mgh.org', action: 'DELETE_CASE', resource: 'predictions/case-1192', status: 'success', ip: '172.16.0.8', timestamp: new Date(Date.now() - 1000 * 60 * 300).toISOString() },
];

function getActionBadgeVariant(action: string): 'default' | 'secondary' | 'outline' | 'warning' {
  if (action.includes('LOGIN')) return 'outline';
  if (action.includes('DELETE')) return 'warning';
  if (action.includes('UPDATE')) return 'secondary';
  return 'default';
}

export default function AdminAuditLogsPage() {
  const { query, handleSearch } = useSearch();

  const filtered = AUDIT_LOGS.filter(
    (l) =>
      l.user.toLowerCase().includes(query.toLowerCase()) ||
      l.action.toLowerCase().includes(query.toLowerCase()) ||
      l.resource.toLowerCase().includes(query.toLowerCase()) ||
      l.ip.includes(query) ||
      l.id.toLowerCase().includes(query.toLowerCase()),
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <SectionTitle
          title="Audit Logs"
          description="Operational trace workspace recording security events, data access, and administrative actions."
        />
        <Badge variant="outline" className="font-mono text-xs px-2.5 py-1">
          <Terminal className="h-3.5 w-3.5 mr-1.5 text-primary" />
          <span className="text-text-muted">Trace Buffer:</span>
          <span className="ml-1 font-semibold text-text-primary tabular-nums">{AUDIT_LOGS.length} Events</span>
        </Badge>
      </div>

      {/* Mandatory Data Credibility Banner */}
      <DemoDataBanner feature="audit logging" />

      {/* Search and Filters */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <SearchBox
          value={query}
          onChange={handleSearch}
          placeholder="Filter audit events by actor, action, resource, or IP address…"
          className="max-w-md w-full"
        />
        {query && (
          <span className="text-xs text-text-muted font-mono">
            Matched {filtered.length} of {AUDIT_LOGS.length} trace records
          </span>
        )}
      </div>

      {/* Audit Log Table */}
      <Card padding="none">
        {filtered.length === 0 ? (
          <EmptyState
            icon={<ShieldAlert className="h-6 w-6 text-text-muted" />}
            title="No audit events found"
            description={`No operational trace events match "${query}". Try adjusting your search query.`}
          />
        ) : (
          <>
            {/* Desktop Table View */}
            <div className="hidden md:block">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead scope="col">Event ID</TableHead>
                    <TableHead scope="col">Actor / Account</TableHead>
                    <TableHead scope="col">Action</TableHead>
                    <TableHead scope="col">Target Resource</TableHead>
                    <TableHead scope="col">Outcome</TableHead>
                    <TableHead scope="col">Source IP</TableHead>
                    <TableHead scope="col" className="text-right">Timestamp</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filtered.map((l) => (
                    <TableRow key={l.id} className="hover:bg-surface-raised/50 transition-colors">
                      <TableCell className="font-mono text-xs text-text-muted">
                        {l.id}
                      </TableCell>
                      <TableCell className="text-xs font-medium text-text-primary font-mono truncate max-w-[180px]">
                        {l.user}
                      </TableCell>
                      <TableCell>
                        <Badge variant={getActionBadgeVariant(l.action)} className="font-mono text-[10px]">
                          {l.action}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-mono text-xs text-text-secondary truncate max-w-[180px]">
                        {l.resource}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={l.status === 'success' ? 'success' : 'error'}
                          dot
                          className="text-[10px] capitalize font-mono"
                        >
                          {l.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-mono text-xs text-text-muted">
                        {l.ip}
                      </TableCell>
                      <TableCell className="text-right font-mono text-xs tabular-nums text-text-muted">
                        {formatDateTime(l.timestamp)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>

            {/* Mobile Stacked Card View */}
            <div className="divide-y divide-border md:hidden">
              {filtered.map((l) => (
                <div key={l.id} className="p-4 space-y-2.5">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs text-text-muted">{l.id}</span>
                      <Badge
                        variant={l.status === 'success' ? 'success' : 'error'}
                        dot
                        className="text-[10px] capitalize font-mono"
                      >
                        {l.status}
                      </Badge>
                    </div>
                    <Badge variant={getActionBadgeVariant(l.action)} className="font-mono text-[10px]">
                      {l.action}
                    </Badge>
                  </div>

                  <div className="space-y-1 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="text-text-muted text-[11px]">Actor:</span>
                      <span className="font-mono text-text-primary font-medium">{l.user}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-text-muted text-[11px]">Resource:</span>
                      <span className="font-mono text-text-secondary">{l.resource}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-text-muted text-[11px]">IP Address:</span>
                      <span className="font-mono text-text-muted">{l.ip}</span>
                    </div>
                    <div className="flex items-center justify-between pt-1 border-t border-border-subtle">
                      <span className="text-text-muted text-[11px]">Timestamp:</span>
                      <span className="font-mono text-text-muted tabular-nums">{formatDateTime(l.timestamp)}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </Card>
    </div>
  );
}
