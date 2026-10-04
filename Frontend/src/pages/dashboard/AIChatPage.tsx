import { useState } from 'react';
import { ChatPanel, ChatMessage } from '@/features/chat';
import { sendKnowledgeChat } from '@/api/services/chatService';
import { toast } from 'sonner';

const PATHOLOGY_SUGGESTIONS = [
  'What are the key histopathological characteristics of lung adenocarcinoma?',
  'How does multi-model ensemble consensus operate on H&E slide images?',
  'What morphological features distinguish colon adenocarcinoma from benign tissue?',
  'কোলন ও ফুসফুসের ক্যান্সারের প্রাথমিক হিস্টোপ্যাথলজিক্যাল লক্ষণ কি?',
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
    } catch (error: any) {
      const errText = error?.message || 'The clinical knowledge assistant encountered an error. Please retry.';
      toast.error(errText);
      const errorMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: errText,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="h-[calc(100vh-8rem)] min-h-[540px] w-full max-w-5xl mx-auto flex flex-col pb-2">
      <ChatPanel
        messages={messages}
        onSend={handleSend}
        isLoading={isLoading}
        title="Medical Knowledge & Evidence Assistant"
        subtitle="Explore peer-reviewed pathology concepts, tissue classifications, and ensemble methodology"
        language={language}
        onLanguageChange={setLanguage}
        suggestions={PATHOLOGY_SUGGESTIONS}
        mode="knowledge"
      />
    </div>
  );
}
