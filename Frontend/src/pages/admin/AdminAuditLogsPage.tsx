import { SectionTitle } from '@/components/ui/SectionTitle';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { SearchBox } from '@/components/ui/SearchBox';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/Table';
import { useSearch } from '@/hooks/useSearch';
import { formatDateTime } from '@/utils/formatters';

const AUDIT_LOGS = [
  { id: 'al001', user: 'dr.chen@memorial.org', action: 'LOGIN', resource: 'auth', status: 'success', ip: '10.0.0.12', timestamp: new Date(Date.now() - 1000 * 60 * 5).toISOString() },
  { id: 'al002', user: 'dr.chen@memorial.org', action: 'CREATE_PREDICTION', resource: 'predictions/p1248', status: 'success', ip: '10.0.0.12', timestamp: new Date(Date.now() - 1000 * 60 * 15).toISOString() },
  { id: 'al003', user: 'dr.park@nyu.edu', action: 'DOWNLOAD_REPORT', resource: 'reports/rep_001', status: 'success', ip: '192.168.1.44', timestamp: new Date(Date.now() - 1000 * 60 * 60).toISOString() },
  { id: 'al004', user: 'unknown', action: 'LOGIN', resource: 'auth', status: 'failed', ip: '203.0.113.5', timestamp: new Date(Date.now() - 1000 * 60 * 90).toISOString() },
  { id: 'al005', user: 'admin@oncovision.ai', action: 'UPDATE_MODEL', resource: 'models/m2', status: 'success', ip: '10.0.0.1', timestamp: new Date(Date.now() - 1000 * 60 * 180).toISOString() },
  { id: 'al006', user: 'dr.hassan@mgh.org', action: 'DELETE_PREDICTION', resource: 'predictions/p1192', status: 'success', ip: '172.16.0.8', timestamp: new Date(Date.now() - 1000 * 60 * 300).toISOString() },
];

export default function AdminAuditLogsPage() {
  const { query, handleSearch } = useSearch();

  const filtered = AUDIT_LOGS.filter(
    (l) =>
      l.user.toLowerCase().includes(query.toLowerCase()) ||
      l.action.toLowerCase().includes(query.toLowerCase()),
  );

  return (
    <div className="space-y-5">
      <SectionTitle
        title="Audit Logs"
        description="All platform actions are recorded for compliance"
        action={
          <div className="flex items-center gap-1.5 rounded-full border border-emerald-500/20 bg-emerald-500/5 px-3 py-1">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-xs text-emerald-400">Recording</span>
          </div>
        }
      />

      <SearchBox value={query} onChange={handleSearch} placeholder="Search by user or action..." className="max-w-sm" />

      <Card padding="none">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>ID</TableHead>
              <TableHead>User</TableHead>
              <TableHead>Action</TableHead>
              <TableHead>Resource</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>IP Address</TableHead>
              <TableHead>Timestamp</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.map((l) => (
              <TableRow key={l.id}>
                <TableCell className="font-mono text-[10px] text-muted-foreground">{l.id}</TableCell>
                <TableCell className="text-xs font-medium max-w-[140px] truncate">{l.user}</TableCell>
                <TableCell>
                  <code className="text-[11px] font-mono bg-secondary px-1.5 py-0.5 rounded">{l.action}</code>
                </TableCell>
                <TableCell className="font-mono text-[11px] text-muted-foreground">{l.resource}</TableCell>
                <TableCell>
                  <Badge variant={l.status === 'success' ? 'success' : 'destructive'} dot className="text-[10px]">
                    {l.status}
                  </Badge>
                </TableCell>
                <TableCell className="font-mono text-[11px] text-muted-foreground">{l.ip}</TableCell>
                <TableCell className="text-[11px] text-muted-foreground">{formatDateTime(l.timestamp)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
}
