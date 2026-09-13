export interface CitySummary {
  id: string
  name: string
  country: string
  source_type: 'SYNTHETIC'
  timezone: string
  dataset_version: string
  generation_seed: number
  generator_version: string
  depot_name: string
  district_count: number
  intersection_count: number
  road_segment_count: number
  bridge_count: number
}

export interface CityMapFeature {
  type: 'Feature'
  id: string
  geometry: {
    type: string
    coordinates: unknown
  }
  properties: Record<string, unknown>
}

export interface CityMapGeoJSON {
  type: 'FeatureCollection'
  features: CityMapFeature[]
}
