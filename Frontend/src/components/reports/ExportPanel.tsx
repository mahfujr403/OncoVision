import { useState } from 'react';
import { Download, FileText } from 'lucide-react';
import { Card, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { buildSimulatedCsv } from '@/lib/mockReports';

export function ExportPanel() {
  const [downloading, setDownloading] = useState(false);

  function handleCsvExport() {
    setDownloading(true);
    try {
      const csv = buildSimulatedCsv();
      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'oncovision-prediction-history-simulated.csv';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } finally {
      setDownloading(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Export</CardTitle>
      </CardHeader>
      <div className="space-y-3">
        <div className="flex items-center justify-between gap-4 py-2">
          <div>
            <p className="text-sm font-medium text-foreground">CSV Export</p>
            <p className="text-xs text-muted-foreground mt-0.5">
              Downloads the simulated dataset shown on this page. Calls the real{' '}
              <code className="font-mono">/api/v1/reports/export/csv</code> endpoint once backend
              integration lands.
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            icon={<Download className="w-3.5 h-3.5" />}
            loading={downloading}
            onClick={handleCsvExport}
          >
            Download CSV
          </Button>
        </div>

        <div className="flex items-center justify-between gap-4 py-2 border-t border-border">
          <div>
            <div className="flex items-center gap-2">
              <p className="text-sm font-medium text-foreground">PDF Export</p>
              <Badge variant="outline">Backend integration pending</Badge>
            </div>
            <p className="text-xs text-muted-foreground mt-0.5">
              The endpoint exists on the backend but isn't wired up in this build yet.
            </p>
          </div>
          <Button variant="outline" size="sm" icon={<FileText className="w-3.5 h-3.5" />} disabled>
            Download PDF
          </Button>
        </div>
      </div>
    </Card>
  );
}

export default ExportPanel;
