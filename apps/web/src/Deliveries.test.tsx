import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import App from './App'
import type { CitySummary } from './types/city'
import type { Delivery } from './types/deliveries'
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

const city: CitySummary = {
  id: 'city-id',
  name: 'Santa Aurora',
  country: 'Brazil',
  source_type: 'SYNTHETIC',
  timezone: 'America/Sao_Paulo',
  dataset_version: '1.1.0',
  generation_seed: 20260913,
  generator_version: 'santa-aurora-v2',
  depot_name: 'Centro de Distribuição FluxMed',
  district_count: 9,
  street_count: 150,
  intersection_count: 768,
  road_segment_count: 2900,
  address_count: 25000,
  facility_count: 49,
  bridge_count: 3,
}

const delivery: Delivery = {
  id: 'delivery-id',
  delivery_code: 'DLV-NF123-001',
  operation_id: operation.id,
  invoice_number: '123',
  invoice_series: '1',
  issuer_document: '12345678000190',
  issuer_name: 'Distribuidora',
  external_reference: null,
  destination_address_id: 'address-id',
  destination_address: 'Rua das Acácias, 101 — Centro Histórico',
  district_name: 'Centro Histórico',
  recipient_name: 'Hospital Central',
  package_count: 3,
  total_weight_kg: '18.500',
  total_volume_m3: '0.1200',
  priority: 'CRITICAL',
  time_window_start: null,
  time_window_end: null,
  time_window_policy: 'SOFT',
  service_time_minutes: 16,
  service_time_source: 'ESTIMATED',
  temperature_class: 'REFRIGERATED',
  handling_requirement: 'STANDARD',
  status: 'PENDING',
  cargo_profile: 'REFRIGERATED_MEDICATION',
  notes: null,
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
  window.history.pushState({}, '', '/deliveries')
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('deliveries workspace', () => {
  it('loads persisted deliveries and generates a deterministic scenario request', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = typeof input === 'string' ? input : input.toString()
      const method = init?.method ?? 'GET'
      if (path.endsWith('/auth/me')) return response(planner)
      if (path.endsWith('/api/v1/operations') && method === 'GET') {
        return response({ items: [operation], page: 1, page_size: 20, total: 1, total_pages: 1 })
      }
      if (path.endsWith('/api/v1/cities')) return response([city])
      if (path.includes('/api/v1/deliveries') && method === 'GET') {
        return response({ items: [delivery], page: 1, page_size: 20, total: 1, total_pages: 1 })
      }
      if (path.endsWith(`/api/v1/operations/${operation.id}/generate-scenario`) && method === 'POST') {
        return response({
          seed: 424242,
          summary: {
            generated_count: 20,
            critical_count: 2,
            refrigerated_count: 3,
            hard_window_count: 4,
            total_weight_kg: '200.0',
            total_volume_m3: '3.0',
          },
          validation: {
            status: 'PENDING_RESOURCES',
            message: 'Endereços validados; capacidade de frota será avaliada no preflight.',
          },
          deliveries: [delivery],
        })
      }
      return response({}, 404)
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<App />)
    const user = userEvent.setup()

    expect(await screen.findByRole('heading', { name: 'Entregas' })).toBeInTheDocument()
    expect(await screen.findByText('DLV-NF123-001')).toBeInTheDocument()
    expect(screen.getByText('Hospital Central')).toBeInTheDocument()

    await user.click(screen.getByRole('tab', { name: 'Gerar cenário' }))
    await user.click(screen.getByRole('button', { name: 'Gerar entregas' }))

    expect(await screen.findByText(/20 entregas geradas com seed 424242/)).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining(`/api/v1/operations/${operation.id}/generate-scenario`),
      expect.objectContaining({ method: 'POST' }),
    )
  })
})
