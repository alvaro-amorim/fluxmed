import type {
  AddressSearchResult,
  CityMapGeoJSON,
  CitySummary,
  FacilitySummary,
} from '../types/city'
import { apiRequest } from './api'

export function listCities(): Promise<CitySummary[]> {
  return apiRequest<CitySummary[]>('/api/v1/cities')
}

export function getCityMap(cityId: string): Promise<CityMapGeoJSON> {
  return apiRequest<CityMapGeoJSON>(`/api/v1/cities/${cityId}/map`)
}

export function searchCityAddresses(
  cityId: string,
  query: string,
  limit = 8,
): Promise<AddressSearchResult> {
  const params = new URLSearchParams({ q: query, limit: String(limit) })
  return apiRequest<AddressSearchResult>(
    `/api/v1/cities/${cityId}/addresses/search?${params.toString()}`,
  )
}

export function listCityFacilities(cityId: string): Promise<FacilitySummary[]> {
  return apiRequest<FacilitySummary[]>(`/api/v1/cities/${cityId}/facilities`)
}
