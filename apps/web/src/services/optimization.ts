import { apiRequest } from './api'
import type {
  OptimizationResult,
  OptimizeAccepted,
  ResultRoute,
  TeamSimulation,
} from '../types/optimization'

export function optimizeOperation(operationId: string, randomSeed?: number): Promise<OptimizeAccepted> {
  return apiRequest<OptimizeAccepted>(`/api/v1/operations/${operationId}/optimize`, {
    method: 'POST',
    body: JSON.stringify({ random_seed: randomSeed }),
  })
}

export function getLatestOptimizationResult(operationId: string): Promise<OptimizationResult> {
  return apiRequest<OptimizationResult>(
    `/api/v1/operations/${operationId}/optimization-runs/latest`,
  )
}

export function getOptimizationResult(runId: string): Promise<OptimizationResult> {
  return apiRequest<OptimizationResult>(`/api/v1/optimization-runs/${runId}/result`)
}

export function getResultRoute(routeId: string): Promise<ResultRoute> {
  return apiRequest<ResultRoute>(`/api/v1/routes/${routeId}`)
}

export function approveOptimizationResult(runId: string): Promise<OptimizationResult> {
  return apiRequest<OptimizationResult>(`/api/v1/optimization-runs/${runId}/approve`, {
    method: 'POST',
  })
}

export function simulateRouteTeam(
  routeId: string,
  primaryWorkerId: string | null,
  helperWorkerId: string | null,
): Promise<TeamSimulation> {
  return apiRequest<TeamSimulation>(`/api/v1/routes/${routeId}/team-simulation`, {
    method: 'POST',
    body: JSON.stringify({
      primary_worker_id: primaryWorkerId,
      helper_worker_id: helperWorkerId,
    }),
  })
}

export function applyRouteTeam(
  routeId: string,
  primaryWorkerId: string | null,
  helperWorkerId: string | null,
): Promise<TeamSimulation> {
  return apiRequest<TeamSimulation>(`/api/v1/routes/${routeId}/team`, {
    method: 'PUT',
    body: JSON.stringify({
      primary_worker_id: primaryWorkerId,
      helper_worker_id: helperWorkerId,
    }),
  })
}
