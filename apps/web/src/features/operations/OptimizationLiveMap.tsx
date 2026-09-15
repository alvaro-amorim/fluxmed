import { useEffect, useRef, useState } from 'react'
import type {
  GeoJSONSource,
  GeoJSONSourceSpecification,
  Map as MapLibreMap,
  Marker as MapLibreMarker,
  StyleSpecification,
} from 'maplibre-gl'

import { getCityMap, listCities } from '../../services/cities'
import type { CityMapGeoJSON } from '../../types/city'
import type { LiveDeliveryPoint, LiveRoute } from '../../types/optimization'
import { routeColor } from './optimization-result-palette'

interface OptimizationLiveMapProps {
  routes: LiveRoute[]
  deliveries: LiveDeliveryPoint[]
}

function emptyRoutes(): GeoJSONSourceSpecification['data'] {
  return { type: 'FeatureCollection', features: [] }
}

function liveStyle(city: CityMapGeoJSON): StyleSpecification {
  return {
    version: 8,
    sources: {
      city: {
        type: 'geojson',
        data: city as unknown as GeoJSONSourceSpecification['data'],
      },
      'live-routes': {
        type: 'geojson',
        data: emptyRoutes(),
      },
    },
    layers: [
      {
        id: 'background',
        type: 'background',
        paint: { 'background-color': '#f4f7f7' },
      },
      {
        id: 'districts',
        type: 'fill',
        source: 'city',
        filter: ['==', ['get', 'feature_type'], 'district'],
        paint: { 'fill-color': '#dcebec', 'fill-opacity': 0.34 },
      },
      {
        id: 'roads',
        type: 'line',
        source: 'city',
        filter: ['==', ['get', 'feature_type'], 'road'],
        paint: { 'line-color': '#aebabc', 'line-width': 1.2 },
      },
      {
        id: 'river',
        type: 'line',
        source: 'city',
        filter: ['==', ['get', 'feature_type'], 'river'],
        paint: { 'line-color': '#63a6b8', 'line-width': 8, 'line-opacity': 0.75 },
      },
      {
        id: 'live-route-lines',
        type: 'line',
        source: 'live-routes',
        paint: {
          'line-color': ['get', 'color'],
          'line-width': 5,
          'line-opacity': 0.9,
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
    ],
  } as StyleSpecification
}

function routeCollection(routes: LiveRoute[]): GeoJSONSourceSpecification['data'] {
  return {
    type: 'FeatureCollection',
    features: routes.flatMap((route, index) =>
      route.geometry
        ? [
            {
              type: 'Feature' as const,
              geometry: route.geometry,
              properties: {
                route_code: route.route_code,
                color: routeColor(index),
              },
            },
          ]
        : [],
    ),
  }
}

export function OptimizationLiveMap({ routes, deliveries }: OptimizationLiveMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const mapRef = useRef<MapLibreMap | null>(null)
  const maplibreRef = useRef<typeof import('maplibre-gl') | null>(null)
  const markersRef = useRef<MapLibreMarker[]>([])
  const [ready, setReady] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    async function load() {
      try {
        const cities = await listCities()
        const city = cities.find((item) => item.name === 'Santa Aurora')
        if (!city) throw new Error('Santa Aurora não está disponível.')
        const data = await getCityMap(city.id)
        const maplibregl = await import('maplibre-gl')
        if (!active || !containerRef.current) return
        const map = new maplibregl.Map({
          container: containerRef.current,
          style: liveStyle(data),
          center: [-46.62, -22.4],
          zoom: 12.1,
          attributionControl: false,
        })
        map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right')
        map.on('load', () => {
          if (active) setReady(true)
        })
        mapRef.current = map
        maplibreRef.current = maplibregl
      } catch (requestError) {
        if (active) {
          setError(
            requestError instanceof Error
              ? requestError.message
              : 'Não foi possível carregar o mapa da otimização.',
          )
        }
      }
    }
    void load()
    return () => {
      active = false
      markersRef.current.forEach((marker) => marker.remove())
      markersRef.current = []
      mapRef.current?.remove()
      mapRef.current = null
      maplibreRef.current = null
    }
  }, [])

  useEffect(() => {
    const map = mapRef.current
    if (!map || !ready) return
    const source = map.getSource('live-routes') as GeoJSONSource | undefined
    source?.setData(routeCollection(routes))
  }, [ready, routes])

  useEffect(() => {
    const map = mapRef.current
    const maplibregl = maplibreRef.current
    if (!map || !maplibregl || !ready) return

    markersRef.current.forEach((marker) => marker.remove())
    markersRef.current = []

    const routeStops = routes.flatMap((route) =>
      route.stops.map((stop) => ({ ...stop, routeCode: route.route_code })),
    )
    const points = routeStops.length
      ? routeStops
      : deliveries.map((delivery, index) => ({ ...delivery, sequence: index + 1, routeCode: '' }))

    markersRef.current = points.map((point) => {
      const element = document.createElement('div')
      element.className = 'result-stop-marker live-stop-marker'
      element.textContent = String(point.sequence ?? '•')
      element.title = `${point.routeCode ? `${point.routeCode} · ` : ''}${point.delivery_code}`
      return new maplibregl.Marker({ element, anchor: 'center' })
        .setLngLat([point.longitude, point.latitude])
        .addTo(map)
    })
  }, [deliveries, ready, routes])

  return (
    <div className="result-map-shell live-map-shell">
      <div ref={containerRef} className="result-map-canvas" data-testid="optimization-live-map" />
      {!ready && !error ? <div className="live-map-loading">Carregando mapa operacional…</div> : null}
      {error ? <div className="result-map-error">{error}</div> : null}
    </div>
  )
}
