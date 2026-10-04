import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { ChatPanel, ChatMessage } from '@/features/chat';
import { sendPredictionChat, generatePredictionSummary } from '@/api/services/chatService';
import { usePredictionHistoryDetail } from '@/hooks/queries/usePredictionHistory';
import { ROUTES } from '@/constants/routes';
import { toast } from 'sonner';

const CASE_SUGGESTIONS = [
  'Explain the ensemble consensus and confidence for this slide evaluation',
  'What histological criteria characterize this predicted tissue class?',
  'Which model architectures agreed or diverged during inference?',
  'What are the recommended clinical correlation steps for this finding?',
];

export default function PredictionChatPage() {
  const { predictionId } = useParams<{ predictionId: string }>();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<string | undefined>();
  const [language, setLanguage] = useState<'en' | 'bn'>('en');
  const [isLoading, setIsLoading] = useState(false);
  const [hasFetchedSummary, setHasFetchedSummary] = useState(false);

  // Fetch underlying case evaluation record for context strip
  const { data: record } = usePredictionHistoryDetail(predictionId);

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
        toast.error('Failed to generate initial case summary.');
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
      const errText = error?.message || 'Case discussion assistant encountered an error. Please retry.';
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

  const caseContext = {
    caseId: predictionId,
    predictedClass: record?.predicted_class,
    confidence: record?.confidence,
    agreementRatio: record?.agreement_ratio,
    imageFilename: record?.image_metadata?.filename,
    status: record?.status,
  };

  return (
    <div className="h-[calc(100vh-8rem)] min-h-[540px] w-full max-w-5xl mx-auto flex flex-col pb-2">
      <ChatPanel
        messages={messages}
        onSend={handleSend}
        isLoading={isLoading}
        title={predictionId ? `Case Discussion: #${predictionId.slice(0, 8)}` : 'Case Discussion'}
        subtitle="Report-scoped discussion grounded in computational pathology evaluation"
        language={language}
        onLanguageChange={setLanguage}
        mode="case_discussion"
        caseContext={caseContext}
        backUrl={predictionId ? `${ROUTES.HISTORY}/${predictionId}` : ROUTES.HISTORY}
        suggestions={CASE_SUGGESTIONS}
      />
    </div>
  );
}
