import { Bookmark, Microscope } from 'lucide-react';
import { SectionTitle } from '@/components/ui/SectionTitle';
import { Card } from '@/components/ui/Card';
import { EmptyState } from '@/components/ui/EmptyState';
import { Badge } from '@/components/ui/Badge';
import { DemoDataBanner } from '@/components/ui/DemoDataBanner';
import { formatDate, formatPercent } from '@/utils/formatters';
import { CANCER_TYPE_LABELS } from '@/constants/app';

// DEMO DATA — no saved-cases endpoint exists on the backend.
const SAVED = [
  { id: 'p7', image: 'rare_scc_case.tiff', label: 'lung_scc', confidence: 0.921, savedAt: new Date(Date.now() - 86400000 * 2).toISOString(), note: 'Unusual morphology — discuss in MDT' },
  { id: 'p12', image: 'colon_aca_grade3.png', label: 'colon_aca', confidence: 0.964, savedAt: new Date(Date.now() - 86400000 * 5).toISOString(), note: 'High-grade adenocarcinoma, confirm staining' },
];

export default function SavedCasesPage() {
  return (
    <div className="space-y-5">
      <SectionTitle
        title="Saved Cases"
        description="Pinned predictions for follow-up or reference"
      />

      <DemoDataBanner feature="saved cases" />

      {SAVED.length === 0 ? (
        <Card>
          <EmptyState
            icon={<Bookmark className="h-6 w-6" />}
            title="No saved cases"
            description="Save any prediction from history for quick reference."
          />
        </Card>
      ) : (
        <div className="grid md:grid-cols-2 gap-4">
          {SAVED.map((c) => (
            <Card key={c.id} className="space-y-3 hover:border-primary/30 transition-colors cursor-pointer">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-2.5">
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                    <Microscope className="h-4 w-4 text-primary" />
                  </div>
                  <div>
                    <p className="text-xs font-medium">{c.image}</p>
                    <p className="text-[10px] text-muted-foreground">{formatDate(c.savedAt)}</p>
                  </div>
                </div>
                <Bookmark className="h-4 w-4 text-primary shrink-0" />
              </div>
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs">{CANCER_TYPE_LABELS[c.label]}</span>
                <Badge variant="success" className="font-mono text-[10px]">{formatPercent(c.confidence)}</Badge>
              </div>
              {c.note && (
                <p className="text-xs text-muted-foreground border-t border-border pt-2">{c.note}</p>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
