export type OperationStatus =
  | 'DRAFT'
  | 'READY'
  | 'OPTIMIZING'
  | 'OPTIMIZED'
  | 'OUTDATED'
  | 'APPROVED'
  | 'DISPATCHED'

export type TrafficMode = 'AUTOMATIC' | 'FREE' | 'CUSTOM'

export interface Operation {
  id: string
  operation_code: string
  operation_date: string
  operation_start_time: string
  operation_end_time: string
  traffic_mode: TrafficMode
  status: OperationStatus
  current_revision_number: number
  city_name: string
  created_by_user_id: string
  created_at: string
  updated_at: string
}

export interface OperationListResponse {
  items: Operation[]
  page: number
  page_size: number
  total: number
  total_pages: number
}

export interface OperationCreateInput {
  operation_date: string
  operation_start_time: string
  operation_end_time: string
  traffic_mode: TrafficMode
}

export type OperationUpdateInput = Partial<OperationCreateInput>
