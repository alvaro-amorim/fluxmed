import type {
  RoadOverride,
  RoadOverrideType,
  RoutePreview,
  RoutingAlgorithm,
  TrafficLevel,
} from '../types/routing'
import { apiRequest } from './api'

export function previewOperationRoute(
  operationId: string,
  destinationAddressId: string,
  options?: { departureTime?: string; algorithm?: RoutingAlgorithm },
): Promise<RoutePreview> {
  return apiRequest<RoutePreview>(`/api/v1/operations/${operationId}/route-preview`, {
    method: 'POST',
    body: JSON.stringify({
      destination_address_id: destinationAddressId,
      departure_time: options?.departureTime,
      algorithm: options?.algorithm ?? 'ASTAR',
    }),
  })
}

export function listRoadOverrides(operationId: string): Promise<RoadOverride[]> {
  return apiRequest<RoadOverride[]>(`/api/v1/operations/${operationId}/road-overrides`)
}

export function createRoadOverride(
  operationId: string,
  input: {
    road_segment_id: string
    override_type: RoadOverrideType
    traffic_level?: TrafficLevel
    reason: string
    notes?: string
  },
): Promise<RoadOverride> {
  return apiRequest<RoadOverride>(`/api/v1/operations/${operationId}/road-overrides`, {
    method: 'POST',
    body: JSON.stringify({
      ...input,
      direction_scope: 'SEGMENT_DIRECTION',
    }),
  })
}

export function deleteRoadOverride(operationId: string, overrideId: string): Promise<void> {
  return apiRequest<void>(
    `/api/v1/operations/${operationId}/road-overrides/${overrideId}`,
    { method: 'DELETE' },
  )
}
