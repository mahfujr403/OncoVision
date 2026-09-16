import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { ChatPanel, ChatMessage } from '@/features/chat';
import { sendPredictionChat, generatePredictionSummary } from '@/api/services/chatService';
import { toast } from 'sonner';

export default function PredictionChatPage() {
  const { predictionId } = useParams<{ predictionId: string }>();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<string | undefined>();
  const [language, setLanguage] = useState<'en' | 'bn'>('en');
  const [isLoading, setIsLoading] = useState(false);
  const [hasFetchedSummary, setHasFetchedSummary] = useState(false);

  useEffect(() => {
    if (!predictionId || hasFetchedSummary) return;

    const fetchSummary = async () => {
      try {
        setIsLoading(true);
        const response = await generatePredictionSummary(predictionId, { language });
        
        const summaryMessage: ChatMessage = {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: response.summary_text,
          created_at: new Date().toISOString(),
        };
        
        setMessages([summaryMessage]);
        setHasFetchedSummary(true);
      } catch (error) {
        toast.error('Failed to generate summary.');
      } finally {
        setIsLoading(false);
      }
    };

    fetchSummary();
  }, [predictionId, language, hasFetchedSummary]);

  const handleSend = async (content: string) => {
    if (!predictionId) return;

    try {
      const userMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'user',
        content,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMessage]);
      setIsLoading(true);

      const response = await sendPredictionChat(predictionId, {
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
      const errText = error?.message || 'Sorry, I encountered an error. Please try again.';
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
    <div className="h-full flex-1 w-full max-w-5xl mx-auto flex flex-col p-4 md:p-6">
      <ChatPanel
        messages={messages}
        onSend={handleSend}
        isLoading={isLoading}
        title="Prediction Discussion"
        subtitle={`Prediction ID: ${predictionId}`}
        language={language}
        onLanguageChange={setLanguage}
      />
    </div>
  );
}
