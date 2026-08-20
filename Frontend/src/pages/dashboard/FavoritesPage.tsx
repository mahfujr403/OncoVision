import { Heart, Microscope } from 'lucide-react';
import { SectionTitle } from '@/components/ui/SectionTitle';
import { Card } from '@/components/ui/Card';
import { EmptyState } from '@/components/ui/EmptyState';
import { Badge } from '@/components/ui/Badge';
import { DemoDataBanner } from '@/components/ui/DemoDataBanner';
import { formatRelativeTime, formatPercent } from '@/utils/formatters';
import { CANCER_TYPE_LABELS } from '@/constants/app';

// DEMO DATA — no favorites/starring endpoint exists. `save_history` on the
// prediction request only controls whether a prediction is written to
// Prediction History; it has nothing to do with favoriting.
const FAVORITES = [
  { id: 'p3', image: 'teaching_case_aca_1.tiff', label: 'lung_aca', confidence: 0.989, createdAt: new Date(Date.now() - 86400000).toISOString() },
  { id: 'p9', image: 'benchmark_colon_001.jpg', label: 'colon_benign', confidence: 0.978, createdAt: new Date(Date.now() - 86400000 * 3).toISOString() },
  { id: 'p14', image: 'atypical_scc_case.png', label: 'lung_scc', confidence: 0.903, createdAt: new Date(Date.now() - 86400000 * 7).toISOString() },
];

export default function FavoritesPage() {
  return (
    <div className="space-y-5">
      <SectionTitle
        title="Favorites"
        description="Starred predictions for easy access"
      />

      <DemoDataBanner feature="favorites" />

      {FAVORITES.length === 0 ? (
        <Card>
          <EmptyState
            icon={<Heart className="h-6 w-6" />}
            title="No favorites yet"
            description="Star any prediction to bookmark it here."
          />
        </Card>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {FAVORITES.map((f) => (
            <Card key={f.id} className="space-y-3 hover:border-primary/30 transition-colors cursor-pointer">
              <div className="flex items-center justify-between">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
                  <Microscope className="h-4 w-4 text-primary" />
                </div>
                <Heart className="h-4 w-4 fill-destructive text-destructive" />
              </div>
              <div>
                <p className="text-xs font-medium truncate">{f.image}</p>
                <p className="text-[10px] text-muted-foreground mt-0.5">{CANCER_TYPE_LABELS[f.label]}</p>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[10px] text-muted-foreground">{formatRelativeTime(f.createdAt)}</span>
                <Badge variant="success" className="font-mono text-[10px]">{formatPercent(f.confidence)}</Badge>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
