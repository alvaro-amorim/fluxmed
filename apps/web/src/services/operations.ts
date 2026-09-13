import { apiRequest } from './api'
import type {
  Operation,
  OperationCreateInput,
  OperationListResponse,
  OperationUpdateInput,
} from '../types/operations'

export function listOperations(): Promise<OperationListResponse> {
  return apiRequest<OperationListResponse>('/api/v1/operations')
}

export function getOperation(operationId: string): Promise<Operation> {
  return apiRequest<Operation>(`/api/v1/operations/${operationId}`)
}

export function createOperation(payload: OperationCreateInput): Promise<Operation> {
  return apiRequest<Operation>('/api/v1/operations', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateOperation(
  operationId: string,
  payload: OperationUpdateInput,
): Promise<Operation> {
  return apiRequest<Operation>(`/api/v1/operations/${operationId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}
