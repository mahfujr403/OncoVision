import React, { useState, useRef, useEffect } from 'react';
import { Send, Globe } from 'lucide-react';
import { Button } from '@/components/ui/Button';

export interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
  language: 'en' | 'bn';
  onLanguageChange: (lang: 'en' | 'bn') => void;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  onSend,
  disabled = false,
  placeholder = 'Inquire about tissue pathology, tumor classes, or H&E findings…',
  language,
  onLanguageChange,
}) => {
  const [message, setMessage] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const adjustHeight = () => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 110)}px`;
    }
  };

  useEffect(() => {
    adjustHeight();
  }, [message]);

  useEffect(() => {
    if (!disabled) {
      const timer = setTimeout(() => {
        textareaRef.current?.focus();
      }, 50);
      return () => clearTimeout(timer);
    }
  }, [disabled]);

  const handleSend = () => {
    if (message.trim() && !disabled) {
      onSend(message.trim());
      setMessage('');
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const toggleLanguage = () => {
    onLanguageChange(language === 'en' ? 'bn' : 'en');
  };

  return (
    <div className="flex flex-col gap-2 p-3 bg-surface border-t border-border">
      <div className="flex items-end gap-2">
        <Button
          onClick={toggleLanguage}
          type="button"
          variant="outline"
          size="sm"
          className="h-10 px-2.5 shrink-0 gap-1.5 font-mono text-xs font-semibold"
          aria-label={language === 'en' ? 'Switch response language to Bengali' : 'Switch response language to English'}
          title={language === 'en' ? 'Switch response language to Bengali' : 'Switch response language to English'}
        >
          <Globe size={13} className="text-primary shrink-0" aria-hidden="true" />
          <span>{language === 'en' ? 'EN' : 'বাং'}</span>
        </Button>

        <div
          onClick={() => textareaRef.current?.focus()}
          className="relative flex-1 rounded-xl bg-surface-raised/50 border border-border overflow-hidden cursor-text focus-within:ring-2 focus-within:ring-primary focus-within:border-primary transition-all shadow-2xs"
        >
          <textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled}
            aria-label="Clinical inquiry input"
            className="w-full max-h-28 bg-transparent resize-none py-2.5 px-3.5 outline-none text-xs sm:text-sm text-text-primary placeholder:text-text-muted disabled:opacity-50 disabled:cursor-not-allowed leading-relaxed"
            rows={1}
          />
        </div>

        <Button
          onClick={handleSend}
          type="button"
          variant="primary"
          size="sm"
          disabled={!message.trim() || disabled}
          aria-label="Send clinical inquiry"
          className="h-10 w-10 p-0 shrink-0 shadow-xs"
        >
          <Send size={15} aria-hidden="true" />
        </Button>
      </div>

      <div className="flex items-center justify-between px-1 text-[10px] text-text-muted">
        <span className="flex items-center gap-1.5 font-medium">
          <span className="w-1.5 h-1.5 rounded-full bg-success"></span>
          Clinical Knowledge RAG Active
        </span>
        <span className="hidden sm:inline font-mono">
          Press Enter to send · Shift+Enter for newline
        </span>
      </div>
    </div>
  );
};
