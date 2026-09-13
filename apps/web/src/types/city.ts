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
  street_count: number
  intersection_count: number
  road_segment_count: number
  address_count: number
  facility_count: number
  bridge_count: number
}

export interface AddressMatch {
  id: string
  street_name: string
  house_number: string
  district_name: string
  complement: string | null
  formatted: string
  longitude: number
  latitude: number
}

export interface AddressSearchResult {
  query: string
  matches: AddressMatch[]
  street_suggestion: string | null
  number_suggestions: string[]
}

export type FacilityType =
  | 'DEPOT'
  | 'HOSPITAL'
  | 'CLINIC'
  | 'LABORATORY'
  | 'PHARMACY'
  | 'WAREHOUSE'
  | 'PUBLIC_FACILITY'

export interface FacilitySummary {
  id: string
  name: string
  facility_type: FacilityType
  address_id: string
  street_name: string
  house_number: string
  district_name: string
  longitude: number
  latitude: number
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
