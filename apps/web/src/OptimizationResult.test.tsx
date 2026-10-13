import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { OptimizationResultPanel } from './features/operations/OptimizationResultPanel'
import type { OptimizationResult, OptimizationRun } from './types/optimization'

vi.mock('./features/operations/OptimizationResultMap', () => ({
  OptimizationResultMap: () => <div data-testid="optimization-result-map">Mapa final</div>,
  routeColor: () => '#123456',
}))

const result: OptimizationResult = {
  run_id: 'run-1',
  operation_id: 'operation-1',
  revision_number: 1,
  status: 'COMPLETED',
  validated: true,
  random_seed: 582914,
  generations_completed: 44,
  stop_reason: 'EARLY_STOPPING',
  delivery_count: 2,
  vehicles_used: 1,
  total_cost_brl: '166.00',
  distance_km: '20.000',
  makespan_minutes: '120.00',
  critical_delays: 0,
  on_time_percentage: '100.00',
  average_weight_utilization_pct: '10.00',
  average_volume_utilization_pct: '12.50',
  pruning_counts: { CAPACITY_EXCEEDED: 4 },
  routes: [
    {
      id: 'route-1',
      route_code: 'R-01',
      vehicle: {
        id: 'vehicle-1',
        plate: 'ABC1D23',
        type: 'CARGO_VAN',
        ownership_type: 'OWNED',
      },
      team: {
        primary_role: 'DRIVER',
        primary_worker: { id: 'driver-1', name: 'Carlos', role: 'DRIVER' },
        helper: null,
        primary_included: false,
        helper_included: false,
        team_cost_brl: '20.00',
      },
      delivery_count: 2,
      distance_km: '20.000',
      duration_minutes: '120.00',
      total_weight_kg: '100.000',
      total_volume_m3: '1.0000',
      weight_utilization_pct: '10.00',
      volume_utilization_pct: '12.50',
      cost: {
        depreciation_brl: '10.00',
        maintenance_brl: '4.00',
        fixed_time_brl: '20.00',
        fuel_brl: '12.00',
        team_brl: '20.00',
        contract_brl: '0.00',
        total_brl: '66.00',
      },
      geometry: { type: 'LineString', coordinates: [] },
      stops: [
        {
          id: 'stop-1',
          sequence: 1,
          delivery_id: 'delivery-1',
          delivery_code: 'DLV-NF100-001',
          recipient_name: 'Hospital Aurora',
          address_label: 'Rua Aurora, 10 — Centro',
          priority: 'HIGH',
          longitude: -46.62,
          latitude: -22.4,
          planned_arrival_at: '2026-09-14T11:00:00-03:00',
          planned_departure_at: '2026-09-14T11:10:00-03:00',
          time_window_start: null,
          time_window_end: null,
          time_window_policy: 'SOFT',
          service_time_minutes: 10,
          lateness_minutes: '0.00',
        },
      ],
    },
  ],
}

const failedRun: OptimizationRun = {
  id: 'run-failed',
  operation_id: 'operation-1',
  status: 'FAILED',
  random_seed: 582914,
  generations_completed: 73,
  stop_reason: 'FAILED',
  validated: false,
  error_code: 'OPTIMIZATIONINPUTERROR',
  error_message:
    'NO_FEASIBLE_SOLUTION_FOUND: DELIVERY_UNASSIGNED, DELIVERY_UNASSIGNED, DELIVERY_UNASSIGNED, DELIVERY_UNASSIGNED.',
  latest_sequence: 95,
  created_at: '2026-09-15T12:52:39Z',
  started_at: '2026-09-15T12:52:40Z',
  completed_at: '2026-09-15T12:53:12Z',
  cancel_requested_at: null,
}

function response(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response
}

function resourcesResponse() {
  return {
    operation_id: 'operation-1',
    operation_date: '2026-09-14',
    selected_vehicle_ids: ['vehicle-1'],
    selected_worker_ids: ['driver-1'],
    unavailable_worker_ids: [],
    vehicles: [],
    workers: [
      {
        id: 'driver-1',
        name: 'Carlos',
        role: 'DRIVER',
        engagement_type: 'EMPLOYEE',
        compensation_model: 'HOURLY',
        compensation_value_brl: '10.00',
        active: true,
        created_at: '2026-09-14T10:00:00Z',
        updated_at: '2026-09-14T10:00:00Z',
      },
    ],
  }
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('optimization result', () => {
  it('shows validated KPIs, route details and approves the current plan', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = typeof input === 'string' ? input : input.toString()
      const method = init?.method ?? 'GET'
      if (path.endsWith('/operations/operation-1/optimization-runs/latest')) {
        return response(result)
      }
      if (path.endsWith('/operations/operation-1/resources')) {
        return response(resourcesResponse())
      }
      if (path.endsWith('/optimization-runs/run-1/approve') && method === 'POST') {
        return response(result)
      }
      return response({}, 404)
    })
    vi.stubGlobal('fetch', fetchMock)
    const onOperationChanged = vi.fn(async () => undefined)

    render(
      <OptimizationResultPanel
        operationId="operation-1"
        operationStatus="OPTIMIZED"
        onOperationChanged={onOperationChanged}
      />,
    )

    expect(await screen.findByText('Plano operacional validado')).toBeInTheDocument()
    expect(screen.getAllByText('ABC1D23').length).toBeGreaterThan(0)
    expect(screen.getByText('Hospital Aurora')).toBeInTheDocument()
    expect(screen.getByTestId('optimization-result-map')).toBeInTheDocument()
    expect(screen.getByText(/R\$\s*166,00/)).toBeInTheDocument()

    await userEvent.setup().click(screen.getByRole('button', { name: 'Aprovar plano' }))
    expect(onOperationChanged).toHaveBeenCalled()
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/optimization-runs/run-1/approve'),
      expect.objectContaining({ method: 'POST' }),
    )
  })

  it('keeps a failed optimization visible with its persisted reason', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const path = typeof input === 'string' ? input : input.toString()
      if (path.endsWith('/operations/operation-1/optimization-runs/latest')) {
        return response({}, 404)
      }
      if (path.endsWith('/operations/operation-1/optimization-runs/latest-run')) {
        return response(failedRun)
      }
      if (path.endsWith('/operations/operation-1/resources')) {
        return response(resourcesResponse())
      }
      return response({}, 404)
    })
    vi.stubGlobal('fetch', fetchMock)

    render(
      <OptimizationResultPanel
        operationId="operation-1"
        operationStatus="READY"
        onOperationChanged={vi.fn(async () => undefined)}
      />,
    )

    expect(await screen.findByText('A otimização não foi concluída')).toBeInTheDocument()
    expect(screen.getByText(failedRun.error_message ?? '')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Tentar novamente' })).toBeInTheDocument()
    expect(screen.queryByText('Ainda não existe um plano otimizado')).not.toBeInTheDocument()
  })

  it('keeps dispatched route details read-only', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const path = typeof input === 'string' ? input : input.toString()
      if (path.endsWith('/operations/operation-1/optimization-runs/latest')) {
        return response(result)
      }
      if (path.endsWith('/operations/operation-1/resources')) {
        return response(resourcesResponse())
      }
      return response({}, 404)
    })
    vi.stubGlobal('fetch', fetchMock)

    render(
      <OptimizationResultPanel
        operationId="operation-1"
        operationStatus="DISPATCHED"
        onOperationChanged={vi.fn(async () => undefined)}
      />,
    )

    expect(await screen.findByText('Plano operacional validado')).toBeInTheDocument()
    expect(screen.getByText('Equipe congelada após o despacho.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Simular equipe' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Aplicar' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Reotimizar' })).toBeDisabled()
  })
})
