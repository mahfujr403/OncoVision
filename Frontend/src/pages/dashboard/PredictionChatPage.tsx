import { useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { ChatPanel, ChatMessage } from '@/features/chat';
import { streamPredictionChat, generatePredictionSummary } from '@/api/services/chatService';
import type { StreamStatusEvent, StreamErrorEvent } from '@/types';
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
  const [currentStatus, setCurrentStatus] = useState<StreamStatusEvent | null>(null);
  const [hasFetchedSummary, setHasFetchedSummary] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Fetch underlying case evaluation record for context strip
  const { data: record } = usePredictionHistoryDetail(predictionId);

  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

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
          isLiveStream: false,
        };

        setMessages([summaryMessage]);
        setHasFetchedSummary(true);
      } catch {
        toast.error('Failed to generate initial case summary.');
      } finally {
        setIsLoading(false);
      }
    };

    fetchSummary();
  }, [predictionId, language, hasFetchedSummary]);

  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsLoading(false);
    setCurrentStatus(null);
  };

  const handleSend = async (content: string) => {
    if (!predictionId) return;

    abortControllerRef.current?.abort();
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    };

    const assistantMsgId = crypto.randomUUID();
    let accumulatedContent = '';

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);
    setCurrentStatus({ stage: 'starting', message: 'Validating case context & query…' });

    try {
      await streamPredictionChat(
        predictionId,
        {
          message: content,
          conversation_id: conversationId,
          language,
        },
        {
          onStatus: (status) => {
            setCurrentStatus(status);
          },
          onSources: (sourcesData) => {
            setMessages((prev) => {
              const existingIdx = prev.findIndex((m) => m.id === assistantMsgId);
              if (existingIdx >= 0) {
                const updated = [...prev];
                updated[existingIdx] = {
                  ...updated[existingIdx],
                  sources: sourcesData.sources,
                };
                return updated;
              }
              return [
                ...prev,
                {
                  id: assistantMsgId,
                  role: 'assistant',
                  content: accumulatedContent,
                  sources: sourcesData.sources,
                  created_at: new Date().toISOString(),
                  isLiveStream: true,
                },
              ];
            });
          },
          onDelta: (deltaText) => {
            accumulatedContent += deltaText;
            setMessages((prev) => {
              const existingIdx = prev.findIndex((m) => m.id === assistantMsgId);
              if (existingIdx >= 0) {
                const updated = [...prev];
                updated[existingIdx] = {
                  ...updated[existingIdx],
                  content: accumulatedContent,
                  isLiveStream: true,
                };
                return updated;
              }
              return [
                ...prev,
                {
                  id: assistantMsgId,
                  role: 'assistant',
                  content: accumulatedContent,
                  created_at: new Date().toISOString(),
                  isLiveStream: true,
                },
              ];
            });
          },
          onDone: (doneData) => {
            if (doneData.conversation_id && !conversationId) {
              setConversationId(doneData.conversation_id);
            }
            setCurrentStatus(null);
            setIsLoading(false);
          },
          onError: (err: StreamErrorEvent) => {
            if (err.error_type === 'cancelled') {
              toast.info('Generation cancelled.');
              setMessages((prev) =>
                prev.filter((m) => m.id !== assistantMsgId || m.content.trim().length > 0),
              );
            } else {
              const errText = err.message || 'Case discussion assistant encountered an error.';
              toast.error(errText);
              setMessages((prev) => {
                const existingIdx = prev.findIndex((m) => m.id === assistantMsgId);
                if (existingIdx >= 0) {
                  const updated = [...prev];
                  updated[existingIdx] = {
                    ...updated[existingIdx],
                    content: accumulatedContent
                      ? `${accumulatedContent}\n\n[${errText}]`
                      : errText,
                    isLiveStream: false,
                  };
                  return updated;
                }
                return [
                  ...prev,
                  {
                    id: assistantMsgId,
                    role: 'assistant',
                    content: errText,
                    created_at: new Date().toISOString(),
                    isLiveStream: false,
                  },
                ];
              });
            }
            setCurrentStatus(null);
            setIsLoading(false);
          },
        },
        abortController.signal,
      );
    } catch (error: any) {
      if (error?.name === 'AbortError') {
        toast.info('Generation cancelled.');
      } else {
        const errText =
          error?.message || 'Case discussion assistant encountered an error. Please retry.';
        toast.error(errText);
      }
    } finally {
      setIsLoading(false);
      setCurrentStatus(null);
      if (abortControllerRef.current === abortController) {
        abortControllerRef.current = null;
      }
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
        currentStatus={currentStatus}
        onStop={handleStop}
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
