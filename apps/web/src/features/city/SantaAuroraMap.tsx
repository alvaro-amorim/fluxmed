import { useEffect, useRef, useState } from 'react'
import type {
  GeoJSONSource,
  GeoJSONSourceSpecification,
  Map as MapLibreMap,
  StyleSpecification,
} from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'

import { getCityMap, listCities } from '../../services/cities'
import {
  createRoadOverride,
  deleteRoadOverride,
  listRoadOverrides,
  previewOperationRoute,
} from '../../services/routing'
import type { AddressMatch, CityMapFeature, CityMapGeoJSON, CitySummary } from '../../types/city'
import type { TrafficMode } from '../../types/operations'
import type { RoadOverride, RoadSelection, RoutePreview, TrafficLevel } from '../../types/routing'
import { AddressAutocomplete } from './AddressAutocomplete'
import './city.css'

interface SantaAuroraMapProps {
  operationId?: string
  departureTime?: string
  trafficMode?: TrafficMode
  immutable?: boolean
}

const roadLayers = [
  'roads-local',
  'roads-collector',
  'roads-arterial',
  'roads-expressway',
  'bridges',
]

function emptyOverlay(): CityMapGeoJSON {
  return { type: 'FeatureCollection', features: [] }
}

function cityStyle(data: CityMapGeoJSON): StyleSpecification {
  return {
    version: 8,
    sources: {
      city: {
        type: 'geojson',
        data: data as unknown as GeoJSONSourceSpecification['data'],
      },
      'routing-overlay': {
        type: 'geojson',
        data: emptyOverlay() as unknown as GeoJSONSourceSpecification['data'],
      },
    },
    layers: [
      {
        id: 'background',
        type: 'background',
        paint: { 'background-color': '#f4f7f7' },
      },
      {
        id: 'district-fill',
        type: 'fill',
        source: 'city',
        filter: ['==', ['get', 'feature_type'], 'district'],
        paint: { 'fill-color': '#cde3e4', 'fill-opacity': 0.3 },
      },
      {
        id: 'district-outline',
        type: 'line',
        source: 'city',
        filter: ['==', ['get', 'feature_type'], 'district'],
        paint: { 'line-color': '#89a6aa', 'line-width': 1 },
      },
      {
        id: 'roads-local',
        type: 'line',
        source: 'city',
        filter: [
          'all',
          ['==', ['get', 'feature_type'], 'road'],
          ['in', ['get', 'road_class'], ['literal', ['LOCAL', 'SERVICE']]],
        ],
        paint: { 'line-color': '#aab6b9', 'line-width': 1 },
      },
      {
        id: 'roads-collector',
        type: 'line',
        source: 'city',
        filter: [
          'all',
          ['==', ['get', 'feature_type'], 'road'],
          ['==', ['get', 'road_class'], 'COLLECTOR'],
        ],
        paint: { 'line-color': '#718087', 'line-width': 1.5 },
      },
      {
        id: 'roads-arterial',
        type: 'line',
        source: 'city',
        filter: [
          'all',
          ['==', ['get', 'feature_type'], 'road'],
          ['==', ['get', 'road_class'], 'ARTERIAL'],
        ],
        paint: { 'line-color': '#1c626c', 'line-width': 2.5 },
      },
      {
        id: 'roads-expressway',
        type: 'line',
        source: 'city',
        filter: [
          'all',
          ['==', ['get', 'feature_type'], 'road'],
          ['==', ['get', 'road_class'], 'EXPRESSWAY'],
        ],
        paint: { 'line-color': '#b87428', 'line-width': 3.5 },
      },
      {
        id: 'bridges',
        type: 'line',
        source: 'city',
        filter: [
          'all',
          ['==', ['get', 'feature_type'], 'road'],
          ['==', ['get', 'is_bridge'], true],
        ],
        paint: { 'line-color': '#d2903e', 'line-width': 5 },
      },
      {
        id: 'river',
        type: 'line',
        source: 'city',
        filter: ['==', ['get', 'feature_type'], 'river'],
        paint: { 'line-color': '#4d9ab1', 'line-width': 9, 'line-opacity': 0.8 },
      },
      {
        id: 'facilities',
        type: 'circle',
        source: 'city',
        filter: ['==', ['get', 'feature_type'], 'facility'],
        paint: {
          'circle-radius': 4.5,
          'circle-color': '#ffffff',
          'circle-stroke-color': '#276f78',
          'circle-stroke-width': 2,
        },
      },
      {
        id: 'depot',
        type: 'circle',
        source: 'city',
        filter: ['==', ['get', 'feature_type'], 'depot'],
        paint: {
          'circle-radius': 8,
          'circle-color': '#0f5963',
          'circle-stroke-color': '#ffffff',
          'circle-stroke-width': 3,
        },
      },
      {
        id: 'routing-route',
        type: 'line',
        source: 'routing-overlay',
        filter: ['==', ['get', 'overlay_type'], 'route'],
        paint: { 'line-color': '#0c7c86', 'line-width': 5, 'line-opacity': 0.92 },
      },
      {
        id: 'routing-traffic',
        type: 'line',
        source: 'routing-overlay',
        filter: ['==', ['get', 'overlay_type'], 'traffic'],
        paint: { 'line-color': '#c47b1d', 'line-width': 7, 'line-opacity': 0.85 },
      },
      {
        id: 'routing-closure',
        type: 'line',
        source: 'routing-overlay',
        filter: ['==', ['get', 'overlay_type'], 'closure'],
        paint: { 'line-color': '#bd3b36', 'line-width': 8, 'line-opacity': 0.9 },
      },
      {
        id: 'routing-selected',
        type: 'line',
        source: 'routing-overlay',
        filter: ['==', ['get', 'overlay_type'], 'selected'],
        paint: {
          'line-color': '#102f37',
          'line-width': 9,
          'line-opacity': 0.7,
          'line-dasharray': [1.2, 1.2],
        },
      },
    ],
  } as StyleSpecification
}

function roadFeatureById(data: CityMapGeoJSON, roadSegmentId: string): CityMapFeature | undefined {
  return data.features.find(
    (feature) =>
      feature.properties.feature_type === 'road' &&
      feature.properties.road_segment_id === roadSegmentId,
  )
}

function syncRoutingOverlay(
  map: MapLibreMap,
  data: CityMapGeoJSON,
  route: RoutePreview | null,
  overrides: RoadOverride[],
  selectedRoad: RoadSelection | null,
): void {
  const features: CityMapFeature[] = []

  if (route) {
    features.push({
      type: 'Feature',
      id: 'active-route',
      geometry: route.geometry,
      properties: { overlay_type: 'route' },
    })
  }

  for (const override of overrides) {
    const feature = roadFeatureById(data, override.road_segment_id)
    if (!feature) continue
    features.push({
      ...feature,
      id: `override:${override.id}`,
      properties: {
        ...feature.properties,
        overlay_type: override.override_type === 'CLOSURE' ? 'closure' : 'traffic',
      },
    })
  }

  if (selectedRoad) {
    const feature = roadFeatureById(data, selectedRoad.road_segment_id)
    if (feature) {
      features.push({
        ...feature,
        id: `selected:${selectedRoad.road_segment_id}`,
        properties: { ...feature.properties, overlay_type: 'selected' },
      })
    }
  }

  const source = map.getSource('routing-overlay') as GeoJSONSource | undefined
  source?.setData(
    { type: 'FeatureCollection', features } as unknown as GeoJSONSourceSpecification['data'],
  )
}

function trafficModeText(mode: TrafficMode | undefined): string {
  if (mode === 'FREE') return 'livre'
  if (mode === 'CUSTOM') return 'personalizado'
  return 'automático'
}

export function SantaAuroraMap({
  operationId,
  departureTime,
  trafficMode,
  immutable = false,
}: SantaAuroraMapProps = {}) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const mapRef = useRef<MapLibreMap | null>(null)
  const cityDataRef = useRef<CityMapGeoJSON | null>(null)
  const [city, setCity] = useState<CitySummary | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [overrides, setOverrides] = useState<RoadOverride[]>([])
  const [route, setRoute] = useState<RoutePreview | null>(null)
  const [destination, setDestination] = useState<AddressMatch | null>(null)
  const [selectedRoad, setSelectedRoad] = useState<RoadSelection | null>(null)
  const [trafficLevel, setTrafficLevel] = useState<TrafficLevel>('HEAVY')
  const [routingLoading, setRoutingLoading] = useState(false)
  const [routingError, setRoutingError] = useState<string | null>(null)

  useEffect(() => {
    let active = true

    async function load() {
      try {
        const cities = await listCities()
        const santaAurora = cities.find((item) => item.name === 'Santa Aurora')
        if (!santaAurora) throw new Error('Santa Aurora ainda não foi gerada no backend.')
        const data = await getCityMap(santaAurora.id)
        if (!active) return
        cityDataRef.current = data
        setCity(santaAurora)

        if (!containerRef.current) return
        const maplibregl = await import('maplibre-gl')
        if (!active || !containerRef.current) return
        const map = new maplibregl.Map({
          container: containerRef.current,
          style: cityStyle(data),
          center: [-46.62, -22.4],
          zoom: 12.1,
          attributionControl: false,
        })
        map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right')
        if (operationId) {
          map.on('click', (event) => {
            const features = map.queryRenderedFeatures(event.point, { layers: roadLayers })
            const road = features.find((feature) => feature.properties?.road_segment_id)
            if (!road?.properties) return
            setSelectedRoad({
              road_segment_id: String(road.properties.road_segment_id),
              street_name: String(road.properties.street_name ?? 'Via sem nome'),
              is_bridge: Boolean(road.properties.is_bridge),
              bridge_name: road.properties.bridge_name
                ? String(road.properties.bridge_name)
                : null,
            })
          })
        }
        mapRef.current = map
      } catch (requestError) {
        if (active) {
          setError(
            requestError instanceof Error
              ? requestError.message
              : 'Não foi possível carregar o mapa de Santa Aurora.',
          )
        }
      } finally {
        if (active) setLoading(false)
      }
    }

    void load()
    return () => {
      active = false
      mapRef.current?.remove()
      mapRef.current = null
    }
  }, [operationId])

  useEffect(() => {
    if (!operationId) return
    let active = true
    void listRoadOverrides(operationId)
      .then((items) => {
        if (active) setOverrides(items)
      })
      .catch((requestError: unknown) => {
        if (active) {
          setRoutingError(
            requestError instanceof Error
              ? requestError.message
              : 'Não foi possível carregar as interdições.',
          )
        }
      })
    return () => {
      active = false
    }
  }, [operationId])

  useEffect(() => {
    const map = mapRef.current
    const data = cityDataRef.current
    if (!map || !data) return
    const update = () => syncRoutingOverlay(map, data, route, overrides, selectedRoad)
    if (map.isStyleLoaded()) update()
    else map.once('load', update)
  }, [overrides, route, selectedRoad])

  function focusAddress(address: AddressMatch) {
    mapRef.current?.flyTo({
      center: [address.longitude, address.latitude],
      zoom: operationId ? 13.4 : 15.2,
      duration: 700,
    })
  }

  async function calculateRoute(address: AddressMatch) {
    if (!operationId) {
      focusAddress(address)
      return
    }
    setDestination(address)
    focusAddress(address)
    setRoutingLoading(true)
    setRoutingError(null)
    try {
      const result = await previewOperationRoute(operationId, address.id, {
        departureTime: departureTime?.slice(0, 8),
        algorithm: 'ASTAR',
      })
      setRoute(result)
    } catch (requestError) {
      setRoute(null)
      setRoutingError(
        requestError instanceof Error ? requestError.message : 'Não foi possível calcular a rota.',
      )
    } finally {
      setRoutingLoading(false)
    }
  }

  async function refreshRoute() {
    if (destination) await calculateRoute(destination)
  }

  async function applyOverride(kind: 'CLOSURE' | 'TRAFFIC') {
    if (!operationId || !selectedRoad || immutable) return
    setRoutingLoading(true)
    setRoutingError(null)
    try {
      const created = await createRoadOverride(operationId, {
        road_segment_id: selectedRoad.road_segment_id,
        override_type: kind,
        traffic_level: kind === 'TRAFFIC' ? trafficLevel : undefined,
        reason: kind === 'CLOSURE' ? 'ROADWORK' : 'EVENT',
        notes: 'Override operacional criado no mapa de planejamento.',
      })
      setOverrides((items) => [...items, created])
      setSelectedRoad(null)
      await refreshRoute()
    } catch (requestError) {
      setRoutingError(
        requestError instanceof Error ? requestError.message : 'Não foi possível aplicar o override.',
      )
    } finally {
      setRoutingLoading(false)
    }
  }

  async function removeOverride(override: RoadOverride) {
    if (!operationId || immutable) return
    setRoutingLoading(true)
    setRoutingError(null)
    try {
      await deleteRoadOverride(operationId, override.id)
      setOverrides((items) => items.filter((item) => item.id !== override.id))
      await refreshRoute()
    } catch (requestError) {
      setRoutingError(
        requestError instanceof Error ? requestError.message : 'Não foi possível remover o override.',
      )
    } finally {
      setRoutingLoading(false)
    }
  }

  return (
    <section className="city-map-panel" aria-label="Mapa base de Santa Aurora">
      <div className="city-map-heading">
        <div>
          <p className="eyebrow eyebrow--dark">
            {operationId ? 'Roteamento operacional' : 'Cidade sintética roteável'}
          </p>
          <h2>Santa Aurora</h2>
          <p>
            {operationId
              ? `Origem fixa no depósito · trânsito ${trafficModeText(trafficMode)} · selecione um destino e clique em vias para simular restrições.`
              : 'Dataset determinístico completo, com malha viária, endereços existentes e facilities médicas sem dependência de mapas externos.'}
          </p>
        </div>
        {city ? <span className="city-version">dataset {city.dataset_version}</span> : null}
      </div>

      {city ? (
        <div className="city-map-metrics" aria-label="Métricas da cidade">
          <span>
            <strong>{city.district_count}</strong>bairros
          </span>
          <span>
            <strong>{city.street_count}</strong>ruas
          </span>
          <span>
            <strong>{city.intersection_count}</strong>interseções
          </span>
          <span>
            <strong>{city.address_count.toLocaleString('pt-BR')}</strong>endereços
          </span>
          <span>
            <strong>{city.facility_count}</strong>facilities
          </span>
          <span>
            <strong>{city.bridge_count}</strong>pontes
          </span>
        </div>
      ) : null}

      <div className="city-map-shell">
        <div ref={containerRef} className="city-map-canvas" data-testid="santa-aurora-map" />
        <div className="city-map-legend" aria-label="Legenda do mapa">
          <span>
            <i className="legend-swatch legend-swatch--ring" />Anel viário
          </span>
          <span>
            <i className="legend-swatch legend-swatch--arterial" />Arteriais
          </span>
          <span>
            <i className="legend-swatch legend-swatch--river" />Rio
          </span>
          <span>
            <i className="legend-swatch legend-swatch--facility" />Facilities
          </span>
          <span>
            <i className="legend-swatch legend-swatch--depot" />Depósito FluxMed
          </span>
          {operationId ? (
            <>
              <span>
                <i className="legend-swatch legend-swatch--route" />Rota calculada
              </span>
              <span>
                <i className="legend-swatch legend-swatch--closure" />Interdição
              </span>
            </>
          ) : null}
        </div>
        {loading ? <div className="city-map-overlay">Carregando Santa Aurora…</div> : null}
        {error ? <div className="city-map-overlay city-map-overlay--error">{error}</div> : null}
      </div>

      {city ? (
        <AddressAutocomplete
          cityId={city.id}
          label={operationId ? 'Destino da rota' : undefined}
          placeholder={operationId ? 'Busque um endereço para calcular depósito → destino' : undefined}
          onSelect={(address) => void calculateRoute(address)}
        />
      ) : null}

      {operationId ? (
        <div className="routing-workbench">
          <div className="routing-summary" aria-live="polite">
            <div>
              <span>Origem</span>
              <strong>Centro de Distribuição FluxMed</strong>
            </div>
            <div>
              <span>Destino</span>
              <strong>{destination?.formatted ?? 'Selecione um endereço'}</strong>
            </div>
            <div>
              <span>Distância</span>
              <strong>{route ? `${(route.distance_m / 1000).toFixed(2)} km` : '—'}</strong>
            </div>
            <div>
              <span>Tempo estimado</span>
              <strong>
                {route ? `${Math.ceil(route.travel_time_seconds / 60)} min` : '—'}
              </strong>
            </div>
            <div>
              <span>Bucket</span>
              <strong>{route?.time_bucket ?? '—'}</strong>
            </div>
          </div>

          {selectedRoad ? (
            <div className="routing-road-card">
              <div>
                <span>Segmento selecionado</span>
                <strong>{selectedRoad.street_name}</strong>
                {selectedRoad.is_bridge ? (
                  <small>{selectedRoad.bridge_name ?? 'Ponte de Santa Aurora'}</small>
                ) : null}
              </div>
              {!immutable ? (
                <div className="routing-road-actions">
                  <button
                    type="button"
                    className="button button--danger"
                    disabled={routingLoading}
                    onClick={() => void applyOverride('CLOSURE')}
                  >
                    Interditar segmento
                  </button>
                  <label>
                    Trânsito
                    <select
                      value={trafficLevel}
                      onChange={(event) => setTrafficLevel(event.target.value as TrafficLevel)}
                    >
                      <option value="LIGHT">Leve</option>
                      <option value="MODERATE">Moderado</option>
                      <option value="HEAVY">Intenso</option>
                      <option value="VERY_HEAVY">Muito intenso</option>
                    </select>
                  </label>
                  <button
                    type="button"
                    className="button button--secondary"
                    disabled={routingLoading}
                    onClick={() => void applyOverride('TRAFFIC')}
                  >
                    Aplicar trânsito
                  </button>
                </div>
              ) : null}
            </div>
          ) : (
            <p className="routing-map-hint">Clique em uma via do mapa para criar uma restrição operacional.</p>
          )}

          {overrides.length > 0 ? (
            <div className="routing-overrides">
              <div className="panel-heading">
                <div>
                  <strong>Overrides ativos</strong>
                  <span>{overrides.length} alteração(ões) no grafo efetivo desta operação.</span>
                </div>
              </div>
              <div className="routing-override-list">
                {overrides.map((override) => (
                  <div key={override.id} className="routing-override-item">
                    <div>
                      <strong>{override.street_name}</strong>
                      <span>
                        {override.override_type === 'CLOSURE'
                          ? 'Interdição'
                          : `Trânsito ${override.traffic_level?.toLowerCase().replace('_', ' ')}`}
                        {override.is_bridge && override.bridge_name
                          ? ` · ${override.bridge_name}`
                          : ''}
                      </span>
                    </div>
                    {!immutable ? (
                      <button
                        type="button"
                        className="button button--ghost"
                        disabled={routingLoading}
                        onClick={() => void removeOverride(override)}
                      >
                        Remover
                      </button>
                    ) : null}
                  </div>
                ))}
              </div>
            </div>
          ) : null}

          {routingLoading ? <p className="routing-state">Recalculando caminho real…</p> : null}
          {routingError ? <p className="form-error">{routingError}</p> : null}
        </div>
      ) : null}
    </section>
  )
}
