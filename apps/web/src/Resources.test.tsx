import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import App from './App'
import type { Vehicle, Worker } from './types/resources'

const planner = {
  id: 'planner-id',
  email: 'planner@fluxmed.demo',
  display_name: 'Planejador Demo',
  role: 'PLANNER',
}

const vehicle: Vehicle = {
  id: 'vehicle-id',
  plate: 'ABC1D23',
  type: 'CARGO_VAN',
  ownership_type: 'OWNED',
  max_payload_kg: '1500.000',
  max_volume_m3: '8.5000',
  max_range_km: '450.00',
  refrigerated: true,
  status: 'AVAILABLE',
  helper_policy: 'OPTIONAL',
  fuel_type: 'DIESEL',
  fuel_efficiency_km_per_l: '10.000',
  active: true,
  cost: {
    ownership_type: 'OWNED',
    depreciation_per_km: '0.50',
    maintenance_per_km: '0.12',
    fixed_cost_per_hour: '6.00',
    contract_price_brl: null,
    pricing_model: null,
    fuel_included: false,
    driver_included: false,
    helper_included: false,
    maintenance_items: [],
  },
  created_at: '2026-09-14T00:00:00-03:00',
  updated_at: '2026-09-14T00:00:00-03:00',
}

const worker: Worker = {
  id: 'worker-id',
  name: 'Carlos Almeida',
  role: 'DRIVER',
  engagement_type: 'EMPLOYEE',
  compensation_model: 'HOURLY',
  compensation_value_brl: '28.50',
  active: true,
  created_at: '2026-09-14T00:00:00-03:00',
  updated_at: '2026-09-14T00:00:00-03:00',
}

function response(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('resource workspaces', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders the real fleet workspace and changes vehicle availability', async () => {
    window.history.pushState({}, '', '/fleet')
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = typeof input === 'string' ? input : input.toString()
      const method = init?.method ?? 'GET'
      if (path.endsWith('/auth/me')) return response(planner)
      if (path.endsWith('/api/v1/vehicles') && method === 'GET') return response([vehicle])
      if (path.endsWith(`/api/v1/vehicles/${vehicle.id}`) && method === 'PATCH') {
        return response({ ...vehicle, status: 'UNAVAILABLE' })
      }
      return response({}, 404)
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<App />)
    const user = userEvent.setup()

    expect(await screen.findByRole('heading', { name: 'Frota' })).toBeInTheDocument()
    expect(await screen.findByText('ABC1D23')).toBeInTheDocument()
    expect(screen.getByText('R$ 0,50')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Marcar indisponível' }))

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining(`/api/v1/vehicles/${vehicle.id}`),
      expect.objectContaining({ method: 'PATCH' }),
    )
  })

  it('loads persisted workforce availability and updates it', async () => {
    window.history.pushState({}, '', '/workforce')
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = typeof input === 'string' ? input : input.toString()
      const method = init?.method ?? 'GET'
      if (path.endsWith('/auth/me')) return response(planner)
      if (path.endsWith('/api/v1/workers') && method === 'GET') return response([worker])
      if (path.includes(`/api/v1/workers/${worker.id}/availability`) && method === 'GET') {
        return response({
          worker_id: worker.id,
          date: '2026-09-14',
          available: false,
          notes: 'Folga',
        })
      }
      if (path.endsWith(`/api/v1/workers/${worker.id}/availability`) && method === 'PUT') {
        return response({
          worker_id: worker.id,
          date: '2026-09-14',
          available: true,
          notes: null,
        })
      }
      return response({}, 404)
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<App />)
    const user = userEvent.setup()

    expect(await screen.findByRole('heading', { name: 'Equipe' })).toBeInTheDocument()
    expect(await screen.findByText('Carlos Almeida')).toBeInTheDocument()
    expect(await screen.findByText('Indisponível')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Marcar disponível' }))

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining(`/api/v1/workers/${worker.id}/availability`),
      expect.objectContaining({ method: 'PUT' }),
    )
  })
})
