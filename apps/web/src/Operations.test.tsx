import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import App from './App'
import type { Operation } from './types/operations'

const planner = {
  id: 'planner-id',
  email: 'planner@fluxmed.demo',
  display_name: 'Planejador Demo',
  role: 'PLANNER',
}

const operation: Operation = {
  id: 'operation-id',
  operation_code: 'OP-20260914-001',
  operation_date: '2026-09-14',
  operation_start_time: '07:30:00',
  operation_end_time: '18:00:00',
  traffic_mode: 'AUTOMATIC',
  status: 'DRAFT',
  current_revision_number: 0,
  city_name: 'Santa Aurora',
  created_by_user_id: 'planner-id',
  created_at: '2026-09-13T12:00:00-03:00',
  updated_at: '2026-09-13T12:00:00-03:00',
}

function response(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response
}

beforeEach(() => {
  window.history.pushState({}, '', '/operations/new')
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('operations flow', () => {
  it('creates an operation through the real API contract and opens its detail', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const path = typeof input === 'string' ? input : input.toString()
        const method = init?.method ?? 'GET'
        if (path.endsWith('/auth/me')) return response(planner)
        if (path.endsWith('/api/v1/operations') && method === 'POST') return response(operation, 201)
        if (path.endsWith('/api/v1/operations/operation-id')) return response(operation)
        return response({}, 404)
      }),
    )

    render(<App />)
    const user = userEvent.setup()

    expect(await screen.findByRole('heading', { name: 'Nova operação' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Criar operação' }))

    expect(await screen.findByRole('heading', { name: 'OP-20260914-001' })).toBeInTheDocument()
    expect(screen.getByText('Santa Aurora · planejamento diário')).toBeInTheDocument()
  })
})
