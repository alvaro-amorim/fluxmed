export type DeliveryPriority = 'CRITICAL' | 'HIGH' | 'NORMAL' | 'LOW'
export type TimeWindowPolicy = 'HARD' | 'SOFT'
export type TemperatureClass = 'AMBIENT' | 'REFRIGERATED'
export type HandlingRequirement = 'STANDARD' | 'TWO_PERSON'
export type ServiceTimeSource = 'ESTIMATED' | 'MANUAL' | 'IMPORTED'
export type DeliveryStatus =
  | 'PENDING'
  | 'PLANNED'
  | 'LOADED'
  | 'DISPATCHED'
  | 'IN_TRANSIT'
  | 'DELIVERED'
  | 'FAILED'

export type CargoProfile =
  | 'MEDICATION_SMALL'
  | 'REFRIGERATED_MEDICATION'
  | 'LAB_MATERIAL'
  | 'HOSPITAL_SUPPLIES'
  | 'BULK_CONSUMABLES'
  | 'MEDICAL_EQUIPMENT'

export type ScenarioProfile = 'NORMAL' | 'BUSY' | 'HIGH_PRESSURE' | 'EMERGENCY'

export interface Delivery {
  id: string
  delivery_code: string
  operation_id: string
  invoice_number: string
  invoice_series: string
  issuer_document: string
  issuer_name: string | null
  external_reference: string | null
  destination_address_id: string
  destination_address: string
  district_name: string
  recipient_name: string
  package_count: number
  total_weight_kg: string
  total_volume_m3: string
  priority: DeliveryPriority
  time_window_start: string | null
  time_window_end: string | null
  time_window_policy: TimeWindowPolicy
  service_time_minutes: number
  service_time_source: ServiceTimeSource
  temperature_class: TemperatureClass
  handling_requirement: HandlingRequirement
  status: DeliveryStatus
  cargo_profile: CargoProfile | null
  notes: string | null
  created_at: string
  updated_at: string
}

export interface DeliveryListResponse {
  items: Delivery[]
  page: number
  page_size: number
  total: number
  total_pages: number
}

export interface DeliveryCreateInput {
  invoice_number: string
  invoice_series: string
  issuer_document: string
  issuer_name?: string | null
  external_reference?: string | null
  recipient_name: string
  destination_address_id: string
  package_count: number
  total_weight_kg: string
  total_volume_m3: string
  priority: DeliveryPriority
  time_window_start?: string | null
  time_window_end?: string | null
  time_window_policy: TimeWindowPolicy
  temperature_class: TemperatureClass
  handling_requirement: HandlingRequirement
  service_time_minutes?: number | null
  notes?: string | null
}

export type DeliveryUpdateInput = Partial<DeliveryCreateInput>

export interface DeliveryFilters {
  operation_id?: string
  priority?: DeliveryPriority
  temperature_class?: TemperatureClass
  status?: DeliveryStatus
  q?: string
}

export interface ScenarioRequest {
  profile: ScenarioProfile
  delivery_count: number
  random_seed?: number
}

export interface ScenarioResponse {
  seed: number
  summary: {
    generated_count: number
    critical_count: number
    refrigerated_count: number
    hard_window_count: number
    total_weight_kg: string
    total_volume_m3: string
  }
  validation: {
    status: string
    message: string
  }
  deliveries: Delivery[]
}

export interface DeliveryImportRow {
  row_number: number
  status: 'VALID' | 'WARNING' | 'ERROR'
  normalized: Record<string, unknown>
  errors: Array<{ code: string; message: string }>
  warnings: Array<{ code: string; message: string }>
}

export interface DeliveryImport {
  id: string
  operation_id: string
  filename: string
  file_type: string
  status: string
  summary: {
    total_rows: number
    valid_rows: number
    warning_rows: number
    error_rows: number
  }
  rows: DeliveryImportRow[]
  created_at: string
  confirmed_at: string | null
}
