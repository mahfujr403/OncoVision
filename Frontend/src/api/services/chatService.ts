import { axiosInstance, unwrap } from '@/api';
import { API_ENDPOINTS } from '@/constants/api';
import type { ApiEnvelope, ChatMessageRequest, ChatMessageResponse, ChatHistoryResponse, SummaryRequest, SummaryResponse } from '@/types';

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
