export interface OptimizeAccepted {
  optimization_run_id: string
  status: string
  result_url: string
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
