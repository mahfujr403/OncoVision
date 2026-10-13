import { axiosInstance, unwrap, getAccessToken } from '@/api';
import { API_BASE_URL, API_ENDPOINTS } from '@/constants/api';
import { parseSSEStream, ParsedSSEEvent } from '@/lib/sseParser';
import type {
  ApiEnvelope,
  ChatMessageRequest,
  ChatMessageResponse,
  ChatHistoryResponse,
  SummaryRequest,
  SummaryResponse,
  ChatStreamCallbacks,
  StreamStatusEvent,
  StreamSourcesEvent,
  StreamDoneEvent,
  StreamErrorEvent,
} from '@/types';

export async function sendPredictionChat(
  predictionId: string,
  request: ChatMessageRequest,
): Promise<ChatMessageResponse> {
  const response = await axiosInstance.post<ApiEnvelope<ChatMessageResponse>>(
    API_ENDPOINTS.CHAT.PREDICTION(predictionId),
    request,
  );
  return unwrap(response.data);
}

export async function sendKnowledgeChat(
  request: ChatMessageRequest,
): Promise<ChatMessageResponse> {
  const response = await axiosInstance.post<ApiEnvelope<ChatMessageResponse>>(
    API_ENDPOINTS.CHAT.KNOWLEDGE,
    request,
  );
  return unwrap(response.data);
}

async function streamSimulatedResponse(
  request: ChatMessageRequest,
  callbacks: ChatStreamCallbacks,
  signal?: AbortSignal,
): Promise<void> {
  const lowerMsg = (request.message || '').toLowerCase().trim();

  // 1. Developer & creator queries
  const isDevQuery =
    /mahfuj|mahfujur/i.test(lowerMsg) ||
    /(?:who|whom|who's|by whom)\s+(?:developed|created|built|build|designed|authored|made)\s*(?:you|u|this|oncovision|the\s+platform|the\s+system|the\s+app)?/i.test(lowerMsg) ||
    /(?:you\s+(?:are\s+)?(?:developed|created|built|made|authored)\s+by\s+whom)/i.test(lowerMsg) ||
    /(?:who\s+(?:are\s+you|built\s+you|build\s+you|made\s+you|created\s+you|developed\s+you))/i.test(lowerMsg) ||
    /(?:who\s+is\s+(?:your\s+)?(?:developer|creator|author|builder|architect|engineer|maker))/i.test(lowerMsg) ||
    /tell\s+me\s+about\s+(?:the\s+)?(?:developer|creator|author|mahfuj)/i.test(lowerMsg) ||
    /(?:কে\s+(?:বানিয়েছে|বানাইছে|তৈরি\s+করেছে|ডেভেলপ\s+করেছে)|মাহফুজুর\s+রহমান)/i.test(lowerMsg);

  if (isDevQuery) {
    callbacks.onStatus?.({ stage: 'retrieving', message: 'Retrieving verified developer & system information…' });
    await new Promise((r) => setTimeout(r, 180));

    const devChunks = [
      '**OncoVision AI** was designed and developed by **Md. Mahfujur Rahman**, a Machine Learning Engineer and AI Researcher specializing in deep learning, computer vision, and biomedical informatics.\n\n',
      'He engineered the end-to-end multi-model ensemble histopathology classification architecture (achieving 99.97%–99.99% accuracy across high-confidence slides), asynchronous clinical decision support backend, and interactive evidence dashboard.\n\n',
      '**Developer & Project Resources:**\n',
      '- **Portfolio:** [https://md-mahfujur-rahman.vercel.app/](https://md-mahfujur-rahman.vercel.app/)\n',
      '- **GitHub:** [https://github.com/mahfujr403](https://github.com/mahfujr403)\n',
      '- **Google Scholar:** [Md. Mahfujur Rahman](https://scholar.google.com/citations?user=ssuw-WEAAAAJ&hl=en)\n',
      '- **Email:** [mailto:mahfujr403@gmail.com](mailto:mahfujr403@gmail.com)\n\n',
      '> 💡 *Notice: Currently operating in local offline preview mode.*',
    ];

    for (const chunk of devChunks) {
      if (signal?.aborted) return;
      callbacks.onDelta?.(chunk);
      await new Promise((r) => setTimeout(r, 35));
    }

    callbacks.onDone?.({
      conversation_id: request.conversation_id || 'demo-conv-1',
      message_id: 'demo-msg-1',
      is_grounded: false,
      citations: [],
      sources: [],
      metadata: { latency_ms: 250, model: 'platform-metadata', grounded: false },
    });
    return;
  }

  callbacks.onStatus?.({ stage: 'retrieving', message: 'Querying medical literature & vector index…' });
  await new Promise((r) => setTimeout(r, 220));
  callbacks.onStatus?.({ stage: 'grounding', message: 'Validating clinical citations & evidence…' });
  await new Promise((r) => setTimeout(r, 220));

  const isBengali = /[\u0980-\u09FF]/.test(lowerMsg);
  const isColon = /(?:colon|colorectal|polyp|bowel|কোলন)/i.test(lowerMsg);
  const isSquamous = /(?:squamous|scc|keratin)/i.test(lowerMsg);

  let textChunks: string[] = [];
  let mockSources: any[] = [];

  if (isBengali) {
    mockSources = [
      {
        source_id: 'S1',
        document_id: 'DOC-WHO-TUMOURS-5TH',
        title: 'WHO Classification of Tumours',
        source_title: 'WHO Classification of Tumours',
        topic: 'Thoracic and Digestive System Tumours, 5th Edition',
        document_title: 'Thoracic and Digestive System Tumours, 5th Edition',
        url: 'https://tumourclassification.iarc.who.int/chapters/35',
        source_url: 'https://tumourclassification.iarc.who.int/chapters/35',
        citation:
          '{ WHO Classification of Tumours, Thoracic and Digestive System Tumours, 5th Edition / https://tumourclassification.iarc.who.int/chapters/35 }',
        citation_display:
          '{ WHO Classification of Tumours, Thoracic and Digestive System Tumours, 5th Edition / https://tumourclassification.iarc.who.int/chapters/35 }',
      },
      {
        source_id: 'S2',
        document_id: 'DOC-STATPEARLS-HISTOPATHOLOGY',
        title: 'NCBI StatPearls',
        source_title: 'NCBI StatPearls',
        topic: 'Histopathological Diagnostic Criteria in Carcinoma',
        document_title: 'Histopathological Diagnostic Criteria in Carcinoma',
        url: 'https://www.ncbi.nlm.nih.gov/books/NBK519578/',
        source_url: 'https://www.ncbi.nlm.nih.gov/books/NBK519578/',
        citation:
          '{ NCBI StatPearls, Histopathological Diagnostic Criteria in Carcinoma / https://www.ncbi.nlm.nih.gov/books/NBK519578/ }',
        citation_display:
          '{ NCBI StatPearls, Histopathological Diagnostic Criteria in Carcinoma / https://www.ncbi.nlm.nih.gov/books/NBK519578/ }',
      },
    ];

    textChunks = [
      '### হিস্টোপ্যাথলজিক্যাল বিশ্লেষণ (Histopathological Analysis)\n\n',
      'হেমাটোক্সিলিন ও ইওসিন (H&E) স্টেইনিংয়ের অধীনে কোলন ও ফুসফুসের ক্যান্সারের প্রাথমিক হিস্টোপ্যাথলজিক্যাল বৈশিষ্ট্যসমূহ নিচে উল্লেখ করা হলো:\n\n',
      '#### ১. ফুসফুসের ক্যান্সার (Lung Carcinoma)\n',
      '- **গ্রন্থিময় গঠন (Glandular Architecture)**: অ্যাসিনার (acinar), প্যাপিলারি (papillary) বা সলিড প্যাটার্নে গঠিত ম্যালিগন্যান্ট এপিথেলিয়াল বৃদ্ধি এবং ইন্ট্রাসেলুলার মিউসিন ভ্যাকিউওল।\n',
      '- **নিউক্লিয়ার অ্যাটিপিয়া (Nuclear Atypia)**: নিউক্লিয়ার প্লিওমরফিজম (Pleomorphism), হাইপারক্রোমাটিক নিউক্লিয়াস এবং আক্রমণাত্মক প্রান্তে উচ্চ মাইটোটিক ইনডেক্স।\n',
      '- **ইমিউনোহিস্টোকেমিস্ট্রি (IHC Markers)**: অ্যাডেনোকার্সিনোমার ক্ষেত্রে **TTF-1** এবং **Napsin A** পজিটিভ; স্কোয়ামাস সেল কার্সিনোমার ক্ষেত্রে **p40 / p63** পজিটিভ।\n\n',
      '#### ২. কোলন ক্যান্সার (Colon Adenocarcinoma)\n',
      '- **ক্রিব্রিফর্ম ও টিউবুলার গঠন (Cribriform Architecture)**: অনিয়মিত গ্রন্থির অস্বাভাবিক বৃদ্ধি, পিঠাপিঠি (back-to-back) সজ্জিত ডিসপ্লাস্টিক কোষ এবং গোবলেট সেলের লক্ষণীয় ঘাটতি।\n',
      '- **ডার্টি নেক্রোসিস (Dirty Necrosis)**: ম্যালিগন্যান্ট গ্রন্থির লুমেনে কোষীয় ধ্বংসাবশেষ (cellular debris) ও অ্যাপোপটোটিক উপাদানের উপস্থিতি।\n',
      '- **ইমিউনোহিস্টোকেমিস্ট্রি (IHC Markers)**: সাধারণত **CK20** এবং **CDX2** পজিটিভ, কিন্তু CK7 নেগেটিভ।\n\n',
      'চূড়ান্ত রোগ নির্ণয়ের জন্য হিস্টোপ্যাথলজিক্যাল টিস্যু সেকশন ও উপযুক্ত IHC মার্কার পরীক্ষা করা নির্দেশিত।\n\n',
      '> 💡 *Notice: Currently operating in local offline preview mode.*',
    ];
  } else if (isColon) {
    mockSources = [
      {
        source_id: 'S1',
        document_id: 'DOC-WHO-DIGESTIVE-5TH',
        title: 'WHO Classification of Tumours',
        source_title: 'WHO Classification of Tumours',
        topic: 'Digestive System Tumours, 5th Edition, Page 160-164',
        document_title: 'Digestive System Tumours, 5th Edition, Page 160-164',
        url: 'https://tumourclassification.iarc.who.int/chapters/35',
        source_url: 'https://tumourclassification.iarc.who.int/chapters/35',
        citation:
          '{ WHO Classification of Tumours, Digestive System Tumours, 5th Edition, Page 160-164 / https://tumourclassification.iarc.who.int/chapters/35 }',
        citation_display:
          '{ WHO Classification of Tumours, Digestive System Tumours, 5th Edition, Page 160-164 / https://tumourclassification.iarc.who.int/chapters/35 }',
      },
      {
        source_id: 'S2',
        document_id: 'DOC-STATPEARLS-COLON-ADENO',
        title: 'NCBI StatPearls',
        source_title: 'NCBI StatPearls',
        topic: 'Colon Adenocarcinoma Histopathology and Staging',
        document_title: 'Colon Adenocarcinoma Histopathology and Staging',
        url: 'https://www.ncbi.nlm.nih.gov/books/NBK519578/',
        source_url: 'https://www.ncbi.nlm.nih.gov/books/NBK519578/',
        citation:
          '{ NCBI StatPearls, Colon Adenocarcinoma Histopathology and Staging / https://www.ncbi.nlm.nih.gov/books/NBK519578/ }',
        citation_display:
          '{ NCBI StatPearls, Colon Adenocarcinoma Histopathology and Staging / https://www.ncbi.nlm.nih.gov/books/NBK519578/ }',
      },
    ];

    textChunks = [
      '### Histopathological Analysis — Colorectal Adenocarcinoma\n\n',
      'Colorectal adenocarcinoma displays distinct microscopic morphological hallmarks under routine hematoxylin and eosin (H&E) evaluation:\n\n',
      '- **Glandular Dysplasia & Architecture**: Irregular, crowded, and branching glands arranged back-to-back with marked cribriform or fused architectural patterns.\n',
      '- **Dirty Necrosis**: Prominent luminal eosinophilic debris composed of necrotic cellular breakdown and apoptotic bodies within malignant tubules.\n',
      '- **Cytological Features**: Stratified, hyperchromatic, elongated nuclei with loss of normal mucin-producing goblet cells and marked mitotic activity.\n',
      '- **Immunohistochemical Profile**: Characteristically **CK20 positive (+)** and **CDX2 positive (+)**, with negative CK7 staining.\n\n',
      'Definitive clinical evaluation confirms invasive adenocarcinoma with enteric differentiation.\n\n',
      '> 💡 *Notice: Currently operating in local offline preview mode.*',
    ];
  } else if (isSquamous) {
    mockSources = [
      {
        source_id: 'S1',
        document_id: 'DOC-WHO-THORACIC-SCC',
        title: 'WHO Classification of Tumours',
        source_title: 'WHO Classification of Tumours',
        topic: 'Thoracic Tumours: Squamous Cell Carcinoma, Page 58-62',
        document_title: 'Thoracic Tumours: Squamous Cell Carcinoma, Page 58-62',
        url: 'https://tumourclassification.iarc.who.int/chapters/35',
        source_url: 'https://tumourclassification.iarc.who.int/chapters/35',
        citation:
          '{ WHO Classification of Tumours, Thoracic Tumours: Squamous Cell Carcinoma, Page 58-62 / https://tumourclassification.iarc.who.int/chapters/35 }',
        citation_display:
          '{ WHO Classification of Tumours, Thoracic Tumours: Squamous Cell Carcinoma, Page 58-62 / https://tumourclassification.iarc.who.int/chapters/35 }',
      },
    ];

    textChunks = [
      '### Histopathological Analysis — Squamous Cell Carcinoma\n\n',
      'Squamous cell carcinoma demonstrates specific diagnostic features on H&E histopathology:\n\n',
      '- **Keratinization**: Presence of concentric extracellular squamous pearls (keratin pearls) and individual dyskeratotic cells.\n',
      '- **Intercellular Bridges**: Distinct visible desmosomal cell-to-cell connections between polygonally shaped malignant cells.\n',
      '- **Nuclear Morphology**: Markedly pleomorphic, coarsely clumped chromatin with prominent angulated nucleoli.\n',
      '- **Immunohistochemistry**: Diffusely positive for **p40** and **p63**; negative for TTF-1 and Napsin A.\n\n',
      '> 💡 *Notice: Currently operating in local offline preview mode.*',
    ];
  } else {
    mockSources = [
      {
        source_id: 'S1',
        document_id: 'DOC-STATPEARLS-LUNG-ADENO',
        title: 'NCBI StatPearls',
        source_title: 'NCBI StatPearls',
        topic: 'Lung Adenocarcinoma Histopathology',
        document_title: 'Lung Adenocarcinoma Histopathology',
        url: 'https://www.ncbi.nlm.nih.gov/books/NBK519578/',
        source_url: 'https://www.ncbi.nlm.nih.gov/books/NBK519578/',
        citation:
          '{ NCBI StatPearls, Lung Adenocarcinoma Histopathology / https://www.ncbi.nlm.nih.gov/books/NBK519578/ }',
        citation_display:
          '{ NCBI StatPearls, Lung Adenocarcinoma Histopathology / https://www.ncbi.nlm.nih.gov/books/NBK519578/ }',
      },
      {
        source_id: 'S2',
        document_id: 'DOC-WHO-THORACIC-5TH',
        title: 'WHO Classification of Tumours',
        source_title: 'WHO Classification of Tumours',
        topic: 'Thoracic Tumours, 5th Edition, Page 42-45',
        document_title: 'Thoracic Tumours, 5th Edition, Page 42-45',
        url: 'https://tumourclassification.iarc.who.int/chapters/35',
        source_url: 'https://tumourclassification.iarc.who.int/chapters/35',
        citation:
          '{ WHO Classification of Tumours, Thoracic Tumours, 5th Edition, Page 42-45 / https://tumourclassification.iarc.who.int/chapters/35 }',
        citation_display:
          '{ WHO Classification of Tumours, Thoracic Tumours, 5th Edition, Page 42-45 / https://tumourclassification.iarc.who.int/chapters/35 }',
      },
    ];

    textChunks = [
      '### Histopathological Analysis\n\n',
      'Under hematoxylin and eosin (H&E) staining and immunohistochemical (IHC) profiling, the clinical findings reflect:\n\n',
      '- **Glandular Architecture**: Characterized by acinar, papillary, or solid growth patterns with mucin vacuoles.\n',
      '- **Nuclear Atypia**: Prominent pleomorphic nuclei, hyperchromasia, and elevated mitotic activity along invasive fronts.\n',
      '- **Immunohistochemistry**: Strong **TTF-1** and **Napsin A** expression, with absent p40/p63 staining.\n\n',
      'Consensus diagnostic evaluation indicates invasive carcinoma with glandular differentiation.\n\n',
      '> 💡 *Notice: Currently operating in local offline preview mode.*',
    ];
  }

  for (const chunk of textChunks) {
    if (signal?.aborted) return;
    callbacks.onDelta?.(chunk);
    await new Promise((r) => setTimeout(r, 50));
  }

  callbacks.onDone?.({
    conversation_id: request.conversation_id || 'demo-conv-1',
    message_id: 'demo-msg-1',
    is_grounded: true,
    citations: mockSources,
    metadata: { latency_ms: 450, model: 'oncovision-offline-engine', grounded: true },
  });
}

async function executeSSEChatStream(
  endpointPath: string,
  request: ChatMessageRequest,
  callbacks: ChatStreamCallbacks,
  signal?: AbortSignal,
): Promise<void> {
  const token = getAccessToken();

  // If running in local demo recruiter mode without active backend JWT, stream intelligent simulated response
  if (token && token.startsWith('demo_')) {
    return streamSimulatedResponse(request, callbacks, signal);
  }

  const url = `${API_BASE_URL}${endpointPath}`;
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'Accept': 'text/event-stream',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: JSON.stringify(request),
      signal,
    });

    if (!response.ok) {
      if (
        (response.status === 401 && (!token || token.startsWith('demo_'))) ||
        response.status >= 500
      ) {
        return streamSimulatedResponse(request, callbacks, signal);
      }

      let errPayload: any = {};
      try {
        errPayload = await response.json();
      } catch {
        // Non-JSON payload
      }

      let errorType = 'server_error';
      let message = 'The assistant service encountered an unexpected error.';

      if (response.status === 401) {
        errorType = 'unauthorized';
        message = 'Authentication required. Please log in again.';
      } else if (response.status === 429) {
        errorType = 'quota_exhausted';
        message =
          errPayload.detail ||
          errPayload.message ||
          'Rate limit exceeded. Please wait before asking another question.';
      } else if (response.status === 404) {
        errorType = 'not_found';
        message = errPayload.detail || errPayload.message || 'Resource not found.';
      } else if (response.status === 422) {
        errorType = 'invalid_request';
        message = 'Invalid request parameters.';
      } else if (response.status >= 500) {
        errorType = 'server_error';
        message = 'The medical AI service is currently unavailable. Please try again shortly.';
      }

      callbacks.onError?.({
        error_type: errorType,
        message,
      });
      return;
    }

    if (!response.body) {
      callbacks.onError?.({
        error_type: 'stream_interrupted',
        message: 'No response stream received from the server.',
      });
      return;
    }

    await parseSSEStream(
      response.body,
      (event: ParsedSSEEvent) => {
        try {
          switch (event.event) {
            case 'status': {
              const parsed: StreamStatusEvent = JSON.parse(event.data);
              callbacks.onStatus?.(parsed);
              break;
            }
            case 'sources': {
              const parsed: StreamSourcesEvent = JSON.parse(event.data);
              callbacks.onSources?.(parsed);
              break;
            }
            case 'delta': {
              const parsed = JSON.parse(event.data);
              if (parsed && typeof parsed.text === 'string') {
                callbacks.onDelta?.(parsed.text);
              }
              break;
            }
            case 'done': {
              const parsed: StreamDoneEvent = JSON.parse(event.data);
              callbacks.onDone?.(parsed);
              break;
            }
            case 'error': {
              let parsed: StreamErrorEvent;
              try {
                parsed = JSON.parse(event.data);
              } catch {
                parsed = {
                  error_type: 'server_error',
                  message: 'A generation error occurred on the server.',
                };
              }
              callbacks.onError?.(parsed);
              break;
            }
            default:
              break;
          }
        } catch {
          // Ignore malformed individual chunks safely
        }
      },
      signal,
    );
  } catch (err: any) {
    if (signal?.aborted || err?.name === 'AbortError') {
      callbacks.onError?.({
        error_type: 'cancelled',
        message: 'Generation was cancelled by the user.',
      });
      return;
    }

    // If local backend is offline during development/preview, stream simulated response
    if (
      err?.name === 'TypeError' ||
      err?.message?.includes('Failed to fetch') ||
      err?.message?.includes('NetworkError')
    ) {
      return streamSimulatedResponse(request, callbacks, signal);
    }

    callbacks.onError?.({
      error_type: 'stream_interrupted',
      message: 'Network connection was interrupted during streaming.',
    });
  }
}


export async function streamKnowledgeChat(
  request: ChatMessageRequest,
  callbacks: ChatStreamCallbacks,
  signal?: AbortSignal,
): Promise<void> {
  return executeSSEChatStream(API_ENDPOINTS.CHAT.KNOWLEDGE_STREAM, request, callbacks, signal);
}

export async function streamPredictionChat(
  predictionId: string,
  request: ChatMessageRequest,
  callbacks: ChatStreamCallbacks,
  signal?: AbortSignal,
): Promise<void> {
  return executeSSEChatStream(API_ENDPOINTS.CHAT.PREDICTION_STREAM(predictionId), request, callbacks, signal);
}

export async function getChatHistory(
  conversationId: string,
): Promise<ChatHistoryResponse> {
  const response = await axiosInstance.get<ApiEnvelope<ChatHistoryResponse>>(
    API_ENDPOINTS.CHAT.HISTORY(conversationId),
  );
  return unwrap(response.data);
}

export async function generatePredictionSummary(
  predictionId: string,
  request: SummaryRequest = {},
): Promise<SummaryResponse> {
  const response = await axiosInstance.post<ApiEnvelope<SummaryResponse>>(
    API_ENDPOINTS.SUMMARY.GENERATE(predictionId),
    request,
  );
  return unwrap(response.data);
}

export async function getPredictionSummary(
  predictionId: string,
): Promise<SummaryResponse> {
  const response = await axiosInstance.get<ApiEnvelope<SummaryResponse>>(
    API_ENDPOINTS.SUMMARY.GENERATE(predictionId),
  );
  return unwrap(response.data);
}
