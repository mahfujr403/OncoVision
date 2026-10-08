import React, { useState, useEffect, useMemo } from 'react';
import { User, Brain, BookOpen, ExternalLink } from 'lucide-react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

export interface ChatBubbleSource {
  title: string;
  source: string;
  relevance: number;
  url?: string;
  document_title?: string;
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

/** Safely escape raw text to prevent XSS before applying structured formatting */
function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

const renderMarkdown = (text: string) => {
  if (!text) return null;

  // 1. First escape raw HTML to block arbitrary script/tag injection
  let html = escapeHtml(text);

  const links: string[] = [];

  // 2. Extract and replace Markdown links [label](url) with safe placeholders
  html = html.replace(
    /\[([^\]]+)\]\(((?:https?:\/\/|mailto:)[^\s\)]+)\)/g,
    (_, label, url) => {
      const id = `%%LINK_${links.length}%%`;
      const isMail = url.startsWith('mailto:');
      links.push(
        `<a href="${url}" ${isMail ? '' : 'target="_blank" rel="noopener noreferrer" '}class="text-primary underline decoration-primary/40 underline-offset-2 hover:decoration-primary hover:text-primary/80 font-medium transition-colors cursor-pointer inline-flex items-center gap-0.5">${label}</a>`,
      );
      return id;
    },
  );

  // 3. Convert standalone raw URLs (http/https only for safety)
  html = html.replace(
    /\b(https?:\/\/[^\s<"'\)]+)/g,
    '<a href="$1" target="_blank" rel="noopener noreferrer" class="text-primary underline decoration-primary/40 underline-offset-2 hover:decoration-primary hover:text-primary/80 font-medium transition-colors cursor-pointer inline-flex items-center gap-0.5 break-all">$1</a>',
  );

  // 4. Restore sanitized links
  links.forEach((linkHtml, i) => {
    html = html.replace(`%%LINK_${i}%%`, linkHtml);
  });

  // 5. Inline Code: `code`
  html = html.replace(
    /`([^`]+)`/g,
    '<code class="font-mono text-xs bg-surface-raised px-1.5 py-0.5 rounded border border-border-subtle text-text-primary">$1</code>',
  );

  // 6. Bold: **text**
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong class="font-semibold text-text-primary">$1</strong>');

  // 7. Italic: *text*
  html = html.replace(/(?<!\*)\*(?!\*)(.*?)(?<!\*)\*(?!\*)/g, '<em class="italic text-text-secondary">$1</em>');

  // 8. Process headings, bullet points, and paragraphs
  const lines = html.split('\n');
  const processedLines: string[] = [];
  let inList = false;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Headings
    const headingMatch = line.match(/^(#{1,3})\s+(.*)$/);
    if (headingMatch) {
      if (inList) {
        processedLines.push('</ul>');
        inList = false;
      }
      processedLines.push(
        `<h4 class="font-bold text-text-primary mt-2.5 mb-1 text-sm tracking-tight">${headingMatch[2]}</h4>`,
      );
      continue;
    }

    // Bullet points
    const bulletMatch = line.match(/^(\s*)[-*]\s+(.*)$/);
    if (bulletMatch) {
      if (!inList) {
        processedLines.push('<ul class="list-disc pl-5 my-1.5 space-y-1 text-text-secondary">');
        inList = true;
      }
      processedLines.push(`<li class="leading-relaxed text-xs md:text-sm">${bulletMatch[2]}</li>`);
    } else {
      if (inList) {
        processedLines.push('</ul>');
        inList = false;
      }
      if (line.trim() === '') {
        processedLines.push('<div class="h-2"></div>');
      } else {
        processedLines.push(`<p class="leading-relaxed text-xs md:text-sm text-text-primary my-0.5">${line}</p>`);
      }
    }
  }
  if (inList) {
    processedLines.push('</ul>');
  }

  return (
    <div
      dangerouslySetInnerHTML={{ __html: processedLines.join('') }}
      className="space-y-0.5 text-xs md:text-sm leading-relaxed"
    />
  );
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
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className={cn('flex w-full mb-4.5', isUser ? 'justify-end' : 'justify-start')}
      role="article"
      aria-label={isUser ? 'Your inquiry' : 'Clinical Assistant response'}
    >
      <div className={cn('flex max-w-[88%] md:max-w-[80%] gap-3', isUser ? 'flex-row-reverse' : 'flex-row')}>
        {/* Avatar */}
        <div className="flex-shrink-0 mt-0.5">
          {isUser ? (
            <div
              className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center text-primary-foreground shadow-xs"
              aria-hidden="true"
            >
              <User size={15} />
            </div>
          ) : (
            <div
              className="w-8 h-8 rounded-lg bg-surface-raised border border-border flex items-center justify-center text-primary shadow-xs"
              aria-hidden="true"
            >
              <Brain size={15} />
            </div>
          )}
        </div>

        {/* Message Container */}
        <div className="flex flex-col gap-1 min-w-0">
          {!isUser && (
            <div className="flex items-center gap-1.5 px-0.5 mb-0.5">
              <span className="text-[11px] font-semibold text-text-secondary flex items-center gap-1">
                <Brain className="w-3 h-3 text-primary" aria-hidden="true" />
                Clinical Knowledge Assistant
              </span>
              <span className="text-[10px] text-text-muted/60">•</span>
              <span className="text-[10px] text-text-muted font-mono">Evidence-Oriented</span>
            </div>
          )}

          <div
            onClick={handleSkipStream}
            className={cn(
              'px-4 py-3 rounded-2xl text-xs md:text-sm leading-relaxed transition-all shadow-xs',
              isUser
                ? 'bg-primary text-primary-foreground rounded-tr-xs'
                : 'bg-surface text-text-primary rounded-tl-xs border border-border hover:border-border-emphasis',
              isActivelyStreaming && 'cursor-pointer',
            )}
            title={isActivelyStreaming ? 'Click to show full text' : undefined}
          >
            {isUser ? (
              <p className="whitespace-pre-wrap">{content}</p>
            ) : (
              <div className="inline">
                {renderMarkdown(visibleText)}
                {isActivelyStreaming && (
                  <span
                    className="inline-block w-1.5 h-3.5 ml-1 bg-primary align-middle rounded-xs animate-pulse"
                    role="status"
                    aria-label="Generating response"
                  />
                )}
              </div>
            )}
          </div>

          {/* Metadata: Sources & Timestamp */}
          {!isActivelyStreaming && (
            <div className={cn('flex flex-col gap-1.5 mt-1', isUser ? 'items-end' : 'items-start')}>
              {/* Retrieved Sources Section */}
              {sources && sources.length > 0 && (
                <div className="flex flex-col gap-1.5 w-full mt-1.5 p-3 rounded-xl border border-border bg-surface-raised/40">
                  <div className="flex items-center justify-between text-[11px] font-semibold text-text-secondary">
                    <span className="flex items-center gap-1.5">
                      <BookOpen size={12} className="text-primary" aria-hidden="true" />
                      Retrieved Evidence &amp; Knowledge Sources ({sources.length})
                    </span>
                    <span className="text-[10px] font-mono text-text-muted">Grounded Literature</span>
                  </div>

                  <div className="flex flex-wrap gap-2 pt-1">
                    {sources.map((source, idx) => {
                      const getSourceUrl = (): string => {
                        if (source.url && (source.url.startsWith('http://') || source.url.startsWith('https://'))) {
                          return source.url;
                        }
                        const cleanPath = (source.source || '').replace(/\\/g, '/');
                        if (cleanPath.startsWith('http://') || cleanPath.startsWith('https://')) {
                          return cleanPath;
                        }
                        return `https://github.com/mahfujr403/OncoVision/blob/main/${cleanPath}`;
                      };

                      const displayTitle = source.document_title || (source.title ? source.title.replace(/_/g, ' ') : 'Medical Evidence');

                      return (
                        <a
                          key={idx}
                          href={getSourceUrl()}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="group inline-flex items-center gap-1.5 text-xs bg-surface hover:bg-surface-raised text-text-primary border border-border hover:border-primary/40 px-2.5 py-1.5 rounded-lg transition-colors shadow-2xs"
                          aria-label={`Source reference: ${displayTitle} (${source.source})`}
                        >
                          <span className="font-mono text-[10px] text-primary font-bold">[{idx + 1}]</span>
                          <span className="truncate max-w-[220px] text-[11px] font-medium text-text-primary group-hover:text-primary transition-colors capitalize">
                            {displayTitle}
                          </span>
                          {source.relevance != null && (
                            <span className="font-mono text-[10px] tabular-nums text-text-muted">
                              ({Math.round(source.relevance * 100)}%)
                            </span>
                          )}
                          <ExternalLink size={10} className="text-text-muted group-hover:text-primary transition-colors shrink-0" />
                        </a>
                      );
                    })}
                  </div>
                </div>
              )}

              {timestamp && (
                <span className="text-[11px] font-mono text-text-muted px-1">{timestamp}</span>
              )}
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
};
