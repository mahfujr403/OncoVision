import { Loader2, ScanLine } from 'lucide-react';
import { Card } from '@/components/ui/Card';

export function ProcessingPanel({ fileName }: { fileName: string }) {
  return (
    <Card className="flex flex-col items-center justify-center text-center py-16 px-8">
      <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center text-primary mb-5 relative">
        <ScanLine className="w-5 h-5 z-10" />
        <Loader2 className="w-12 h-12 spin-icon absolute text-primary/25" />
      </div>
      <p className="text-sm font-semibold text-foreground">Running AI-assisted analysis…</p>
      <p className="text-xs text-muted-foreground mt-1.5 max-w-xs">
        Analyzing <span className="font-mono">{fileName}</span> across available models. This
        usually takes a few seconds.
      </p>
      <div className="w-48 h-1.5 rounded-full bg-muted mt-6 overflow-hidden">
        <div className="h-full w-1/3 bg-primary rounded-full indeterminate-bar" />
      </div>
    </Card>
  );
}

export default ProcessingPanel;
