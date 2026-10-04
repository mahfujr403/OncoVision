import React, { useRef, useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  Microscope,
  Activity,
  Dna,
  FileText,
  ShieldAlert,
  BookOpen,
  ArrowLeft,
  ArrowRight,
  Loader2,
} from 'lucide-react';
import { AnimatePresence, motion } from 'framer-motion';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { ChatBubble } from './ChatBubble';
import { ChatInput } from './ChatInput';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: any[];
  created_at: string;
}

export interface CaseContext {
  caseId?: string;
  predictedClass?: string | null;
  confidence?: number;
  agreementRatio?: number | null;
  imageFilename?: string;
  status?: string;
}

export interface ChatPanelProps {
  messages: ChatMessage[];
  onSend: (message: string) => void;
  isLoading: boolean;
  title: string;
  subtitle?: string;
  language: 'en' | 'bn';
  onLanguageChange: (lang: 'en' | 'bn') => void;
  suggestions?: string[];
  mode?: 'knowledge' | 'case_discussion';
  caseContext?: CaseContext;
  backUrl?: string;
  onBack?: () => void;
}

function getDiseaseBadgeVariant(
  label: string | null | undefined,
): 'lungAca' | 'lungScc' | 'colonAca' | 'lungBenign' | 'colonBenign' | 'secondary' {
  if (!label) return 'secondary';
  const norm = label.toLowerCase();
  if (norm.includes('lung') && (norm.includes('adeno') || norm.includes('aca'))) return 'lungAca';
  if (norm.includes('lung') && (norm.includes('squamous') || norm.includes('scc'))) return 'lungScc';
  if (norm.includes('colon') && (norm.includes('adeno') || norm.includes('aca'))) return 'colonAca';
  if (norm.includes('lung') && norm.includes('benign')) return 'lungBenign';
  if (norm.includes('colon') && norm.includes('benign')) return 'colonBenign';
  return 'secondary';
}

function formatClassLabel(raw: string | null | undefined): string {
  if (!raw) return '—';
  return raw
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

export const ChatPanel: React.FC<ChatPanelProps> = ({
  messages,
  onSend,
  isLoading,
  title,
  subtitle,
  language,
  onLanguageChange,
  suggestions,
  mode = 'knowledge',
  caseContext,
  backUrl,
  onBack,
}) => {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [streamingMsgId, setStreamingMsgId] = useState<string | null>(null);
  const seenMsgIdsRef = useRef<Set<string>>(new Set());
  const isInitialMountRef = useRef<boolean>(true);

  const isCaseDiscussion = mode === 'case_discussion';

  const scrollToBottom = useCallback(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, []);

  // Track new assistant messages to stream them smoothly
  useEffect(() => {
    if (isInitialMountRef.current) {
      messages.forEach((m) => seenMsgIdsRef.current.add(m.id));
      isInitialMountRef.current = false;
      return;
    }

    const lastMsg = messages[messages.length - 1];
    if (
      lastMsg &&
      lastMsg.role === 'assistant' &&
      !seenMsgIdsRef.current.has(lastMsg.id)
    ) {
      seenMsgIdsRef.current.add(lastMsg.id);
      setStreamingMsgId(lastMsg.id);
    }
  }, [messages]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading, scrollToBottom]);

  return (
    <div
      className="flex flex-col h-full bg-surface rounded-xl border border-border shadow-xs overflow-hidden w-full"
      role="region"
      aria-label={isCaseDiscussion ? 'Case discussion workspace' : 'Medical knowledge assistant'}
    >
      {/* ── Top Header ── */}
      <div className="flex flex-col p-4 border-b border-border bg-surface z-10 gap-2.5">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-surface-raised border border-border flex items-center justify-center text-primary shrink-0 shadow-2xs">
              {isCaseDiscussion ? <Microscope className="w-5 h-5" /> : <BookOpen className="w-5 h-5" />}
            </div>

            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h2 className="text-base font-bold font-display text-text-primary tracking-tight">
                  {title}
                </h2>
                <Badge variant="outline" className="font-mono text-[10px] text-text-muted gap-1">
                  {isCaseDiscussion ? (
                    <>
                      <Microscope className="h-3 w-3 text-primary" />
                      CASE DISCUSSION{caseContext?.caseId ? ` · #${caseContext.caseId.slice(0, 8)}` : ''}
                    </>
                  ) : (
                    <>
                      <BookOpen className="h-3 w-3 text-primary" />
                      MEDICAL KNOWLEDGE
                    </>
                  )}
                </Badge>
              </div>
              {subtitle && (
                <p className="text-xs text-text-muted mt-0.5">{subtitle}</p>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2">
            {backUrl && (
              <Button asChild variant="outline" size="sm" className="gap-1.5 text-xs">
                <Link to={backUrl}>
                  <ArrowLeft className="h-3.5 w-3.5" />
                  Back to Case
                </Link>
              </Button>
            )}
            {onBack && !backUrl && (
              <Button variant="outline" size="sm" onClick={onBack} className="gap-1.5 text-xs">
                <ArrowLeft className="h-3.5 w-3.5" />
                Back
              </Button>
            )}
          </div>
        </div>

        {/* ── Clinical Decision Support Disclaimer ── */}
        <div className="flex items-start gap-2 text-xs text-text-secondary bg-surface-raised/60 border border-border-subtle px-3 py-2 rounded-lg">
          <ShieldAlert size={14} className="shrink-0 text-accent mt-0.5" aria-hidden="true" />
          <span className="leading-relaxed text-[11px] text-text-muted">
            {isCaseDiscussion
              ? 'Investigational Case Discussion: Grounded in computational multi-model ensemble pathology results for this specimen. Does not constitute a definitive or primary medical diagnosis.'
              : 'Investigational Decision Support: Grounded in peer-reviewed pathology concepts and literature knowledge bases. Not a substitute for board-certified pathologist review.'}
          </span>
        </div>
      </div>

      {/* ── Case Context Strip (Prediction-Scoped Chat Only) ── */}
      {isCaseDiscussion && caseContext && (
        <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-2.5 bg-surface-raised/30 border-b border-border text-xs">
          <div className="flex items-center gap-2.5 flex-wrap">
            <span className="text-[10px] uppercase tracking-wider font-mono text-text-muted">
              Context:
            </span>
            {caseContext.caseId && (
              <span className="font-mono text-xs font-semibold text-text-muted">
                Case #{caseContext.caseId.slice(0, 8)}
              </span>
            )}
            {caseContext.predictedClass && (
              <Badge variant={getDiseaseBadgeVariant(caseContext.predictedClass)} className="text-[11px] font-semibold">
                {formatClassLabel(caseContext.predictedClass)}
              </Badge>
            )}
            {caseContext.confidence != null && (
              <span className="font-mono tabular-nums text-xs font-semibold text-text-primary">
                {caseContext.confidence}% confidence
              </span>
            )}
            {caseContext.agreementRatio != null && (
              <span className="font-mono tabular-nums text-xs text-text-secondary">
                ({Math.round(caseContext.agreementRatio * 100)}% agreement)
              </span>
            )}
            {caseContext.imageFilename && (
              <span className="text-[11px] text-text-muted truncate max-w-[180px] font-mono hidden sm:inline">
                Slide: {caseContext.imageFilename}
              </span>
            )}
          </div>

          {caseContext.caseId && (
            <Link
              to={`/history/${caseContext.caseId}`}
              className="inline-flex items-center gap-1 text-[11px] text-primary hover:underline font-medium"
            >
              View Evaluation Record <ArrowRight className="h-3 w-3" />
            </Link>
          )}
        </div>
      )}

      {/* ── Messages Scroll Area ── */}
      <div
        className="flex-1 overflow-y-auto p-4 scroll-smooth"
        ref={scrollRef}
        tabIndex={0}
        aria-label="Conversation message history"
      >
        <div className="max-w-3xl mx-auto w-full">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full min-h-[300px] text-center py-8 px-4">
              <div className="w-14 h-14 rounded-2xl bg-surface-raised border border-border flex items-center justify-center mb-4 shadow-xs text-primary">
                {isCaseDiscussion ? <Microscope className="w-7 h-7" /> : <BookOpen className="w-7 h-7" />}
              </div>

              <h3 className="text-base sm:text-lg font-bold font-display tracking-tight text-text-primary mb-1">
                {isCaseDiscussion
                  ? `Case Discussion: #${caseContext?.caseId?.slice(0, 8) ?? 'Evaluation'}`
                  : 'Medical Knowledge & Evidence Assistant'}
              </h3>

              <p className="text-xs sm:text-sm text-text-muted max-w-md mb-6 leading-relaxed">
                {isCaseDiscussion
                  ? 'Discuss this computational pathology evaluation, cross-architecture agreement, or histological patterns for this specimen.'
                  : 'Ask about histopathological tissue patterns, tumor classifications, or computational pathology methodology.'}
              </p>

              {suggestions && suggestions.length > 0 && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 w-full max-w-xl">
                  {suggestions.map((suggestion, idx) => (
                    <button
                      key={idx}
                      onClick={() => onSend(suggestion)}
                      className="group text-left p-3.5 rounded-xl border border-border bg-surface hover:bg-surface-raised hover:border-primary/40 transition-colors duration-150 flex items-start gap-2.5 shadow-2xs cursor-pointer"
                    >
                      <div className="p-1.5 rounded-lg bg-surface-raised text-primary group-hover:bg-primary group-hover:text-primary-foreground transition-colors shrink-0 mt-0.5 border border-border">
                        {idx % 4 === 0 ? (
                          <Microscope size={14} />
                        ) : idx % 4 === 1 ? (
                          <Dna size={14} />
                        ) : idx % 4 === 2 ? (
                          <Activity size={14} />
                        ) : (
                          <FileText size={14} />
                        )}
                      </div>
                      <div className="min-w-0 flex-1">
                        <span className="block text-xs font-semibold text-text-primary group-hover:text-primary transition-colors">
                          {suggestion}
                        </span>
                        <span className="block text-[10px] text-text-muted mt-0.5 font-mono">
                          {isCaseDiscussion
                            ? idx % 2 === 0
                              ? 'Model Evidence Query'
                              : 'Histopathology Context'
                            : idx % 4 === 0
                              ? 'Tissue Diagnostic Query'
                              : idx % 4 === 1
                                ? 'Clinical Pathology'
                                : idx % 4 === 2
                                  ? 'Ensemble Methodology'
                                  : 'Oncological Screening'}
                        </span>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="flex flex-col">
              <AnimatePresence initial={false}>
                {messages.map((msg) => (
                  <ChatBubble
                    key={msg.id}
                    role={msg.role}
                    content={msg.content}
                    sources={msg.sources}
                    timestamp={
                      msg.created_at
                        ? new Date(msg.created_at).toLocaleTimeString([], {
                            hour: '2-digit',
                            minute: '2-digit',
                          })
                        : undefined
                    }
                    isStreaming={streamingMsgId === msg.id}
                    onStreamComplete={() => setStreamingMsgId(null)}
                    onStreamProgress={scrollToBottom}
                  />
                ))}
              </AnimatePresence>

              {isLoading && (
                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex items-center gap-2.5 bg-surface text-text-primary border border-border px-3.5 py-2.5 rounded-2xl rounded-tl-xs w-fit mt-2 ml-11 shadow-xs"
                  role="status"
                  aria-live="polite"
                >
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-primary shrink-0" aria-hidden="true" />
                  <span className="text-xs font-medium text-text-secondary tracking-wide">
                    {isCaseDiscussion
                      ? 'Analyzing model outputs & formulating clinical explanation…'
                      : 'Retrieving literature evidence & generating response…'}
                  </span>
                </motion.div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* ── Message Composer ── */}
      <div className="z-10">
        <ChatInput
          onSend={onSend}
          disabled={isLoading}
          language={language}
          onLanguageChange={onLanguageChange}
          placeholder={
            isCaseDiscussion
              ? 'Ask about this evaluation, model agreement, or tissue features…'
              : 'Inquire about tissue pathology, tumor classes, or H&E findings…'
          }
        />
      </div>
    </div>
  );
};
