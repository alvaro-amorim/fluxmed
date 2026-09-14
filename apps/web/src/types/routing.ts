export type RoutingAlgorithm = 'DIJKSTRA' | 'ASTAR'
export type TrafficLevel = 'FREE' | 'LIGHT' | 'MODERATE' | 'HEAVY' | 'VERY_HEAVY'
export type RoadOverrideType = 'CLOSURE' | 'TRAFFIC'

export interface RoadOverride {
  id: string
  operation_id: string
  road_segment_id: string
  street_name: string
  override_type: RoadOverrideType
  direction_scope: 'SEGMENT_DIRECTION'
  traffic_level: TrafficLevel | null
  reason: string
  notes: string | null
  is_bridge: boolean
  bridge_name: string | null
}

export interface RoutePreview {
  operation_id: string
  destination_address_id: string
  algorithm: RoutingAlgorithm
  traffic_mode: 'AUTOMATIC' | 'FREE' | 'CUSTOM'
  departure_at: string
  arrival_at: string
  distance_m: number
  travel_time_seconds: number
  time_bucket: string
  edge_ids: string[]
  geometry: {
    type: 'LineString'
    coordinates: number[][]
  }
  cache_hit: boolean
}

export interface RoadSelection {
  road_segment_id: string
  street_name: string
  is_bridge: boolean
  bridge_name: string | null
}
