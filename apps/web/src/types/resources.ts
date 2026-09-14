export type VehicleType = 'MOTO' | 'VAN_COMPACT' | 'CARGO_VAN' | 'LIGHT_TRUCK'
export type VehicleOwnershipType = 'OWNED' | 'AGGREGATED'
export type VehicleStatus = 'AVAILABLE' | 'UNAVAILABLE' | 'MAINTENANCE' | 'INACTIVE'
export type HelperPolicy = 'FORBIDDEN' | 'OPTIONAL' | 'REQUIRED'
export type FuelType = 'GASOLINE' | 'ETHANOL' | 'DIESEL' | 'FLEX' | 'OTHER'
export type WorkerRole = 'DRIVER' | 'HELPER' | 'MOTORCYCLE_COURIER'
export type WorkerEngagementType = 'EMPLOYEE' | 'DAY_WORKER' | 'AGGREGATED'
export type CompensationModel =
  | 'HOURLY'
  | 'DAILY'
  | 'PER_ROUTE'
  | 'INCLUDED_IN_VEHICLE_CONTRACT'

export interface MaintenanceItem {
  id: string
  name: string
  cost_brl: string
  interval_km: string
  active: boolean
  cost_per_km: string
}

export interface VehicleCost {
  ownership_type: VehicleOwnershipType
  depreciation_per_km: string | null
  maintenance_per_km: string | null
  fixed_cost_per_hour: string | null
  contract_price_brl: string | null
  pricing_model: 'PER_ROUTE' | null
  fuel_included: boolean
  driver_included: boolean
  helper_included: boolean
  maintenance_items: MaintenanceItem[]
}

export interface Vehicle {
  id: string
  plate: string
  type: VehicleType
  ownership_type: VehicleOwnershipType
  max_payload_kg: string
  max_volume_m3: string
  max_range_km: string
  refrigerated: boolean
  status: VehicleStatus
  helper_policy: HelperPolicy
  fuel_type: FuelType | null
  fuel_efficiency_km_per_l: string | null
  active: boolean
  cost: VehicleCost
  created_at: string
  updated_at: string
}

export interface OwnedVehicleCostInput {
  acquisition_value_brl: string
  residual_value_brl: string
  useful_life_km: string
  annual_ipva_brl: string
  annual_insurance_brl: string
  annual_fixed_costs_brl: string
  expected_productive_hours_per_year: string
  maintenance_items: Array<{
    name: string
    cost_brl: string
    interval_km: string
    active?: boolean
  }>
}

export interface AggregatedVehicleContractInput {
  price_brl: string
  pricing_model?: 'PER_ROUTE'
  fuel_included: boolean
  driver_included: boolean
  helper_included: boolean
}

export interface VehicleCreateInput {
  plate: string
  type: VehicleType
  ownership_type: VehicleOwnershipType
  max_payload_kg: string
  max_volume_m3: string
  max_range_km: string
  refrigerated: boolean
  status?: VehicleStatus
  helper_policy: HelperPolicy
  fuel_type?: FuelType | null
  fuel_efficiency_km_per_l?: string | null
  owned_cost?: OwnedVehicleCostInput | null
  aggregated_contract?: AggregatedVehicleContractInput | null
}

export interface Worker {
  id: string
  name: string
  role: WorkerRole
  engagement_type: WorkerEngagementType
  compensation_model: CompensationModel
  compensation_value_brl: string
  active: boolean
  created_at: string
  updated_at: string
}

export interface WorkerCreateInput {
  name: string
  role: WorkerRole
  engagement_type: WorkerEngagementType
  compensation_model: CompensationModel
  compensation_value_brl: string
}

export interface WorkerAvailability {
  worker_id: string
  date: string
  available: boolean
  notes: string | null
}

export interface OperationResources {
  operation_id: string
  operation_date: string
  selected_vehicle_ids: string[]
  selected_worker_ids: string[]
  unavailable_worker_ids: string[]
  vehicles: Vehicle[]
  workers: Worker[]
}
