import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'

import App from './App'

const planner = {
  id: 'planner-id',
  email: 'planner@fluxmed.demo',
  display_name: 'Planejador Demo',
  role: 'PLANNER',
}

const operation = {
  id: 'operation-id',
  operation_code: 'OP-20260915-001',
  operation_date: '2026-09-15',
  operation_start_time: '07:30:00',
  operation_end_time: '18:00:00',
  traffic_mode: 'AUTOMATIC',
  status: 'OPTIMIZED',
  current_revision_number: 2,
  city_name: 'Santa Aurora',
  created_by_user_id: 'planner-id',
  created_at: '2026-09-15T10:00:00Z',
  updated_at: '2026-09-15T13:00:00Z',
}

const completedReport = {
  id: 'report-id',
  operation_id: operation.id,
  optimization_run_id: 'run-id-12345678',
  report_type: 'DAILY_OPERATION',
  format: 'PDF',
  status: 'COMPLETED',
  filename: 'fluxmed_OP-20260915-001_report.pdf',
  content_type: 'application/pdf',
  error_message: null,
  created_at: '2026-09-15T14:00:00Z',
  completed_at: '2026-09-15T14:00:01Z',
  download_url: '/api/v1/reports/report-id/download',
}

function response(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response
}

beforeEach(() => {
  window.history.pushState({}, '', '/reports?operation_id=operation-id')
})

afterEach(() => {
  vi.unstubAllGlobals()
})

it('generates a report and shows it in history', async () => {
  let generated = false
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = typeof input === 'string' ? input : input.toString()
      const method = init?.method ?? 'GET'
      if (path.endsWith('/api/v1/auth/me')) return response(planner)
      if (path.endsWith('/api/v1/operations')) {
        return response({ items: [operation], page: 1, page_size: 20, total: 1, total_pages: 1 })
      }
      if (path.endsWith('/api/v1/reports') && method === 'GET') {
        return response({ items: generated ? [completedReport] : [] })
      }
      if (path.endsWith('/api/v1/operations/operation-id/reports') && method === 'POST') {
        generated = true
        return response(completedReport, 202)
      }
      return response({}, 404)
    }),
  )

  render(<App />)
  const user = userEvent.setup()

  expect(await screen.findByRole('heading', { name: 'Artefatos da operação' })).toBeInTheDocument()
  expect(screen.getByText(/snapshot imutável/i)).toBeInTheDocument()

  await user.click(screen.getByRole('button', { name: 'Gerar PDF' }))

  await waitFor(() => {
    expect(screen.getByText('fluxmed_OP-20260915-001_report.pdf')).toBeInTheDocument()
  })
  expect(screen.getByRole('button', { name: 'Baixar' })).toBeEnabled()
})

it('retries a failed report and keeps the same run history entry', async () => {
  let retried = false
  const failedReport = {
    ...completedReport,
    status: 'FAILED',
    filename: null,
    content_type: null,
    error_message: 'falha simulada',
    completed_at: '2026-09-15T14:00:01Z',
    download_url: null,
  }
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = typeof input === 'string' ? input : input.toString()
      const method = init?.method ?? 'GET'
      if (path.endsWith('/api/v1/auth/me')) return response(planner)
      if (path.endsWith('/api/v1/operations')) {
        return response({ items: [operation], page: 1, page_size: 20, total: 1, total_pages: 1 })
      }
      if (path.endsWith('/api/v1/reports') && method === 'GET') {
        return response({ items: [retried ? completedReport : failedReport] })
      }
      if (path.endsWith('/api/v1/reports/report-id/retry') && method === 'POST') {
        retried = true
        return response(completedReport, 202)
      }
      return response({}, 404)
    }),
  )

  render(<App />)
  const user = userEvent.setup()

  expect(await screen.findByText('falha simulada')).toBeInTheDocument()
  const retryButton = screen.getByRole('button', { name: 'Tentar novamente' })
  await user.click(retryButton)

  await waitFor(() => {
    expect(screen.queryByText('falha simulada')).not.toBeInTheDocument()
  })
  expect(screen.getByRole('button', { name: 'Baixar' })).toBeEnabled()
  expect(screen.getByText(/snapshot do run run-id-1/i)).toBeInTheDocument()
})
