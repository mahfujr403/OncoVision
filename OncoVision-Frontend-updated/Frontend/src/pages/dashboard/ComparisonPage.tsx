import { GitCompare } from 'lucide-react';
import { SectionTitle } from '@/components/ui/SectionTitle';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { EmptyState } from '@/components/ui/EmptyState';
import { DemoDataBanner } from '@/components/ui/DemoDataBanner';
import { Button } from '@/components/ui/Button';
import { Link } from 'react-router-dom';
import { ROUTES } from '@/constants/routes';

// DEMO DATA — the backend has no comparison/multi-case-selection workflow;
// each prediction is fetched individually via GET /predictions/history/{id}.
export default function ComparisonPage() {
  return (
    <div className="space-y-5">
      <SectionTitle
        title="Case Comparison"
        description="Side-by-side analysis of multiple predictions"
        action={
          <Button size="sm" asChild>
            <Link to={ROUTES.HISTORY}>Select cases</Link>
          </Button>
        }
      />

      <DemoDataBanner feature="case comparison" />

      <div className="grid md:grid-cols-2 gap-4 min-h-[400px]">
        {[1, 2].map((slot) => (
          <Card
            key={slot}
            variant="ghost"
            className="border-dashed flex flex-col items-center justify-center min-h-[300px]"
          >
            <EmptyState
              icon={<GitCompare className="h-6 w-6" />}
              title={`Case ${slot}`}
              description="Select a prediction from history to compare here."
              action={{ label: 'Browse history', onClick: () => {} }}
            />
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Comparison Matrix</CardTitle>
          <CardDescription>Model-by-model confidence breakdown will appear once two cases are selected.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-40 flex items-center justify-center rounded-md border border-dashed border-border">
            <p className="text-xs text-muted-foreground">Select two cases to view comparison data</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
