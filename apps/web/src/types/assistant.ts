export interface AssistantContextInput {
  operation_id?: string | null
  route_id?: string | null
  delivery_id?: string | null
}

export interface AssistantMessageInput {
  message: string
  context: AssistantContextInput
}

export interface AssistantToolCall {
  name: string
  status: string
  error: string | null
}

export interface AssistantMessageResponse {
  request_id: string
  message: string
  provider: string
  model: string
  prompt_version: string
  latency_ms: number
  input_tokens: number
  output_tokens: number
  tool_calls: AssistantToolCall[]
  suggested_actions: Array<Record<string, unknown>>
}

export interface AssistantStatus {
  status: 'HEALTHY' | 'DEGRADED'
  provider: string
  model: string
}
