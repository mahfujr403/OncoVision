import React from 'react';
import { Bot, User } from 'lucide-react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

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

export const ChatBubble: React.FC<ChatBubbleProps> = ({ role, content, timestamp, sources }) => {
  const isUser = role === 'user';

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={cn("flex w-full mb-4", isUser ? "justify-end" : "justify-start")}
    >
      <div className={cn("flex max-w-[80%] gap-3", isUser ? "flex-row-reverse" : "flex-row")}>
        <div className="flex-shrink-0 mt-1">
          {isUser ? (
            <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-primary-foreground">
              <User size={18} />
            </div>
          ) : (
            <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center text-muted-foreground border">
              <Bot size={18} />
            </div>
          )}
        </div>
        
        <div className="flex flex-col gap-1">
          <div
            className={cn(
              "px-4 py-2.5 rounded-2xl text-sm",
              isUser
                ? "bg-primary text-primary-foreground rounded-tr-sm"
                : "bg-muted text-foreground rounded-tl-sm border"
            )}
          >
            {isUser ? <p className="whitespace-pre-wrap">{content}</p> : renderMarkdown(content)}
          </div>
          
          {(timestamp || sources?.length) && (
            <div className={cn("flex flex-col gap-1.5 mt-1", isUser ? "items-end" : "items-start")}>
              {sources && sources.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {sources.map((source, idx) => (
                    <a
                      key={idx}
                      href={source.source}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center text-[10px] bg-secondary text-secondary-foreground px-2 py-0.5 rounded-full hover:bg-secondary/80 transition-colors"
                      title={`Relevance: ${(source.relevance * 100).toFixed(0)}%`}
                    >
                      {source.title}
                    </a>
                  ))}
                </div>
              )}
              {timestamp && (
                <span className="text-xs text-muted-foreground px-1">{timestamp}</span>
              )}
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
};
