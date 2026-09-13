import type { OperationStatus, TrafficMode } from '../../types/operations'

const statusLabels: Record<OperationStatus, string> = {
  DRAFT: 'Rascunho',
  READY: 'Pronta',
  OPTIMIZING: 'Otimizando',
  OPTIMIZED: 'Otimizada',
  OUTDATED: 'Desatualizada',
  APPROVED: 'Aprovada',
  DISPATCHED: 'Despachada',
}

const trafficLabels: Record<TrafficMode, string> = {
  AUTOMATIC: 'Automático',
  FREE: 'Livre',
  CUSTOM: 'Personalizado',
}

export function operationStatusLabel(status: OperationStatus): string {
  return statusLabels[status]
}

export function trafficModeLabel(mode: TrafficMode): string {
  return trafficLabels[mode]
}

export function formatOperationDate(value: string): string {
  const [year, month, day] = value.split('-')
  return `${day}/${month}/${year}`
}

export function formatOperationTime(value: string): string {
  return value.slice(0, 5)
}
