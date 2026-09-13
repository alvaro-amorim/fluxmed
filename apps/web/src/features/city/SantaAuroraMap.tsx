import { useEffect, useRef, useState } from 'react'
import type { GeoJSONSourceSpecification, Map as MapLibreMap, StyleSpecification } from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'

import { getCityMap, listCities } from '../../services/cities'
import type { AddressMatch, CityMapGeoJSON, CitySummary } from '../../types/city'
import { AddressAutocomplete } from './AddressAutocomplete'
import './city.css'

function cityStyle(data: CityMapGeoJSON): StyleSpecification {
  return {
    version: 8,
    sources: {
      city: {
        type: 'geojson',
        data: data as unknown as GeoJSONSourceSpecification['data'],
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
    ],
  } as StyleSpecification
}

export function SantaAuroraMap() {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const mapRef = useRef<MapLibreMap | null>(null)
  const [city, setCity] = useState<CitySummary | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let active = true

    async function load() {
      try {
        const cities = await listCities()
        const santaAurora = cities.find((item) => item.name === 'Santa Aurora')
        if (!santaAurora) throw new Error('Santa Aurora ainda não foi gerada no backend.')
        const data = await getCityMap(santaAurora.id)
        if (!active) return
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
  }, [])

  function focusAddress(address: AddressMatch) {
    mapRef.current?.flyTo({
      center: [address.longitude, address.latitude],
      zoom: 15.2,
      duration: 700,
    })
  }

  return (
    <section className="city-map-panel" aria-label="Mapa base de Santa Aurora">
      <div className="city-map-heading">
        <div>
          <p className="eyebrow eyebrow--dark">Cidade sintética roteável</p>
          <h2>Santa Aurora</h2>
          <p>
            Dataset determinístico completo, com malha viária, endereços existentes e facilities
            médicas sem dependência de mapas externos.
          </p>
        </div>
        {city ? <span className="city-version">dataset {city.dataset_version}</span> : null}
      </div>

      {city ? (
        <div className="city-map-metrics" aria-label="Métricas da cidade">
          <span><strong>{city.district_count}</strong>bairros</span>
          <span><strong>{city.street_count}</strong>ruas</span>
          <span><strong>{city.intersection_count}</strong>interseções</span>
          <span><strong>{city.address_count.toLocaleString('pt-BR')}</strong>endereços</span>
          <span><strong>{city.facility_count}</strong>facilities</span>
          <span><strong>{city.bridge_count}</strong>pontes</span>
        </div>
      ) : null}

      <div className="city-map-shell">
        <div ref={containerRef} className="city-map-canvas" data-testid="santa-aurora-map" />
        <div className="city-map-legend" aria-label="Legenda do mapa">
          <span><i className="legend-swatch legend-swatch--ring" />Anel viário</span>
          <span><i className="legend-swatch legend-swatch--arterial" />Arteriais</span>
          <span><i className="legend-swatch legend-swatch--river" />Rio</span>
          <span><i className="legend-swatch legend-swatch--facility" />Facilities</span>
          <span><i className="legend-swatch legend-swatch--depot" />Depósito FluxMed</span>
        </div>
        {loading ? <div className="city-map-overlay">Carregando Santa Aurora…</div> : null}
        {error ? <div className="city-map-overlay city-map-overlay--error">{error}</div> : null}
      </div>

      {city ? <AddressAutocomplete cityId={city.id} onSelect={focusAddress} /> : null}
    </section>
  )
}
