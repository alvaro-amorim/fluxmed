import type {
  Delivery,
  DeliveryCreateInput,
  DeliveryFilters,
  DeliveryImport,
  DeliveryListResponse,
  ScenarioRequest,
  ScenarioResponse,
} from '../types/deliveries'
import { apiRequest } from './api'

export function listDeliveries(filters: DeliveryFilters = {}): Promise<DeliveryListResponse> {
  const params = new URLSearchParams()
  if (filters.operation_id) params.set('operation_id', filters.operation_id)
  if (filters.priority) params.set('priority', filters.priority)
  if (filters.temperature_class) params.set('temperature_class', filters.temperature_class)
  if (filters.status) params.set('status', filters.status)
  if (filters.q?.trim()) params.set('q', filters.q.trim())
  const query = params.toString()
  return apiRequest<DeliveryListResponse>(`/api/v1/deliveries${query ? `?${query}` : ''}`)
}

export function getDelivery(deliveryId: string): Promise<Delivery> {
  return apiRequest<Delivery>(`/api/v1/deliveries/${deliveryId}`)
}

export function createDelivery(
  operationId: string,
  payload: DeliveryCreateInput,
): Promise<Delivery> {
  return apiRequest<Delivery>(`/api/v1/operations/${operationId}/deliveries`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function deleteDelivery(operationId: string, deliveryId: string): Promise<void> {
  return apiRequest<void>(`/api/v1/operations/${operationId}/deliveries/${deliveryId}`, {
    method: 'DELETE',
  })
}

export function generateScenario(
  operationId: string,
  payload: ScenarioRequest,
): Promise<ScenarioResponse> {
  return apiRequest<ScenarioResponse>(`/api/v1/operations/${operationId}/generate-scenario`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function createDeliveryImport(operationId: string, file: File): Promise<DeliveryImport> {
  const formData = new FormData()
  formData.set('file', file)
  return apiRequest<DeliveryImport>(`/api/v1/operations/${operationId}/delivery-imports`, {
    method: 'POST',
    body: formData,
  })
}

export function confirmDeliveryImport(importId: string): Promise<DeliveryImport> {
  return apiRequest<DeliveryImport>(`/api/v1/delivery-imports/${importId}/confirm`, {
    method: 'POST',
  })
}
