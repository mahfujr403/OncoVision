import React, { useRef, useEffect, useState, useCallback } from 'react';
import { ShieldCheck, Microscope, Sparkles, Activity, Dna } from 'lucide-react';
import { AnimatePresence, motion } from 'framer-motion';
import { ChatBubble } from './ChatBubble';
import { ChatInput } from './ChatInput';
import { OncoVisionIcon } from './OncoVisionIcon';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: any[];
  created_at: string;
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
}) => {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [streamingMsgId, setStreamingMsgId] = useState<string | null>(null);
  const seenMsgIdsRef = useRef<Set<string>>(new Set());
  const isInitialMountRef = useRef<boolean>(true);

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
    if (lastMsg && lastMsg.role === 'assistant' && !seenMsgIdsRef.current.has(lastMsg.id)) {
      seenMsgIdsRef.current.add(lastMsg.id);
      setStreamingMsgId(lastMsg.id);
    }
  }, [messages]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading, scrollToBottom]);

  return (
    <div className="flex flex-col h-full bg-card rounded-xl border shadow-sm overflow-hidden w-full">
      {/* Header with OncoVision Pathological Intelligence Branding */}
      <div className="flex flex-col gap-2.5 p-4 border-b bg-card/95 backdrop-blur-sm z-10">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-primary to-primary/80 flex items-center justify-center text-primary-foreground shadow-sm ring-2 ring-primary/20">
              <OncoVisionIcon className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-semibold tracking-tight text-foreground">{title}</h2>
                <span className="inline-flex items-center gap-1 text-[11px] font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded-full">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                  Patho-AI Core
                </span>
              </div>
              {subtitle && <p className="text-xs text-muted-foreground mt-0.5">{subtitle}</p>}
            </div>
          </div>

          <div className="hidden sm:flex items-center gap-2 text-[11px] text-muted-foreground bg-muted/50 border px-2.5 py-1 rounded-lg">
            <Microscope size={12} className="text-primary" />
            <span>H&E Histopathology RAG</span>
            <span className="text-muted-foreground/40">•</span>
            <Sparkles size={12} className="text-primary" />
            <span>Sub-2s Flash Core</span>
          </div>
        </div>

        {/* Clinical Decision Support Banner */}
        <div className="flex items-center gap-2 text-xs text-blue-700 dark:text-blue-400 bg-blue-50/70 dark:bg-blue-950/20 border border-blue-200/60 dark:border-blue-900/40 px-3 py-1.5 rounded-lg">
          <ShieldCheck size={14} className="flex-shrink-0 text-blue-600 dark:text-blue-400" />
          <span className="leading-tight">
            Clinical Decision Support: Grounded in peer-reviewed oncology & histopathology. Not a replacement for board-certified pathologist review.
          </span>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 scroll-smooth" ref={scrollRef}>
        <div className="max-w-3xl mx-auto w-full">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full min-h-[300px] text-center py-8 px-4">
              <div className="relative w-16 h-16 rounded-2xl bg-gradient-to-tr from-primary/20 via-primary/10 to-transparent border border-primary/25 flex items-center justify-center mb-4 shadow-sm">
                <OncoVisionIcon className="w-8 h-8 text-primary" />
                <div className="absolute -bottom-1 -right-1 w-6 h-6 rounded-full bg-card border border-primary/30 flex items-center justify-center text-primary shadow-xs">
                  <Microscope size={12} />
                </div>
              </div>
              <h3 className="text-lg font-semibold tracking-tight mb-1.5">Welcome to {title}</h3>
              <p className="text-xs sm:text-sm text-muted-foreground max-w-md mb-6 leading-relaxed">
                Ask any questions regarding histopathological tissue patterns, tumor types, or classification insights.
              </p>
              {suggestions && suggestions.length > 0 && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 w-full max-w-xl">
                  {suggestions.map((suggestion, idx) => (
                    <button
                      key={idx}
                      onClick={() => onSend(suggestion)}
                      className="group text-left p-3.5 rounded-xl border border-border/80 bg-card hover:bg-muted/60 hover:border-primary/40 transition-all duration-200 flex items-start gap-2.5 shadow-2xs hover:shadow-xs"
                    >
                      <div className="p-1.5 rounded-lg bg-primary/10 text-primary group-hover:bg-primary group-hover:text-primary-foreground transition-colors shrink-0 mt-0.5">
                        {idx % 4 === 0 ? (
                          <Microscope size={14} />
                        ) : idx % 4 === 1 ? (
                          <Dna size={14} />
                        ) : idx % 4 === 2 ? (
                          <Activity size={14} />
                        ) : (
                          <Sparkles size={14} />
                        )}
                      </div>
                      <div className="min-w-0 flex-1">
                        <span className="block text-xs font-semibold text-foreground/90 group-hover:text-primary transition-colors">
                          {suggestion}
                        </span>
                        <span className="block text-[10px] text-muted-foreground mt-0.5">
                          {idx % 4 === 0
                            ? 'Tissue Diagnostic Query'
                            : idx % 4 === 1
                            ? 'Clinical Pathology'
                            : idx % 4 === 2
                            ? 'AI Model Classification'
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
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex items-center gap-2.5 bg-primary/5 text-primary border border-primary/20 px-3.5 py-2.5 rounded-2xl rounded-tl-xs w-fit mt-2 ml-11 shadow-xs"
                >
                  <div className="relative flex items-center justify-center">
                    <OncoVisionIcon className="w-3.5 h-3.5 animate-spin text-primary" />
                  </div>
                  <span className="text-xs font-medium tracking-wide">
                    Analyzing histopathology knowledge base...
                  </span>
                </motion.div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Input Area */}
      <div className="z-10">
        <ChatInput
          onSend={onSend}
          disabled={isLoading}
          language={language}
          onLanguageChange={onLanguageChange}
        />
      </div>
    </div>
  );
};
