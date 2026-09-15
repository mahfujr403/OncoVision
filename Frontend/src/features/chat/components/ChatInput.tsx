import React, { useState, useRef, useEffect } from 'react';
import { Send, Globe } from 'lucide-react';
import { cn } from '@/lib/utils';

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
  placeholder = "Type your message...",
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
    <div className="flex items-end gap-2 p-3 bg-card border-t">
      <button
        onClick={toggleLanguage}
        type="button"
        className="p-2.5 rounded-full bg-secondary text-secondary-foreground hover:bg-secondary/80 transition-colors flex-shrink-0 flex items-center justify-center h-10 w-[60px] text-xs font-semibold"
        title={language === 'en' ? 'Switch to Bengali' : 'Switch to English'}
      >
        <Globe size={14} className="mr-1 hidden sm:block" />
        {language === 'en' ? 'EN' : 'বাং'}
      </button>
      
      <div className="relative flex-1 rounded-2xl bg-muted border overflow-hidden focus-within:ring-1 focus-within:ring-primary focus-within:border-primary transition-all">
        <textarea
          ref={textareaRef}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          className="w-full max-h-24 bg-transparent resize-none py-3 px-4 outline-none text-sm disabled:opacity-50"
          rows={1}
        />
      </div>

      <button
        onClick={handleSend}
        type="button"
        disabled={!message.trim() || disabled}
        className="p-2.5 rounded-full bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex-shrink-0 h-10 w-10 flex items-center justify-center"
      >
        <Send size={18} />
      </button>
    </div>
  );
};
