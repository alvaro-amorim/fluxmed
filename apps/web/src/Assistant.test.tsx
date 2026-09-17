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

function response(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response
}

beforeEach(() => {
  window.history.pushState({}, '', '/assistant')
})

afterEach(() => {
  vi.unstubAllGlobals()
})

it('asks a factual question using the selected operation context and copies the chat history', async () => {
  const writeText = vi.fn(async () => undefined)
  vi.stubGlobal(
    'navigator',
    Object.assign(Object.create(window.navigator), {
      clipboard: { writeText },
    }),
  )
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = typeof input === 'string' ? input : input.toString()
      const method = init?.method ?? 'GET'
      if (path.endsWith('/api/v1/auth/me')) return response(planner)
      if (path.endsWith('/api/v1/operations')) {
        return response({ items: [operation], page: 1, page_size: 20, total: 1, total_pages: 1 })
      }
      if (path.endsWith('/api/v1/assistant/status')) {
        return response({ status: 'HEALTHY', provider: 'mock', model: 'fluxmed-mock-v1' })
      }
      if (path.endsWith('/api/v1/assistant/messages') && method === 'POST') {
        const payload = JSON.parse(String(init?.body)) as {
          message: string
          context: { operation_id: string }
        }
        expect(payload.context.operation_id).toBe(operation.id)
        expect(payload.message).toBe('Qual o custo total da operação?')
        return response({
          request_id: 'request-id',
          message: 'O custo total da OP-20260915-001 é R$ 400,38.',
          provider: 'mock',
          model: 'fluxmed-mock-v1',
          prompt_version: 'assistant-system-v1',
          latency_ms: 2,
          input_tokens: 0,
          output_tokens: 0,
          tool_calls: [{ name: 'get_operation_summary', status: 'success', error: null }],
          suggested_actions: [],
        })
      }
      return response({}, 404)
    }),
  )

  render(<App />)
  const user = userEvent.setup()

  expect(await screen.findByRole('heading', { name: 'Explique o plano com dados validados' })).toBeInTheDocument()
  expect(screen.getByText(/Assistente IA · Configurado/i)).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Copiar histórico' })).toBeDisabled()

  await user.click(screen.getByRole('button', { name: 'Qual o custo total da operação?' }))

  await waitFor(() => {
    expect(screen.getByText('O custo total da OP-20260915-001 é R$ 400,38.')).toBeInTheDocument()
  })
  expect(screen.getByText(/get_operation_summary \(success\)/)).toBeInTheDocument()

  const copyButton = screen.getByRole('button', { name: 'Copiar histórico' })
  expect(copyButton).toBeEnabled()
  await user.click(copyButton)

  await waitFor(() => expect(writeText).toHaveBeenCalledTimes(1))
  const copied = String(writeText.mock.calls[0][0])
  expect(copied).toContain('# FluxMed — Histórico do Assistente IA')
  expect(copied).toContain('**Operação:** OP-20260915-001')
  expect(copied).toContain('## Você')
  expect(copied).toContain('Qual o custo total da operação?')
  expect(copied).toContain('## FluxMed IA')
  expect(copied).toContain('_Provider: mock · fluxmed-mock-v1_')
  expect(copied).toContain('**Fontes estruturadas:** get_operation_summary (success)')
  expect(screen.getByRole('button', { name: 'Copiado' })).toBeInTheDocument()
})

it('disables questions when the provider is degraded', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const path = typeof input === 'string' ? input : input.toString()
      if (path.endsWith('/api/v1/auth/me')) return response(planner)
      if (path.endsWith('/api/v1/operations')) {
        return response({ items: [operation], page: 1, page_size: 20, total: 1, total_pages: 1 })
      }
      if (path.endsWith('/api/v1/assistant/status')) {
        return response({ status: 'DEGRADED', provider: 'cohere', model: 'command-a-plus-05-2026' })
      }
      return response({}, 404)
    }),
  )

  render(<App />)

  expect(await screen.findByText(/temporariamente indisponível/i)).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Qual o custo total da operação?' })).toBeDisabled()
  expect(screen.getByLabelText('Pergunte sobre a operação selecionada')).toBeDisabled()
})
