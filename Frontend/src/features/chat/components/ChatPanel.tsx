import React, { useRef, useEffect } from 'react';
import { AlertCircle } from 'lucide-react';
import { AnimatePresence, motion } from 'framer-motion';
import { ChatBubble } from './ChatBubble';
import { ChatInput } from './ChatInput';

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

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  return (
    <div className="flex flex-col h-full bg-card rounded-lg border shadow-sm overflow-hidden w-full">
      {/* Header */}
      <div className="flex flex-col p-4 border-b bg-card z-10">
        <h2 className="text-lg font-semibold">{title}</h2>
        {subtitle && <p className="text-sm text-muted-foreground">{subtitle}</p>}
        <div className="mt-2 flex items-start sm:items-center gap-1.5 text-xs text-amber-600 dark:text-amber-500 bg-amber-50 dark:bg-amber-950/30 p-2 rounded-md">
          <AlertCircle size={14} className="mt-0.5 sm:mt-0 flex-shrink-0" />
          <span>AI-generated medical information. Always consult a healthcare professional.</span>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 scroll-smooth" ref={scrollRef}>
        <div className="max-w-3xl mx-auto w-full">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full min-h-[200px] text-center py-10 opacity-70">
              <div className="w-16 h-16 bg-muted rounded-full flex items-center justify-center mb-4">
                <span className="text-2xl">👋</span>
              </div>
              <h3 className="text-lg font-medium mb-2">Welcome to {title}</h3>
              <p className="text-sm text-muted-foreground max-w-md mb-6">
                Ask any questions regarding the reports or knowledge base.
              </p>
              {suggestions && suggestions.length > 0 && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-lg mt-4">
                  {suggestions.map((suggestion, idx) => (
                    <button
                      key={idx}
                      onClick={() => onSend(suggestion)}
                      className="text-left text-sm p-3 rounded-lg border bg-card hover:bg-muted/50 transition-colors"
                    >
                      {suggestion}
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
                    timestamp={msg.created_at ? new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : undefined}
                  />
                ))}
              </AnimatePresence>

              {isLoading && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex gap-1.5 items-center bg-muted text-muted-foreground p-3 rounded-2xl rounded-tl-sm w-fit mt-2 ml-10 border"
                >
                  <span className="w-2 h-2 bg-current rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                  <span className="w-2 h-2 bg-current rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                  <span className="w-2 h-2 bg-current rounded-full animate-bounce"></span>
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
