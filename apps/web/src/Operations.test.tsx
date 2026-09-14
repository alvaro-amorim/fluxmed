import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import App from './App'
import type { Operation, PreflightResponse } from './types/operations'

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

const scenarioDelivery = {
  id: 'delivery-id',
  delivery_code: 'DLV-NF100-001',
  operation_id: operation.id,
  invoice_number: '100',
  invoice_series: '1',
  issuer_document: '123',
  issuer_name: null,
  external_reference: null,
  destination_address_id: 'address-id',
  destination_address: 'Rua Aurora, 10 — Centro Histórico',
  district_name: 'Centro Histórico',
  recipient_name: 'Hospital Aurora',
  package_count: 1,
  total_weight_kg: '10.000',
  total_volume_m3: '0.1000',
  priority: 'NORMAL',
  time_window_start: null,
  time_window_end: null,
  time_window_policy: 'SOFT',
  service_time_minutes: 10,
  service_time_source: 'ESTIMATED',
  temperature_class: 'AMBIENT',
  handling_requirement: 'STANDARD',
  status: 'PENDING',
  cargo_profile: null,
  notes: null,
  created_at: '2026-09-14T10:00:00-03:00',
  updated_at: '2026-09-14T10:00:00-03:00',
} as const

const invalidPreflight: PreflightResponse = {
  status: 'INVALID',
  blocking_errors: [
    {
      code: 'NO_VEHICLES',
      message: 'Selecione ao menos um veículo disponível antes de otimizar.',
      related_delivery_ids: [],
    },
  ],
  warnings: [],
  summary: {
    delivery_count: 1,
    vehicle_count: 0,
    worker_count: 0,
    critical_count: 0,
    refrigerated_count: 0,
    hard_window_count: 0,
    two_person_count: 0,
    total_weight_kg: '10.000',
    total_volume_m3: '0.1000',
    operation_window_minutes: 630,
  },
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
  it('prepares an operation through the wizard and blocks invalid optimization', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = typeof input === 'string' ? input : input.toString()
      const method = init?.method ?? 'GET'
      if (path.endsWith('/auth/me')) return response(planner)
      if (path.endsWith('/api/v1/cities')) return response([])
      if (path.endsWith('/api/v1/operations') && method === 'POST') return response(operation, 201)
      if (path.includes('/api/v1/deliveries?operation_id=operation-id')) {
        return response({ items: [], page: 1, page_size: 20, total: 0, total_pages: 0 })
      }
      if (path.endsWith('/api/v1/operations/operation-id/generate-scenario')) {
        return response({
          seed: 123,
          summary: {
            generated_count: 1,
            critical_count: 0,
            refrigerated_count: 0,
            hard_window_count: 0,
            total_weight_kg: '10',
            total_volume_m3: '0.1',
          },
          validation: { status: 'FEASIBLE', message: 'Cenário válido.' },
          deliveries: [scenarioDelivery],
        })
      }
      if (path.endsWith('/api/v1/operations/operation-id/resources') && method === 'GET') {
        return response({
          operation_id: operation.id,
          operation_date: operation.operation_date,
          selected_vehicle_ids: [],
          selected_worker_ids: [],
          unavailable_worker_ids: [],
          vehicles: [],
          workers: [],
        })
      }
      if (path.endsWith('/api/v1/operations/operation-id/validate') && method === 'POST') {
        return response(invalidPreflight)
      }
      return response({}, 404)
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<App />)
    const user = userEvent.setup()

    expect(await screen.findByRole('heading', { name: 'Nova operação' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Salvar e continuar' }))

    expect(await screen.findByRole('button', { name: 'Gerar cenário' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Gerar cenário' }))
    expect(await screen.findByText(/1 entregas geradas/)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Continuar para recursos' }))
    expect(await screen.findByText('Frota e equipe da operação')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Ir para revisão' }))
    expect(await screen.findByText('Operação com bloqueios')).toBeInTheDocument()
    expect(screen.getByText('NO_VEHICLES')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Otimizar rotas' })).toBeDisabled()
  })
})
