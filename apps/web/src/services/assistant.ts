import { apiRequest } from './api'
import type {
  AssistantMessageInput,
  AssistantMessageResponse,
  AssistantStatus,
} from '../types/assistant'

export function getAssistantStatus(): Promise<AssistantStatus> {
  return apiRequest<AssistantStatus>('/api/v1/assistant/status')
}

export function sendAssistantMessage(
  payload: AssistantMessageInput,
): Promise<AssistantMessageResponse> {
  return apiRequest<AssistantMessageResponse>('/api/v1/assistant/messages', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
