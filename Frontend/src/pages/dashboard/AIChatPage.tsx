import { useState, useRef, useEffect } from 'react';
import { ChatPanel, ChatMessage } from '@/features/chat';
import { streamKnowledgeChat } from '@/api/services/chatService';
import type { StreamStatusEvent, StreamErrorEvent } from '@/types';
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
  const [currentStatus, setCurrentStatus] = useState<StreamStatusEvent | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsLoading(false);
    setCurrentStatus(null);
  };

  const handleSend = async (content: string) => {
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
    setCurrentStatus({ stage: 'starting', message: 'Initiating medical query validation…' });

    try {
      await streamKnowledgeChat(
        {
          message: content,
          conversation_id: conversationId,
          language,
        },
        {
          onStatus: (status) => {
            setCurrentStatus(status);
          },
          onSources: (_sourcesData) => {
            // Do not render references before text generation finishes
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
            const rawCitations = doneData.citations || doneData.sources || [];
            const formattedSources = rawCitations
              .map((c: any) => {
                const rawUrl = (c.source_url || c.url || '').trim();
                // User requirement: citation MUST be clickable with a valid external URL
                if (!rawUrl || (!rawUrl.startsWith('http://') && !rawUrl.startsWith('https://'))) {
                  return null;
                }
                const book = (c.source_title || c.title || '').trim();
                const section = (c.document_title || c.topic || '').trim();
                if (
                  !book ||
                  [
                    'histopathology',
                    'lung cancer',
                    'colon cancer',
                    'general oncology',
                    'clinical reference',
                    'medical literature',
                    'histopathological concepts',
                    'lung pathology',
                    'colon pathology',
                  ].includes(book.toLowerCase())
                ) {
                  return null;
                }
                const urlPart = ` / ${rawUrl}`;
                const citation =
                  c.citation_display ||
                  (book && section && book.toLowerCase() !== section.toLowerCase()
                    ? `{ ${book}, ${section}${urlPart} }`
                    : `{ ${book || section}${urlPart} }`);
                return {
                  source_id: c.source_id,
                  title: book,
                  document_title: section,
                  url: rawUrl,
                  source: c.document_id,
                  citation,
                };
              })
              .filter(Boolean);

            setMessages((prev) => {
              const existingIdx = prev.findIndex((m) => m.id === assistantMsgId);
              if (existingIdx >= 0) {
                const updated = [...prev];
                updated[existingIdx] = {
                  ...updated[existingIdx],
                  sources: formattedSources.length > 0 ? formattedSources : undefined,
                  isLiveStream: false,
                };
                return updated;
              }
              return prev;
            });
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
              const errText = err.message || 'An error occurred during response generation.';
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
          error?.message || 'The clinical knowledge assistant encountered an error. Please retry.';
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

  return (
    <div className="h-[calc(100vh-8rem)] min-h-[540px] w-full max-w-5xl mx-auto flex flex-col pb-2">
      <ChatPanel
        messages={messages}
        onSend={handleSend}
        isLoading={isLoading}
        currentStatus={currentStatus}
        onStop={handleStop}
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
