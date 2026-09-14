import { apiRequest, apiUrl } from './api'
import type {
  OptimizationResult,
  OptimizationRun,
  OptimizationTraceEvent,
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

export function getLatestOptimizationRun(operationId: string): Promise<OptimizationRun> {
  return apiRequest<OptimizationRun>(
    `/api/v1/operations/${operationId}/optimization-runs/latest-run`,
  )
}

export function getOptimizationRun(runId: string): Promise<OptimizationRun> {
  return apiRequest<OptimizationRun>(`/api/v1/optimization-runs/${runId}`)
}

export function getOptimizationTrace(runId: string): Promise<OptimizationTraceEvent[]> {
  return apiRequest<OptimizationTraceEvent[]>(`/api/v1/optimization-runs/${runId}/trace`)
}

export function cancelOptimizationRun(runId: string): Promise<OptimizationRun> {
  return apiRequest<OptimizationRun>(`/api/v1/optimization-runs/${runId}/cancel`, {
    method: 'POST',
  })
}

const TRACE_EVENT_TYPES = [
  'optimization_started',
  'generation_snapshot',
  'best_solution_updated',
  'pruning_summary',
  'optimization_completed',
  'optimization_failed',
  'optimization_cancelled',
] as const

export function subscribeOptimizationEvents(
  runId: string,
  afterSequence: number,
  onEvent: (event: OptimizationTraceEvent) => void,
  onConnectionError?: () => void,
): () => void {
  const query = afterSequence > 0 ? `?after=${afterSequence}` : ''
  const source = new EventSource(apiUrl(`/api/v1/optimization-runs/${runId}/events${query}`), {
    withCredentials: true,
  })
  const handler = (raw: Event) => {
    const message = raw as MessageEvent<string>
    try {
      onEvent(JSON.parse(message.data) as OptimizationTraceEvent)
    } catch {
      // Ignore malformed frames; persisted replay remains the source of truth.
    }
  }
  TRACE_EVENT_TYPES.forEach((eventType) => source.addEventListener(eventType, handler))
  source.onerror = () => onConnectionError?.()
  return () => source.close()
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
