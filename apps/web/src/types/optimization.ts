export interface OptimizeAccepted {
  optimization_run_id: string
  status: string
  result_url: string
  status_url: string
  events_url: string
}

export type OptimizationRunStatus =
  | 'QUEUED'
  | 'RUNNING'
  | 'COMPLETED'
  | 'FAILED'
  | 'CANCELLED'
  | 'INTERRUPTED'

export interface OptimizationRun {
  id: string
  operation_id: string
  status: OptimizationRunStatus
  random_seed: number
  generations_completed: number
  stop_reason: string
  validated: boolean
  error_code: string | null
  error_message: string | null
  latest_sequence: number
  created_at: string
  started_at: string | null
  completed_at: string | null
  cancel_requested_at: string | null
}

export interface LiveDeliveryPoint {
  delivery_id: string
  delivery_code: string
  longitude: number
  latitude: number
  sequence?: number
}

export interface LiveRoute {
  route_code: string
  vehicle_id: string
  delivery_ids: string[]
  distance_km: string
  duration_minutes: string
  geometry: {
    type: 'LineString'
    coordinates: number[][]
  } | null
  stops: LiveDeliveryPoint[]
}

export interface RouteAssignmentChange {
  delivery_id: string
  from_vehicle_id: string
  to_vehicle_id: string
  from_position: number
  to_position: number
}

export interface OptimizationTracePayload {
  status?: string
  random_seed?: number
  delivery_count?: number
  population_size?: number
  max_generations?: number
  deliveries?: LiveDeliveryPoint[]
  generation?: number
  feasible?: boolean
  hard_violations?: number
  service_penalty?: string
  critical_risk?: string
  cost_brl?: string
  makespan_minutes?: string
  travel_minutes?: string
  distance_km?: string
  vehicles_used?: number
  diversity_ratio?: number
  mutation_rate?: number
  immigrants_added?: number
  pruning_counts?: Record<string, number>
  counts?: Record<string, number>
  routes?: LiveRoute[]
  changes?: RouteAssignmentChange[]
  selection_reasons?: Array<Record<string, unknown>>
  stop_reason?: string
  validated?: boolean
  final?: Record<string, unknown> | boolean
  baselines?: Array<Record<string, unknown>>
  error_code?: string
  message?: string
}

export interface OptimizationTraceEvent {
  id: string
  run_id: string
  sequence: number
  event_type: string
  generation: number | null
  elapsed_ms: number | null
  payload: OptimizationTracePayload
  created_at: string
}

export interface ResultWorker {
  id: string
  name: string
  role: string
}

export interface ResultVehicle {
  id: string
  plate: string
  type: string
  ownership_type: string
}

export interface RouteCost {
  depreciation_brl: string
  maintenance_brl: string
  fixed_time_brl: string
  fuel_brl: string
  team_brl: string
  contract_brl: string
  total_brl: string
}

export interface RouteTeam {
  primary_role: string | null
  primary_worker: ResultWorker | null
  helper: ResultWorker | null
  primary_included: boolean
  helper_included: boolean
  team_cost_brl: string
}

export interface ResultStop {
  id: string
  sequence: number
  delivery_id: string
  delivery_code: string
  recipient_name: string
  address_label: string
  priority: string
  longitude: number
  latitude: number
  planned_arrival_at: string | null
  planned_departure_at: string | null
  time_window_start: string | null
  time_window_end: string | null
  time_window_policy: string
  service_time_minutes: number
  lateness_minutes: string
}

export interface ResultRoute {
  id: string
  route_code: string
  vehicle: ResultVehicle
  team: RouteTeam
  delivery_count: number
  distance_km: string
  duration_minutes: string
  total_weight_kg: string
  total_volume_m3: string
  weight_utilization_pct: string
  volume_utilization_pct: string
  cost: RouteCost
  geometry: {
    type: 'LineString'
    coordinates: number[][]
  }
  stops: ResultStop[]
}

export interface OptimizationResult {
  run_id: string
  operation_id: string
  revision_number: number
  status: string
  validated: boolean
  random_seed: number
  generations_completed: number
  stop_reason: string
  delivery_count: number
  vehicles_used: number
  total_cost_brl: string
  distance_km: string
  makespan_minutes: string
  critical_delays: number
  on_time_percentage: string
  average_weight_utilization_pct: string
  average_volume_utilization_pct: string
  pruning_counts: Record<string, number>
  routes: ResultRoute[]
}

export interface TeamSimulation {
  valid: boolean
  route_id: string
  team: RouteTeam | null
  route_cost: RouteCost | null
  issues: string[]
}
