import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  createRoadOverride,
  deleteRoadOverride,
  listRoadOverrides,
  previewOperationRoute,
} from './routing'

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

describe('routing api client', () => {
  it('requests a real route preview with the selected destination', async () => {
    const fetchMock = vi.fn(async () =>
      response({
        operation_id: 'operation-1',
        destination_address_id: 'address-1',
        algorithm: 'ASTAR',
        traffic_mode: 'AUTOMATIC',
        departure_at: '2026-09-14T07:30:00',
        arrival_at: '2026-09-14T07:42:00',
        distance_m: 8400,
        travel_time_seconds: 720,
        time_bucket: '07:30-07:45',
        edge_ids: ['segment-1'],
        geometry: { type: 'LineString', coordinates: [[-46.62, -22.4], [-46.61, -22.39]] },
        cache_hit: false,
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    const result = await previewOperationRoute('operation-1', 'address-1', {
      departureTime: '07:30:00',
    })

    expect(result.distance_m).toBe(8400)
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/operations/operation-1/route-preview',
      expect.objectContaining({ method: 'POST', credentials: 'include' }),
    )
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit
    expect(JSON.parse(String(init.body))).toEqual({
      destination_address_id: 'address-1',
      departure_time: '07:30:00',
      algorithm: 'ASTAR',
    })
  })

  it('creates, lists and removes a closure using operation-scoped endpoints', async () => {
    const closure = {
      id: 'override-1',
      operation_id: 'operation-1',
      road_segment_id: 'segment-1',
      street_name: 'Ponte Central',
      override_type: 'CLOSURE',
      direction_scope: 'SEGMENT_DIRECTION',
      traffic_level: null,
      reason: 'ROADWORK',
      notes: null,
      is_bridge: true,
      bridge_name: 'Ponte Central',
    }
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
      if (init?.method === 'POST') return response(closure, 201)
      if (init?.method === 'DELETE') return response(undefined, 204)
      return response([closure])
    })
    vi.stubGlobal('fetch', fetchMock)

    const created = await createRoadOverride('operation-1', {
      road_segment_id: 'segment-1',
      override_type: 'CLOSURE',
      reason: 'ROADWORK',
    })
    const listed = await listRoadOverrides('operation-1')
    await deleteRoadOverride('operation-1', 'override-1')

    expect(created.id).toBe('override-1')
    expect(listed).toHaveLength(1)
    const createInit = fetchMock.mock.calls[0]?.[1] as RequestInit
    expect(JSON.parse(String(createInit.body))).toEqual({
      road_segment_id: 'segment-1',
      override_type: 'CLOSURE',
      reason: 'ROADWORK',
      direction_scope: 'SEGMENT_DIRECTION',
    })
    expect(fetchMock).toHaveBeenLastCalledWith(
      '/api/v1/operations/operation-1/road-overrides/override-1',
      expect.objectContaining({ method: 'DELETE', credentials: 'include' }),
    )
  })
})
