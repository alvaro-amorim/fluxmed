import { useEffect, useMemo, useState } from 'react'

import {
  generateDemoOperationResources,
  getOperationResources,
  updateOperationResources,
} from '../../services/resources'
import type { OperationResources, Vehicle, Worker } from '../../types/resources'

function vehicleLabel(vehicle: Vehicle) {
  const type = {
    MOTO: 'Moto',
    VAN_COMPACT: 'Van compacta',
    CARGO_VAN: 'Van de carga',
    LIGHT_TRUCK: 'Caminhão leve',
  }[vehicle.type]
  return `${vehicle.plate} · ${type}`
}

function workerRoleLabel(worker: Worker) {
  return {
    DRIVER: 'Motorista',
    HELPER: 'Ajudante',
    MOTORCYCLE_COURIER: 'Motociclista',
  }[worker.role]
}

interface OperationResourcesPanelProps {
  operationId: string
  immutable?: boolean
}

export function OperationResourcesPanel({
  operationId,
  immutable = false,
}: OperationResourcesPanelProps) {
  const [resources, setResources] = useState<OperationResources | null>(null)
  const [vehicleIds, setVehicleIds] = useState<string[]>([])
  const [workerIds, setWorkerIds] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [generatingDemo, setGeneratingDemo] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)
  const [demoGenerated, setDemoGenerated] = useState(false)

  useEffect(() => {
    let active = true
    setLoading(true)
    void getOperationResources(operationId)
      .then((result) => {
        if (!active) return
        setResources(result)
        setVehicleIds(result.selected_vehicle_ids)
        setWorkerIds(result.selected_worker_ids)
        setError(null)
      })
      .catch((requestError: unknown) => {
        if (!active) return
        setError(
          requestError instanceof Error
            ? requestError.message
            : 'Não foi possível carregar os recursos da operação.',
        )
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [operationId])

  const unavailableWorkers = useMemo(
    () => new Set(resources?.unavailable_worker_ids ?? []),
    [resources],
  )

  function toggleVehicle(vehicleId: string) {
    setSaved(false)
    setDemoGenerated(false)
    setVehicleIds((current) =>
      current.includes(vehicleId)
        ? current.filter((item) => item !== vehicleId)
        : [...current, vehicleId],
    )
  }

  function toggleWorker(workerId: string) {
    setSaved(false)
    setDemoGenerated(false)
    setWorkerIds((current) =>
      current.includes(workerId)
        ? current.filter((item) => item !== workerId)
        : [...current, workerId],
    )
  }

  async function save() {
    setSaving(true)
    setSaved(false)
    setDemoGenerated(false)
    setError(null)
    try {
      const updated = await updateOperationResources(operationId, {
        vehicle_ids: vehicleIds,
        worker_ids: workerIds,
      })
      setResources(updated)
      setVehicleIds(updated.selected_vehicle_ids)
      setWorkerIds(updated.selected_worker_ids)
      setSaved(true)
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Não foi possível atualizar os recursos da operação.',
      )
    } finally {
      setSaving(false)
    }
  }

  async function generateDemo() {
    setGeneratingDemo(true)
    setSaved(false)
    setDemoGenerated(false)
    setError(null)
    try {
      const generated = await generateDemoOperationResources(operationId)
      setResources(generated)
      setVehicleIds(generated.selected_vehicle_ids)
      setWorkerIds(generated.selected_worker_ids)
      setDemoGenerated(true)
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Não foi possível gerar os recursos de demonstração.',
      )
    } finally {
      setGeneratingDemo(false)
    }
  }

  return (
    <section className="operation-resources-panel" aria-labelledby="operation-resources-title">
      <div className="panel-heading">
        <div>
          <strong id="operation-resources-title">Frota e equipe da operação</strong>
          <span>Selecione apenas os recursos que poderão participar do planejamento.</span>
        </div>
        {resources ? (
          <span className="resource-badge">
            {vehicleIds.length} veículos · {workerIds.length} pessoas
          </span>
        ) : null}
      </div>

      {loading ? <p className="operations-state">Carregando recursos…</p> : null}
      {error ? <p className="form-error">{error}</p> : null}

      {resources && !loading ? (
        <div className="operation-resource-columns">
          <div className="operation-resource-group">
            <h3>Frota</h3>
            {resources.vehicles.length === 0 ? (
              <p className="operations-state">Nenhum veículo ativo cadastrado.</p>
            ) : (
              resources.vehicles.map((vehicle) => {
                const disabled = !vehicle.active || vehicle.status !== 'AVAILABLE' || immutable
                return (
                  <label
                    className={`operation-resource-option ${
                      disabled ? 'operation-resource-option--disabled' : ''
                    }`}
                    key={vehicle.id}
                  >
                    <input
                      type="checkbox"
                      checked={vehicleIds.includes(vehicle.id)}
                      disabled={disabled}
                      onChange={() => toggleVehicle(vehicle.id)}
                    />
                    <span>
                      <strong>{vehicleLabel(vehicle)}</strong>
                      <small>
                        {vehicle.max_payload_kg} kg · {vehicle.max_volume_m3} m³ ·{' '}
                        {vehicle.max_range_km} km
                        {vehicle.refrigerated ? ' · refrigerado' : ''}
                      </small>
                    </span>
                  </label>
                )
              })
            )}
          </div>

          <div className="operation-resource-group">
            <h3>Equipe</h3>
            {resources.workers.length === 0 ? (
              <p className="operations-state">Nenhuma pessoa ativa cadastrada.</p>
            ) : (
              resources.workers.map((worker) => {
                const unavailable = unavailableWorkers.has(worker.id)
                const disabled = unavailable || !worker.active || immutable
                return (
                  <label
                    className={`operation-resource-option ${
                      disabled ? 'operation-resource-option--disabled' : ''
                    }`}
                    key={worker.id}
                  >
                    <input
                      type="checkbox"
                      checked={workerIds.includes(worker.id)}
                      disabled={disabled}
                      onChange={() => toggleWorker(worker.id)}
                    />
                    <span>
                      <strong>{worker.name}</strong>
                      <small>
                        {workerRoleLabel(worker)}
                        {unavailable ? ' · indisponível na data da operação' : ''}
                      </small>
                    </span>
                  </label>
                )
              })
            )}
          </div>
        </div>
      ) : null}

      {resources && !immutable ? (
        <div className="form-actions">
          {demoGenerated ? (
            <span className="resource-save-success">Recursos demo gerados e selecionados.</span>
          ) : saved ? (
            <span className="resource-save-success">Recursos atualizados.</span>
          ) : null}
          <button
            className="button button--secondary"
            type="button"
            disabled={saving || generatingDemo}
            onClick={() => void generateDemo()}
          >
            {generatingDemo ? 'Gerando demo…' : 'Gerar frota e equipe demo'}
          </button>
          <button
            className="button button--primary"
            type="button"
            disabled={saving || generatingDemo}
            onClick={() => void save()}
          >
            {saving ? 'Salvando…' : 'Salvar seleção'}
          </button>
        </div>
      ) : null}
    </section>
  )
}
