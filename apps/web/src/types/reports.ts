export type ReportFormat = 'PDF' | 'XLSX' | 'CSV'
export type ReportStatus = 'QUEUED' | 'COMPLETED' | 'FAILED'

export interface ReportItem {
  id: string
  operation_id: string
  optimization_run_id: string
  report_type: 'DAILY_OPERATION'
  format: ReportFormat
  status: ReportStatus
  filename: string | null
  content_type: string | null
  error_message: string | null
  created_at: string
  completed_at: string | null
  download_url: string | null
}

export interface ReportListResponse {
  items: ReportItem[]
}
