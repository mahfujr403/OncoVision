import { useState } from 'react';
import { ChatPanel, ChatMessage } from '@/features/chat';
import { sendKnowledgeChat } from '@/api/services/chatService';
import { toast } from 'sonner';

const SUGGESTIONS = [
  'What is lung adenocarcinoma?',
  'কোলন ক্যান্সারের লক্ষণ কি?',
  'How does histopathology classification work?',
  'Tell me about cancer screening methods',
];

export default function AIChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<string | undefined>();
  const [language, setLanguage] = useState<'en' | 'bn'>('en');
  const [isLoading, setIsLoading] = useState(false);

  const handleSend = async (content: string) => {
    try {
      const userMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'user',
        content,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMessage]);
      setIsLoading(true);

      const response = await sendKnowledgeChat({
        message: content,
        conversation_id: conversationId,
        language,
      });

      if (response.conversation_id && !conversationId) {
        setConversationId(response.conversation_id);
      }

      const assistantMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: response.response,
        sources: response.sources,
        created_at: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      toast.error('Failed to send message. Please try again.');
      // Optional: Add error message to chat
      const errorMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="h-full flex-1 w-full max-w-5xl mx-auto flex flex-col p-4 md:p-6">
      <ChatPanel
        messages={messages}
        onSend={handleSend}
        isLoading={isLoading}
        title="AI Cancer Knowledge Assistant"
        subtitle="Ask questions about cancer, histopathology, and OncoVision"
        language={language}
        onLanguageChange={setLanguage}
        suggestions={SUGGESTIONS}
      />
    </div>
  );
}
