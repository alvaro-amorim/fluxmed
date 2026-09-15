import { useEffect, useRef, useState } from 'react'
import type {
  GeoJSONSourceSpecification,
  Map as MapLibreMap,
  Marker as MapLibreMarker,
  StyleSpecification,
} from 'maplibre-gl'

import { getCityMap, listCities } from '../../services/cities'
import type { CityMapGeoJSON } from '../../types/city'
import type { ResultRoute } from '../../types/optimization'
import { routeColor } from './optimization-result-palette'

interface OptimizationResultMapProps {
  routes: ResultRoute[]
  selectedRouteId: string | null
  onSelectRoute: (routeId: string) => void
}

function resultStyle(city: CityMapGeoJSON, routes: ResultRoute[]): StyleSpecification {
  const routeFeatures = routes.map((route, index) => ({
    type: 'Feature' as const,
    id: route.id,
    geometry: route.geometry,
    properties: {
      route_id: route.id,
      route_code: route.route_code,
      color: routeColor(index),
    },
  }))
  return {
    version: 8,
    sources: {
      city: {
        type: 'geojson',
        data: city as unknown as GeoJSONSourceSpecification['data'],
      },
      routes: {
        type: 'geojson',
        data: {
          type: 'FeatureCollection',
          features: routeFeatures,
        } as unknown as GeoJSONSourceSpecification['data'],
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
        id: 'result-routes',
        type: 'line',
        source: 'routes',
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

export function OptimizationResultMap({
  routes,
  selectedRouteId,
  onSelectRoute,
}: OptimizationResultMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const mapRef = useRef<MapLibreMap | null>(null)
  const markersRef = useRef<
    Array<{ marker: MapLibreMarker; routeId: string; element: HTMLButtonElement }>
  >([])
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
          style: resultStyle(data, routes),
          center: [-46.62, -22.4],
          zoom: 12.1,
          attributionControl: false,
        })
        map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right')
        map.on('click', 'result-routes', (event) => {
          const routeId = event.features?.[0]?.properties?.route_id
          if (routeId) onSelectRoute(String(routeId))
        })
        markersRef.current = routes.flatMap((route) =>
          route.stops.map((stop) => {
            const element = document.createElement('button')
            element.type = 'button'
            element.className = 'result-stop-marker'
            element.textContent = String(stop.sequence)
            element.title = `${route.route_code} · ${stop.delivery_code} · ${stop.recipient_name}`
            element.setAttribute('aria-label', `Parada ${stop.sequence}: ${stop.delivery_code}`)
            element.addEventListener('click', (event) => {
              event.stopPropagation()
              onSelectRoute(route.id)
            })
            const marker = new maplibregl.Marker({ element, anchor: 'center' })
              .setLngLat([stop.longitude, stop.latitude])
              .addTo(map)
            return { marker, routeId: route.id, element }
          }),
        )
        mapRef.current = map
      } catch (requestError) {
        if (active) {
          setError(
            requestError instanceof Error
              ? requestError.message
              : 'Não foi possível carregar o mapa do resultado.',
          )
        }
      }
    }
    void load()
    return () => {
      active = false
      markersRef.current.forEach(({ marker }) => marker.remove())
      markersRef.current = []
      mapRef.current?.remove()
      mapRef.current = null
    }
  }, [routes, onSelectRoute])

  useEffect(() => {
    const map = mapRef.current
    if (map?.getLayer('result-routes')) {
      map.setPaintProperty(
        'result-routes',
        'line-opacity',
        selectedRouteId
          ? ['case', ['==', ['get', 'route_id'], selectedRouteId], 1, 0.22]
          : 0.9,
      )
      map.setPaintProperty(
        'result-routes',
        'line-width',
        selectedRouteId
          ? ['case', ['==', ['get', 'route_id'], selectedRouteId], 7, 3]
          : 5,
      )
    }
    markersRef.current.forEach(({ routeId, element }) => {
      element.style.opacity = !selectedRouteId || routeId === selectedRouteId ? '1' : '0.28'
    })
  }, [selectedRouteId])

  return (
    <div className="result-map-shell">
      <div ref={containerRef} className="result-map-canvas" data-testid="optimization-result-map" />
      {error ? <div className="result-map-error">{error}</div> : null}
    </div>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export { routeColor } from './optimization-result-palette'
