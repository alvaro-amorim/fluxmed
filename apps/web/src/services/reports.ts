import { ApiClientError, apiRequest, apiUrl } from './api'
import type { ReportFormat, ReportItem, ReportListResponse } from '../types/reports'

export function listReports(operationId?: string): Promise<ReportListResponse> {
  const query = operationId ? `?operation_id=${encodeURIComponent(operationId)}` : ''
  return apiRequest<ReportListResponse>(`/api/v1/reports${query}`)
}

export function createReport(operationId: string, format: ReportFormat): Promise<ReportItem> {
  return apiRequest<ReportItem>(`/api/v1/operations/${operationId}/reports`, {
    method: 'POST',
    body: JSON.stringify({ report_type: 'DAILY_OPERATION', format }),
  })
}

export async function downloadReport(report: ReportItem): Promise<void> {
  const response = await fetch(apiUrl(`/api/v1/reports/${report.id}/download`), {
    credentials: 'include',
  })
  if (!response.ok) {
    throw new ApiClientError(
      response.status,
      'REPORT_DOWNLOAD_FAILED',
      'Não foi possível baixar o relatório.',
    )
  }
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = report.filename ?? `fluxmed_report.${report.format.toLowerCase()}`
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}
