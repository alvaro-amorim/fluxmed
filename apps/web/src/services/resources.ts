import { apiRequest } from './api'
import type {
  OperationResources,
  Vehicle,
  VehicleCreateInput,
  Worker,
  WorkerAvailability,
  WorkerCreateInput,
} from '../types/resources'

export function listVehicles(): Promise<Vehicle[]> {
  return apiRequest<Vehicle[]>('/api/v1/vehicles')
}

export function createVehicle(payload: VehicleCreateInput): Promise<Vehicle> {
  return apiRequest<Vehicle>('/api/v1/vehicles', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateVehicle(
  vehicleId: string,
  payload: Partial<VehicleCreateInput>,
): Promise<Vehicle> {
  const allowed = {
    plate: payload.plate,
    type: payload.type,
    max_payload_kg: payload.max_payload_kg,
    max_volume_m3: payload.max_volume_m3,
    max_range_km: payload.max_range_km,
    refrigerated: payload.refrigerated,
    status: payload.status,
    helper_policy: payload.helper_policy,
    fuel_type: payload.fuel_type,
    fuel_efficiency_km_per_l: payload.fuel_efficiency_km_per_l,
  }
  return apiRequest<Vehicle>(`/api/v1/vehicles/${vehicleId}`, {
    method: 'PATCH',
    body: JSON.stringify(
      Object.fromEntries(Object.entries(allowed).filter(([, value]) => value !== undefined)),
    ),
  })
}

export function deactivateVehicle(vehicleId: string): Promise<Vehicle> {
  return apiRequest<Vehicle>(`/api/v1/vehicles/${vehicleId}/deactivate`, {
    method: 'POST',
  })
}

export function listWorkers(): Promise<Worker[]> {
  return apiRequest<Worker[]>('/api/v1/workers')
}

export function createWorker(payload: WorkerCreateInput): Promise<Worker> {
  return apiRequest<Worker>('/api/v1/workers', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateWorker(
  workerId: string,
  payload: Partial<WorkerCreateInput>,
): Promise<Worker> {
  return apiRequest<Worker>(`/api/v1/workers/${workerId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function deactivateWorker(workerId: string): Promise<Worker> {
  return apiRequest<Worker>(`/api/v1/workers/${workerId}/deactivate`, {
    method: 'POST',
  })
}

export function getWorkerAvailability(workerId: string, date: string): Promise<WorkerAvailability> {
  const query = new URLSearchParams({ date })
  return apiRequest<WorkerAvailability>(
    `/api/v1/workers/${workerId}/availability?${query.toString()}`,
  )
}

export function setWorkerAvailability(
  workerId: string,
  payload: { date: string; available: boolean; notes?: string | null },
): Promise<WorkerAvailability> {
  return apiRequest<WorkerAvailability>(`/api/v1/workers/${workerId}/availability`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export function getOperationResources(operationId: string): Promise<OperationResources> {
  return apiRequest<OperationResources>(`/api/v1/operations/${operationId}/resources`)
}

export function updateOperationResources(
  operationId: string,
  payload: { vehicle_ids: string[]; worker_ids: string[] },
): Promise<OperationResources> {
  return apiRequest<OperationResources>(`/api/v1/operations/${operationId}/resources`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export function generateDemoOperationResources(
  operationId: string,
): Promise<OperationResources> {
  return apiRequest<OperationResources>(`/api/v1/operations/${operationId}/resources/demo`, {
    method: 'POST',
  })
}
