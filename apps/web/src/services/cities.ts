import type { CityMapGeoJSON, CitySummary } from '../types/city'
import { apiRequest } from './api'

export function listCities(): Promise<CitySummary[]> {
  return apiRequest<CitySummary[]>('/api/v1/cities')
}

export function getCityMap(cityId: string): Promise<CityMapGeoJSON> {
  return apiRequest<CityMapGeoJSON>(`/api/v1/cities/${cityId}/map`)
}
