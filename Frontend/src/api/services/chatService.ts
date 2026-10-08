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

async function executeSSEChatStream(
  endpointPath: string,
  request: ChatMessageRequest,
  callbacks: ChatStreamCallbacks,
  signal?: AbortSignal,
): Promise<void> {
  const url = `${API_BASE_URL}${endpointPath}`;
  const token = getAccessToken();

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
