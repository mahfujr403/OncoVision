import { Info } from 'lucide-react';
import { Card, CardHeader, CardTitle } from '@/components/ui/Card';
import { Toggle } from '@/components/ui/Toggle';
import { Badge } from '@/components/ui/Badge';
import type { PredictionRequestOptions } from '@/types/prediction';

interface PredictionOptionsPanelProps {
  options: PredictionRequestOptions;
  onChange: (options: PredictionRequestOptions) => void;
  disabled?: boolean;
}

function OptionRow({
  label,
  description,
  control,
}: {
  label: React.ReactNode;
  description: string;
  control: React.ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-4 py-3 border-b border-border last:border-0">
      <div className="min-w-0">
        <p className="text-sm font-medium text-foreground">{label}</p>
        <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">{description}</p>
      </div>
      <div className="shrink-0 pt-0.5">{control}</div>
    </div>
  );
}

export function PredictionOptionsPanel({ options, onChange, disabled }: PredictionOptionsPanelProps) {
  function set<K extends keyof PredictionRequestOptions>(key: K, value: PredictionRequestOptions[K]) {
    onChange({ ...options, [key]: value });
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Prediction Options</CardTitle>
      </CardHeader>

      <div>
        <OptionRow
          label="Reliability threshold"
          description="Flags results for review below this confidence level. Does not change the model's prediction or how it was made."
          control={
            <div className="flex items-center gap-3 w-40">
              <input
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={options.confidence_threshold}
                disabled={disabled}
                onChange={(e) => set('confidence_threshold', Number(e.target.value))}
                className="w-24 accent-primary"
                aria-label="Reliability threshold"
              />
              <span className="text-xs font-mono text-foreground w-9 text-right">
                {options.confidence_threshold.toFixed(2)}
              </span>
            </div>
          }
        />

        <OptionRow
          label="Include individual model predictions"
          description="Show each model's own prediction and confidence alongside the final ensemble result."
          control={
            <Toggle
              checked={options.include_individual_predictions}
              onChange={(v) => set('include_individual_predictions', v)}
              disabled={disabled}
              label="Include individual model predictions"
            />
          }
        />

        <OptionRow
          label="Include runtime statistics"
          description="Show AI runtime health and per-request execution timing with the result."
          control={
            <Toggle
              checked={options.include_runtime_statistics}
              onChange={(v) => set('include_runtime_statistics', v)}
              disabled={disabled}
              label="Include runtime statistics"
            />
          }
        />

        <OptionRow
          label="Save to history"
          description="Persist this prediction to your prediction history."
          control={
            <Toggle
              checked={options.save_history}
              onChange={(v) => set('save_history', v)}
              disabled={disabled}
              label="Save to history"
            />
          }
        />

        <OptionRow
          label={
            <span className="inline-flex items-center gap-2">
              Generate report
              <Badge variant="outline">Coming soon</Badge>
            </span>
          }
          description="Accepted by the API today, but report generation isn't implemented on the backend yet — enabling this has no effect."
          control={
            <Toggle
              checked={options.generate_report}
              onChange={(v) => set('generate_report', v)}
              disabled
              label="Generate report (not yet implemented)"
            />
          }
        />
      </div>

      <div className="flex items-start gap-2 mt-4 pt-4 border-t border-border">
        <Info className="w-3.5 h-3.5 text-muted-foreground mt-0.5 shrink-0" />
        <p className="text-xs text-muted-foreground leading-relaxed">
          These are the exact options the prediction API supports today. Nothing here is
          simulated on the backend's behalf.
        </p>
      </div>
    </Card>
  );
}

export default PredictionOptionsPanel;
