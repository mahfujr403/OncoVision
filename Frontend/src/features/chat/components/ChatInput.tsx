import React, { useState, useRef, useEffect } from 'react';
import { Send, Globe } from 'lucide-react';

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
  placeholder = "Inquire about tissue pathology, tumor classes, or H&E findings...",
  language,
  onLanguageChange,
}) => {
  const [message, setMessage] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const adjustHeight = () => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 96)}px`;
    }
  };

  useEffect(() => {
    adjustHeight();
  }, [message]);

  // Automatically place cursor in the text box on mount and when AI response finishes
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
    <div className="flex flex-col gap-1.5 p-3 bg-card border-t">
      <div className="flex items-end gap-2">
        <button
          onClick={toggleLanguage}
          type="button"
          className="p-2.5 rounded-xl bg-secondary text-secondary-foreground hover:bg-secondary/80 transition-colors flex-shrink-0 flex items-center justify-center h-10 w-[64px] text-xs font-semibold shadow-2xs"
          title={language === 'en' ? 'Switch to Bengali' : 'Switch to English'}
        >
          <Globe size={14} className="mr-1 hidden sm:block text-primary" />
          {language === 'en' ? 'EN' : 'বাং'}
        </button>
        
        <div
          onClick={() => textareaRef.current?.focus()}
          className="relative flex-1 rounded-2xl bg-muted/60 border border-border/80 overflow-hidden cursor-text focus-within:ring-1 focus-within:ring-primary focus-within:border-primary transition-all shadow-2xs"
        >
          <textarea
            ref={textareaRef}
            autoFocus
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled}
            className="w-full max-h-24 bg-transparent resize-none py-2.5 px-4 outline-none text-sm cursor-text disabled:opacity-50 disabled:cursor-not-allowed"
            rows={1}
          />
        </div>

        <button
          onClick={handleSend}
          type="button"
          disabled={!message.trim() || disabled}
          className="p-2.5 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex-shrink-0 h-10 w-10 flex items-center justify-center shadow-xs"
        >
          <Send size={16} />
        </button>
      </div>

      <div className="flex items-center justify-between px-2 text-[10px] text-muted-foreground/60">
        <span className="flex items-center gap-1 font-medium">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
          Clinical Knowledge RAG Active
        </span>
        <span className="hidden sm:inline">Press Enter to send • Shift+Enter for new line</span>
      </div>
    </div>
  );
};

