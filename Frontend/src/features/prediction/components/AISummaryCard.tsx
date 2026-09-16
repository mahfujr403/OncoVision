import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Sparkles, MessageSquare, Copy, Check, RefreshCw, AlertCircle, ShieldAlert } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Loader } from '@/components/ui/Loader';
import { ROUTES } from '@/constants/routes';
import { generatePredictionSummary } from '@/api/services/chatService';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';

interface AISummaryCardProps {
  predictionId: string;
  initialSummary?: string | null;
  className?: string;
}

export function AISummaryCard({ predictionId, initialSummary, className }: AISummaryCardProps) {
  const [summary, setSummary] = useState<string | null>(initialSummary ?? null);
  const [language, setLanguage] = useState<'en' | 'bn'>('en');
  const [isLoading, setIsLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = async (targetLang = language) => {
    if (!predictionId) return;
    setIsLoading(true);
    setError(null);
    try {
      const resp = await generatePredictionSummary(predictionId, { language: targetLang });
      setSummary(resp.summary_text);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to generate AI summary';
      setError(msg);
      toast.error('Could not generate summary. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopy = async () => {
    if (!summary) return;
    try {
      await navigator.clipboard.writeText(summary);
      setCopied(true);
      toast.success('Summary copied to clipboard');
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error('Failed to copy text');
    }
  };

  const handleLanguageChange = (lang: 'en' | 'bn') => {
    setLanguage(lang);
    if (summary) {
      handleGenerate(lang);
    }
  };

  return (
    <div className={cn('rounded-xl border border-border bg-card p-6 shadow-sm space-y-4', className)}>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-border/70">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary shrink-0">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold text-foreground">AI Clinical Assistant</h3>
              <Badge variant="outline" className="text-[10px] font-mono px-1.5 py-0 bg-primary/5 text-primary border-primary/20">
                Gemini 2.5
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground">
              Synthesized medical summary &amp; interactive case discussion
            </p>
          </div>
        </div>

        {/* Language selector & Chat Link */}
        <div className="flex items-center gap-2 self-start sm:self-auto">
          <div className="inline-flex rounded-lg border border-border bg-muted/40 p-0.5 text-xs font-medium">
            <button
              type="button"
              onClick={() => handleLanguageChange('en')}
              className={cn(
                'px-2.5 py-1 rounded-md transition-colors',
                language === 'en'
                  ? 'bg-background text-foreground shadow-xs font-semibold'
                  : 'text-muted-foreground hover:text-foreground'
              )}
            >
              English
            </button>
            <button
              type="button"
              onClick={() => handleLanguageChange('bn')}
              className={cn(
                'px-2.5 py-1 rounded-md transition-colors',
                language === 'bn'
                  ? 'bg-background text-foreground shadow-xs font-semibold'
                  : 'text-muted-foreground hover:text-foreground'
              )}
            >
              বাংলা
            </button>
          </div>

          <Button asChild variant="outline" size="sm" className="gap-1.5 text-xs">
            <Link to={`${ROUTES.PREDICTION_CHAT}/${predictionId}`}>
              <MessageSquare className="w-3.5 h-3.5 text-primary" />
              AI Chat
            </Link>
          </Button>
        </div>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="py-8 flex flex-col items-center justify-center gap-3 text-center">
          <Loader size="md" />
          <div className="space-y-1">
            <p className="text-sm font-medium text-foreground">Synthesizing clinical findings...</p>
            <p className="text-xs text-muted-foreground">
              Analyzing ensemble probabilities and formulating structured oncologist notes.
            </p>
          </div>
        </div>
      )}

      {/* Error state */}
      {!isLoading && error && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-4 space-y-3">
          <div className="flex items-start gap-2.5 text-destructive text-xs font-medium">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
          <Button size="sm" variant="outline" onClick={() => handleGenerate()} className="gap-1.5 text-xs">
            <RefreshCw className="w-3.5 h-3.5" />
            Try again
          </Button>
        </div>
      )}

      {/* Empty / Not yet generated state */}
      {!isLoading && !summary && !error && (
        <div className="rounded-lg border border-dashed border-border/80 bg-muted/20 p-5 text-center space-y-3">
          <p className="text-xs text-muted-foreground max-w-md mx-auto">
            Generate an AI-synthesized explanation of this ensemble prediction, model confidence, and histopathological implications in {language === 'en' ? 'English' : 'Bangla'}.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-2 pt-1">
            <Button
              variant="primary"
              size="sm"
              onClick={() => handleGenerate()}
              className="gap-1.5 shadow-sm"
            >
              <Sparkles className="w-3.5 h-3.5" />
              Generate AI Summary
            </Button>
            <Button asChild variant="ghost" size="sm" className="gap-1.5">
              <Link to={`${ROUTES.PREDICTION_CHAT}/${predictionId}`}>
                <MessageSquare className="w-3.5 h-3.5" />
                Discuss in AI Chat
              </Link>
            </Button>
          </div>
        </div>
      )}

      {/* Generated summary display */}
      {!isLoading && summary && (
        <div className="space-y-3">
          <div className="rounded-lg border border-border/60 bg-muted/25 p-4 text-sm text-foreground/90 whitespace-pre-line leading-relaxed font-sans">
            {summary}
          </div>

          {/* Action bar */}
          <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
            <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
              <ShieldAlert className="w-3.5 h-3.5 text-warning shrink-0" />
              <span>AI-generated for reference only. Consult a certified pathologist.</span>
            </div>

            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={handleCopy}
                className="gap-1.5 text-xs h-8"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
                {copied ? 'Copied' : 'Copy'}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleGenerate()}
                className="gap-1.5 text-xs h-8"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                Regenerate
              </Button>
              <Button asChild variant="primary" size="sm" className="gap-1.5 text-xs h-8">
                <Link to={`${ROUTES.PREDICTION_CHAT}/${predictionId}`}>
                  <MessageSquare className="w-3.5 h-3.5" />
                  Discuss with AI
                </Link>
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
