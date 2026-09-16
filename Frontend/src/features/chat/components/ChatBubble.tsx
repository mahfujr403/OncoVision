import React, { useState, useEffect, useMemo } from 'react';
import { User, Microscope, FileText, ExternalLink } from 'lucide-react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { OncoVisionIcon } from './OncoVisionIcon';

export interface ChatBubbleSource {
  title: string;
  source: string;
  relevance: number;
}

export interface ChatBubbleProps {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
  sources?: ChatBubbleSource[];
  isStreaming?: boolean;
  onStreamComplete?: () => void;
  onStreamProgress?: () => void;
}

const renderMarkdown = (text: string) => {
  let html = text;
  // Bold
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  // Italic
  html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
  // Newlines
  html = html.replace(/\n/g, '<br />');
  // Bullet points
  html = html.replace(/^- (.*)$/gm, '<li>$1</li>');
  
  // Wrap bullet points in ul if there are any
  if (html.includes('<li>')) {
    html = html.replace(/(<li>.*<\/li>)/s, '<ul class="list-disc pl-4 my-2">$1</ul>');
  }

  return <div dangerouslySetInnerHTML={{ __html: html }} className="space-y-1" />;
};

export const ChatBubble: React.FC<ChatBubbleProps> = ({
  role,
  content,
  timestamp,
  sources,
  isStreaming = false,
  onStreamComplete,
  onStreamProgress,
}) => {
  const isUser = role === 'user';

  // Word/token streaming effect
  const words = useMemo(() => {
    return content.split(/(\s+)/);
  }, [content]);

  const [streamIndex, setStreamIndex] = useState<number>(() => (isStreaming ? 1 : words.length));

  useEffect(() => {
    if (!isStreaming) {
      setStreamIndex(words.length);
      return;
    }

    setStreamIndex(1);
    const interval = setInterval(() => {
      setStreamIndex((prev) => {
        const next = prev + 1;
        if (next >= words.length) {
          clearInterval(interval);
          onStreamComplete?.();
          return words.length;
        }
        onStreamProgress?.();
        return next;
      });
    }, 24);

    return () => clearInterval(interval);
  }, [isStreaming, words, onStreamComplete, onStreamProgress]);

  const isActivelyStreaming = isStreaming && streamIndex < words.length;
  const visibleText = isActivelyStreaming ? words.slice(0, streamIndex).join('') : content;

  const handleSkipStream = () => {
    if (isActivelyStreaming) {
      setStreamIndex(words.length);
      onStreamComplete?.();
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className={cn("flex w-full mb-4.5", isUser ? "justify-end" : "justify-start")}
    >
      <div className={cn("flex max-w-[85%] md:max-w-[78%] gap-3", isUser ? "flex-row-reverse" : "flex-row")}>
        {/* Avatar */}
        <div className="flex-shrink-0 mt-1">
          {isUser ? (
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center text-primary-foreground shadow-xs">
              <User size={16} />
            </div>
          ) : (
            <div className="w-8 h-8 rounded-lg bg-primary/10 border border-primary/25 flex items-center justify-center text-primary shadow-xs ring-2 ring-primary/5">
              <OncoVisionIcon className="w-4.5 h-4.5" />
            </div>
          )}
        </div>
        
        {/* Content Container */}
        <div className="flex flex-col gap-1 min-w-0">
          {!isUser && (
            <div className="flex items-center gap-1.5 px-0.5 mb-0.5">
              <span className="text-[11px] font-semibold text-primary uppercase tracking-wider flex items-center gap-1">
                <Microscope className="w-3 h-3 text-primary" />
                OncoVision Patho-AI
              </span>
              <span className="text-[10px] text-muted-foreground/60">•</span>
              <span className="text-[10px] text-muted-foreground">Histopathology Intelligence</span>
            </div>
          )}

          <div
            onClick={handleSkipStream}
            className={cn(
              "px-4 py-3 rounded-2xl text-sm leading-relaxed transition-all",
              isUser
                ? "bg-primary text-primary-foreground rounded-tr-xs shadow-xs"
                : "bg-card text-foreground rounded-tl-xs border border-primary/15 shadow-xs hover:border-primary/30",
              isActivelyStreaming && "cursor-pointer"
            )}
            title={isActivelyStreaming ? "Click to reveal immediately" : undefined}
          >
            {isUser ? (
              <p className="whitespace-pre-wrap">{content}</p>
            ) : (
              <div className="inline">
                {renderMarkdown(visibleText)}
                {isActivelyStreaming && (
                  <span className="inline-block w-1.5 h-3.5 ml-1 bg-primary align-middle rounded-xs animate-pulse" />
                )}
              </div>
            )}
          </div>
          
          {/* Metadata: Sources & Timestamp */}
          {(!isActivelyStreaming && (timestamp || sources?.length)) && (
            <div className={cn("flex flex-col gap-1.5 mt-1", isUser ? "items-end" : "items-start")}>
              {sources && sources.length > 0 && (
                <div className="flex flex-col gap-1 w-full mt-0.5">
                  <span className="text-[10px] font-medium text-muted-foreground flex items-center gap-1">
                    <FileText size={10} className="text-primary/70" /> Cited Histopathological Sources:
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {sources.map((source, idx) => (
                      <a
                        key={idx}
                        href={source.source}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-[10px] bg-primary/5 hover:bg-primary/10 text-primary border border-primary/15 px-2.5 py-1 rounded-md transition-colors"
                        title={`Source: ${source.source} (Relevance: ${(source.relevance * 100).toFixed(0)}%)`}
                      >
                        <span className="w-1.5 h-1.5 rounded-full bg-primary/70"></span>
                        <span className="truncate max-w-[220px] font-medium">{source.title}</span>
                        <ExternalLink size={9} className="opacity-70 ml-0.5" />
                      </a>
                    ))}
                  </div>
                </div>
              )}
              {timestamp && (
                <span className="text-[11px] text-muted-foreground px-1">{timestamp}</span>
              )}
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
};
