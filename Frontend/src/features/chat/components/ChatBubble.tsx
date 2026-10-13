import React, { useState, useEffect, useMemo } from 'react';
import { User, Brain, BookOpen, ExternalLink, ChevronDown } from 'lucide-react';
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
  const [isSourcesExpanded, setIsSourcesExpanded] = useState<boolean>(false);

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

  // Filter sources strictly for valid, clickable external URLs with proper publication titles
  const validSources = useMemo(() => {
    if (!sources || !Array.isArray(sources)) return [];
    return sources.filter((s: any) => {
      const rawUrl = (s.url || s.source_url || '').trim();
      const isHttp = rawUrl.startsWith('http://') || rawUrl.startsWith('https://');
      if (!isHttp) return false;

      const book = (s.source_title || s.title || '').trim().toLowerCase();
      const invalidPlaceholders = [
        'histopathology',
        'lung cancer',
        'colon cancer',
        'general oncology',
        'clinical reference',
        'medical literature',
        'histopathological concepts',
        'lung pathology',
        'colon pathology',
        'internal',
      ];
      if (!book || invalidPlaceholders.includes(book)) return false;

      return true;
    });
  }, [sources]);

  const canShowReferences =
    !isActivelyStreaming &&
    !isStreaming &&
    Boolean(visibleText && visibleText.trim().length > 0) &&
    validSources.length > 0;

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
              <div>
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

                {/* References footnote: strictly rendered only when generation is finished, content exists, and verifiable clickable external URLs are present */}
                {canShowReferences && (
                  <div className="mt-3.5 pt-2.5 border-t border-border/40 text-xs">
                    <div className="flex items-center justify-between">
                      {validSources.length > 1 ? (
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            setIsSourcesExpanded((prev) => !prev);
                          }}
                          className="inline-flex items-center gap-1.5 text-[11px] font-semibold text-text-muted hover:text-text-primary transition-colors cursor-pointer py-0.5 select-none"
                          aria-expanded={isSourcesExpanded}
                        >
                          <BookOpen size={11} className="text-primary/70" />
                          <span>References ({validSources.length})</span>
                          <ChevronDown
                            size={11}
                            className={cn(
                              'transition-transform duration-200 text-text-muted',
                              isSourcesExpanded && 'rotate-180 text-text-primary'
                            )}
                          />
                        </button>
                      ) : (
                        <div className="inline-flex items-center gap-1.5 text-[11px] font-semibold text-text-muted">
                          <BookOpen size={11} className="text-primary/70" />
                          <span>References:</span>
                        </div>
                      )}
                    </div>

                    {(validSources.length === 1 || isSourcesExpanded) && (
                      <ol className="mt-2 space-y-1.5 pl-0 list-none">
                        {validSources.map((source, idx) => {
                          const book = source.source_title || source.title || 'Medical Literature';
                          const section = source.document_title || source.topic || '';
                          const rawUrl = source.url || (source as any).source_url;
                          const url = rawUrl?.trim();
                          const formattedRef = source.citation || (
                            section && section.toLowerCase() !== book.toLowerCase()
                              ? `{ ${book}, ${section} / ${url} }`
                              : `{ ${book} / ${url} }`
                          );

                          return (
                            <li
                              key={idx}
                              className="flex items-start gap-1.5 text-[11px] font-mono leading-relaxed text-text-secondary"
                            >
                              <span className="text-text-muted shrink-0 select-none">[{idx + 1}]</span>
                              <a
                                href={url}
                                target="_blank"
                                rel="noopener noreferrer"
                                onClick={(e) => e.stopPropagation()}
                                className="inline-flex items-baseline gap-1 text-primary hover:underline hover:text-primary/90 transition-colors break-all cursor-pointer font-medium"
                                title={url}
                              >
                                <span>{formattedRef}</span>
                                <ExternalLink size={10} className="shrink-0 text-primary/70 inline self-center" />
                              </a>
                            </li>
                          );
                        })}
                      </ol>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Timestamp */}
          {!isActivelyStreaming && timestamp && (
            <div className={cn('flex mt-0.5', isUser ? 'justify-end' : 'justify-start')}>
              <span className="text-[11px] font-mono text-text-muted px-1">{timestamp}</span>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
};
