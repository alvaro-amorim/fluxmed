import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { OptimizationLivePanel } from './features/operations/OptimizationLivePanel'
import type { OptimizationTraceEvent } from './types/optimization'

vi.mock('./features/operations/OptimizationLiveMap', () => ({
  OptimizationLiveMap: () => <div data-testid="optimization-live-map">Mapa ao vivo</div>,
}))

const events: OptimizationTraceEvent[] = [
  {
    id: 'event-1',
    run_id: 'run-1',
    sequence: 1,
    event_type: 'optimization_started',
    generation: null,
    elapsed_ms: 0,
    payload: {
      status: 'RUNNING',
      random_seed: 42,
      delivery_count: 2,
      population_size: 16,
      max_generations: 10,
      deliveries: [],
    },
    created_at: '2026-09-14T19:00:00Z',
  },
  {
    id: 'event-2',
    run_id: 'run-1',
    sequence: 2,
    event_type: 'generation_snapshot',
    generation: 0,
    elapsed_ms: 100,
    payload: {
      generation: 0,
      cost_brl: '180.00',
      makespan_minutes: '120',
      distance_km: '21.4',
      diversity_ratio: 0.8,
      mutation_rate: 0.22,
      pruning_counts: { CAPACITY_EXCEEDED: 2 },
    },
    created_at: '2026-09-14T19:00:00Z',
  },
  {
    id: 'event-3',
    run_id: 'run-1',
    sequence: 3,
    event_type: 'generation_snapshot',
    generation: 4,
    elapsed_ms: 600,
    payload: {
      generation: 4,
      cost_brl: '150.00',
      makespan_minutes: '105',
      distance_km: '17.5',
      diversity_ratio: 0.62,
      mutation_rate: 0.25,
      pruning_counts: { CAPACITY_EXCEEDED: 3 },
    },
    created_at: '2026-09-14T19:00:01Z',
  },
]

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

describe('optimization replay', () => {
  it('replays persisted trace events with navigation controls without opening a live stream', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const path = typeof input === 'string' ? input : input.toString()
      if (path.endsWith('/optimization-runs/run-1/trace')) return response(events)
      if (path.endsWith('/optimization-runs/run-1')) {
        return response({
          id: 'run-1',
          operation_id: 'operation-1',
          status: 'COMPLETED',
          random_seed: 42,
          generations_completed: 4,
          stop_reason: 'EARLY_STOPPING',
          validated: true,
          error_code: null,
          error_message: null,
          latest_sequence: 3,
          created_at: '2026-09-14T19:00:00Z',
          started_at: '2026-09-14T19:00:00Z',
          completed_at: '2026-09-14T19:00:01Z',
          cancel_requested_at: null,
        })
      }
      return response({}, 404)
    })
    const EventSourceMock = vi.fn(() => {
      throw new Error('Replay must not open EventSource')
    })
    vi.stubGlobal('fetch', fetchMock)
    vi.stubGlobal('EventSource', EventSourceMock)

    render(<OptimizationLivePanel runId="run-1" mode="replay" />)

    expect(await screen.findByText('Replay persistido')).toBeInTheDocument()
    expect(screen.getByRole('dialog', { name: 'Replay da otimização' })).toBeInTheDocument()
    expect(screen.getByText('1 / 3 eventos')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Anterior' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Próximo' })).toBeInTheDocument()
    expect(screen.getByLabelText('Linha do tempo do replay')).toBeInTheDocument()
    expect(EventSourceMock).not.toHaveBeenCalled()

    const user = userEvent.setup()
    await user.selectOptions(screen.getByLabelText('Velocidade do replay'), '4')
    await user.click(screen.getByRole('button', { name: 'Próximo' }))
    expect(screen.getByText('2 / 3 eventos')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Reproduzir' }))

    await waitFor(() => expect(screen.getByText('4')).toBeInTheDocument(), { timeout: 1200 })
    expect(screen.getByText(/R\$\s*150,00/)).toBeInTheDocument()
    expect(screen.getByText('17,5 km')).toBeInTheDocument()
    expect(screen.getByText('3 / 3 eventos')).toBeInTheDocument()
    expect(EventSourceMock).not.toHaveBeenCalled()

    fireEvent.change(screen.getByLabelText('Linha do tempo do replay'), {
      target: { value: '1' },
    })
    expect(screen.getByText('1 / 3 eventos')).toBeInTheDocument()
  })
})
