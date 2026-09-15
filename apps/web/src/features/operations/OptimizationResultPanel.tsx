import { useCallback, useEffect, useMemo, useState } from 'react'

import { ApiClientError } from '../../services/api'
import {
  applyRouteTeam,
  approveOptimizationResult,
  getLatestOptimizationResult,
  getLatestOptimizationRun,
  optimizeOperation,
  simulateRouteTeam,
} from '../../services/optimization'
import { getOperationResources } from '../../services/resources'
import type { OperationStatus } from '../../types/operations'
import type {
  OptimizationResult,
  OptimizationRun,
  OptimizationRunStatus,
  ResultRoute,
  TeamSimulation,
} from '../../types/optimization'
import type { OperationResources, Worker } from '../../types/resources'
import { OptimizationLivePanel } from './OptimizationLivePanel'
import { OptimizationResultMap, routeColor } from './OptimizationResultMap'
import './optimization-result.css'

interface OptimizationResultPanelProps {
  operationId: string
  operationStatus: OperationStatus
  onOperationChanged: () => Promise<void>
}

function money(value: string): string {
  return Number(value).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

function decimal(value: string, suffix: string, digits = 1): string {
  return `${Number(value).toLocaleString('pt-BR', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })}${suffix}`
}

function minutes(value: string): string {
  const total = Math.round(Number(value))
  const hours = Math.floor(total / 60)
  const mins = total % 60
  return hours > 0 ? `${hours}h ${mins}min` : `${mins}min`
}

function clock(value: string | null): string {
  if (!value) return '—'
  return new Intl.DateTimeFormat('pt-BR', {
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

function roleLabel(role: string | null): string {
  if (role === 'MOTORCYCLE_COURIER') return 'Motociclista'
  if (role === 'DRIVER') return 'Motorista'
  if (role === 'HELPER') return 'Ajudante'
  return 'Equipe do contrato'
}

function vehicleTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    MOTO: 'Moto',
    VAN_COMPACT: 'Van compacta',
    CARGO_VAN: 'Cargo van',
    LIGHT_TRUCK: 'Caminhão leve',
  }
  return labels[type] ?? type
}

function RouteInspector({
  route,
  resources,
  onTeamApplied,
}: {
  route: ResultRoute
  resources: OperationResources | null
  onTeamApplied: () => Promise<void>
}) {
  const [primaryWorkerId, setPrimaryWorkerId] = useState(route.team.primary_worker?.id ?? '')
  const [helperWorkerId, setHelperWorkerId] = useState(route.team.helper?.id ?? '')
  const [simulation, setSimulation] = useState<TeamSimulation | null>(null)
  const [simulating, setSimulating] = useState(false)
  const [teamError, setTeamError] = useState<string | null>(null)

  useEffect(() => {
    setPrimaryWorkerId(route.team.primary_worker?.id ?? '')
    setHelperWorkerId(route.team.helper?.id ?? '')
    setSimulation(null)
    setTeamError(null)
  }, [route.id, route.team.helper?.id, route.team.primary_worker?.id])

  const selectedWorkers = useMemo(() => {
    if (!resources) return []
    const ids = new Set(resources.selected_worker_ids)
    return resources.workers.filter((worker) => ids.has(worker.id))
  }, [resources])
  const primaryWorkers = selectedWorkers.filter((worker) => worker.role === route.team.primary_role)
  const helpers = selectedWorkers.filter((worker) => worker.role === 'HELPER')

  async function simulate(apply: boolean) {
    setSimulating(true)
    setTeamError(null)
    try {
      const result = apply
        ? await applyRouteTeam(route.id, primaryWorkerId || null, helperWorkerId || null)
        : await simulateRouteTeam(route.id, primaryWorkerId || null, helperWorkerId || null)
      setSimulation(result)
      if (apply && result.valid) await onTeamApplied()
    } catch (requestError) {
      setTeamError(
        requestError instanceof Error
          ? requestError.message
          : 'Não foi possível validar a equipe da rota.',
      )
    } finally {
      setSimulating(false)
    }
  }

  return (
    <aside className="result-inspector">
      <div className="result-inspector__header">
        <div>
          <p className="eyebrow eyebrow--dark">{route.route_code}</p>
          <h3>{route.vehicle.plate}</h3>
          <span>{vehicleTypeLabel(route.vehicle.type)}</span>
        </div>
        <strong>{money(route.cost.total_brl)}</strong>
      </div>

      <div className="result-utilization">
        <div>
          <span>Peso</span>
          <strong>{decimal(route.weight_utilization_pct, '%')}</strong>
          <progress max="100" value={Math.min(100, Number(route.weight_utilization_pct))} />
        </div>
        <div>
          <span>Volume</span>
          <strong>{decimal(route.volume_utilization_pct, '%')}</strong>
          <progress max="100" value={Math.min(100, Number(route.volume_utilization_pct))} />
        </div>
      </div>

      <dl className="result-route-metrics">
        <div>
          <dt>Entregas</dt>
          <dd>{route.delivery_count}</dd>
        </div>
        <div>
          <dt>Distância</dt>
          <dd>{decimal(route.distance_km, ' km')}</dd>
        </div>
        <div>
          <dt>Duração</dt>
          <dd>{minutes(route.duration_minutes)}</dd>
        </div>
        <div>
          <dt>Carga</dt>
          <dd>{decimal(route.total_weight_kg, ' kg')}</dd>
        </div>
      </dl>

      <section className="result-subsection">
        <div className="result-subsection__heading">
          <strong>Equipe</strong>
          <span>Custo {money(route.team.team_cost_brl)}</span>
        </div>
        <p>
          {roleLabel(route.team.primary_role)}:{' '}
          <strong>
            {route.team.primary_included
              ? 'incluído no contrato'
              : route.team.primary_worker?.name ?? 'não alocado'}
          </strong>
        </p>
        <p>
          Ajudante:{' '}
          <strong>
            {route.team.helper_included
              ? 'incluído no contrato'
              : route.team.helper?.name ?? 'não necessário'}
          </strong>
        </p>

        {resources ? (
          <div className="team-simulation">
            {!route.team.primary_included && route.team.primary_role ? (
              <label>
                {roleLabel(route.team.primary_role)}
                <select
                  value={primaryWorkerId}
                  onChange={(event) => setPrimaryWorkerId(event.target.value)}
                >
                  <option value="">Selecionar</option>
                  {primaryWorkers.map((worker: Worker) => (
                    <option key={worker.id} value={worker.id}>
                      {worker.name}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}
            {!route.team.helper_included ? (
              <label>
                Ajudante
                <select
                  value={helperWorkerId}
                  onChange={(event) => setHelperWorkerId(event.target.value)}
                >
                  <option value="">Sem ajudante</option>
                  {helpers.map((worker: Worker) => (
                    <option key={worker.id} value={worker.id}>
                      {worker.name}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}
            <div className="team-simulation__actions">
              <button
                className="button button--ghost"
                type="button"
                disabled={simulating}
                onClick={() => void simulate(false)}
              >
                Simular equipe
              </button>
              <button
                className="button button--secondary"
                type="button"
                disabled={simulating || !simulation?.valid}
                onClick={() => void simulate(true)}
              >
                Aplicar
              </button>
            </div>
            {simulation ? (
              <p className={simulation.valid ? 'simulation-ok' : 'form-error'}>
                {simulation.valid
                  ? `Equipe válida · novo custo da rota ${money(simulation.route_cost?.total_brl ?? route.cost.total_brl)}`
                  : simulation.issues.join(' ')}
              </p>
            ) : null}
            {teamError ? <p className="form-error">{teamError}</p> : null}
          </div>
        ) : null}
      </section>

      <section className="result-subsection">
        <strong>Custos da rota</strong>
        <dl className="cost-breakdown">
          {Number(route.cost.fuel_brl) > 0 ? <div><dt>Combustível</dt><dd>{money(route.cost.fuel_brl)}</dd></div> : null}
          {Number(route.cost.depreciation_brl) > 0 ? <div><dt>Depreciação</dt><dd>{money(route.cost.depreciation_brl)}</dd></div> : null}
          {Number(route.cost.maintenance_brl) > 0 ? <div><dt>Manutenção</dt><dd>{money(route.cost.maintenance_brl)}</dd></div> : null}
          {Number(route.cost.fixed_time_brl) > 0 ? <div><dt>Custo fixo</dt><dd>{money(route.cost.fixed_time_brl)}</dd></div> : null}
          {Number(route.cost.team_brl) > 0 ? <div><dt>Equipe</dt><dd>{money(route.cost.team_brl)}</dd></div> : null}
          {Number(route.cost.contract_brl) > 0 ? <div><dt>Contrato</dt><dd>{money(route.cost.contract_brl)}</dd></div> : null}
          <div className="cost-breakdown__total"><dt>Total</dt><dd>{money(route.cost.total_brl)}</dd></div>
        </dl>
      </section>

      <section className="result-subsection result-stops">
        <strong>Sequência de paradas</strong>
        <ol>
          {route.stops.map((stop) => (
            <li key={stop.id}>
              <div>
                <strong>{stop.delivery_code}</strong>
                <span>{stop.recipient_name}</span>
                <small>{stop.address_label}</small>
              </div>
              <div className="stop-meta">
                <span>{stop.priority}</span>
                <span>ETA {clock(stop.planned_arrival_at)}</span>
                <span>{stop.service_time_minutes} min serviço</span>
              </div>
            </li>
          ))}
        </ol>
      </section>
    </aside>
  )
}

export function OptimizationResultPanel({
  operationId,
  operationStatus,
  onOperationChanged,
}: OptimizationResultPanelProps) {
  const [result, setResult] = useState<OptimizationResult | null>(null)
  const [resources, setResources] = useState<OperationResources | null>(null)
  const [selectedRouteId, setSelectedRouteId] = useState<string | null>(null)
  const [activeRunId, setActiveRunId] = useState<string | null>(null)
  const [latestRun, setLatestRun] = useState<OptimizationRun | null>(null)
  const [replayRunId, setReplayRunId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [optimizing, setOptimizing] = useState(false)
  const [approving, setApproving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadResult = useCallback(async () => {
    try {
      const latest = await getLatestOptimizationResult(operationId)
      setResult(latest)
      setSelectedRouteId((current) => current ?? latest.routes[0]?.id ?? null)
    } catch (requestError) {
      if (requestError instanceof ApiClientError && requestError.status === 404) {
        setResult(null)
      } else {
        throw requestError
      }
    }
  }, [operationId])

  const loadActiveRun = useCallback(async () => {
    try {
      const latest = await getLatestOptimizationRun(operationId)
      setLatestRun(latest)
      setActiveRunId(latest.status === 'QUEUED' || latest.status === 'RUNNING' ? latest.id : null)
    } catch (requestError) {
      if (!(requestError instanceof ApiClientError && requestError.status === 404)) throw requestError
      setLatestRun(null)
      setActiveRunId(null)
    }
  }, [operationId])

  const refresh = useCallback(async () => {
    await Promise.all([loadResult(), onOperationChanged()])
  }, [loadResult, onOperationChanged])

  const handleTerminal = useCallback(
    async (runStatus: OptimizationRunStatus) => {
      if (runStatus === 'COMPLETED') await loadResult()
      await Promise.all([onOperationChanged(), loadActiveRun()])
    },
    [loadActiveRun, loadResult, onOperationChanged],
  )

  useEffect(() => {
    let active = true
    setLoading(true)
    Promise.all([loadResult(), loadActiveRun(), getOperationResources(operationId)])
      .then(([, , operationResources]) => {
        if (active) setResources(operationResources)
      })
      .catch((requestError: unknown) => {
        if (active) {
          setError(
            requestError instanceof Error
              ? requestError.message
              : 'Não foi possível carregar o resultado da operação.',
          )
        }
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [loadActiveRun, loadResult, operationId])

  const selectedRoute = useMemo(
    () => result?.routes.find((route) => route.id === selectedRouteId) ?? result?.routes[0] ?? null,
    [result, selectedRouteId],
  )
  const terminalRun =
    latestRun &&
    (latestRun.status === 'FAILED' ||
      latestRun.status === 'CANCELLED' ||
      latestRun.status === 'INTERRUPTED')
      ? latestRun
      : null

  async function optimize() {
    setOptimizing(true)
    setError(null)
    setLatestRun(null)
    setReplayRunId(null)
    try {
      const accepted = await optimizeOperation(operationId)
      setActiveRunId(accepted.optimization_run_id)
      await onOperationChanged()
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Não foi possível otimizar esta operação.',
      )
    } finally {
      setOptimizing(false)
    }
  }

  async function approve() {
    if (!result) return
    setApproving(true)
    setError(null)
    try {
      await approveOptimizationResult(result.run_id)
      await refresh()
    } catch (requestError) {
      setError(
        requestError instanceof Error ? requestError.message : 'Não foi possível aprovar o plano.',
      )
    } finally {
      setApproving(false)
    }
  }

  if (loading) {
    return <section className="result-empty-state">Carregando resultado operacional…</section>
  }

  if (!result && !activeRunId) {
    return (
      <section className="result-empty-state">
        <p className="eyebrow eyebrow--dark">Resultado</p>
        <h2>
          {terminalRun?.status === 'FAILED'
            ? 'A otimização não foi concluída'
            : terminalRun?.status === 'INTERRUPTED'
              ? 'A otimização foi interrompida'
              : terminalRun?.status === 'CANCELLED'
                ? 'A otimização foi cancelada'
                : 'Ainda não existe um plano otimizado'}
        </h2>
        {terminalRun ? (
          <div className="result-warning">
            <strong>
              {terminalRun.status === 'FAILED'
                ? 'Falha registrada na última execução.'
                : terminalRun.status === 'INTERRUPTED'
                  ? 'A API foi interrompida durante o cálculo.'
                  : 'Nenhum resultado parcial foi aprovado.'}
            </strong>
            <span>
              {terminalRun.error_message ??
                (terminalRun.status === 'CANCELLED'
                  ? 'Você pode iniciar uma nova otimização quando quiser.'
                  : 'Revise os dados operacionais ou tente novamente.')}
            </span>
          </div>
        ) : (
          <p>
            O FluxMed executará o algoritmo genético sobre a operação atual, alocará a equipe e
            validará o plano antes de disponibilizar o resultado.
          </p>
        )}
        <button
          className="button button--primary"
          type="button"
          disabled={optimizing || operationStatus === 'DISPATCHED'}
          onClick={() => void optimize()}
        >
          {optimizing ? 'Iniciando…' : terminalRun ? 'Tentar novamente' : 'Otimizar rotas'}
        </button>
        {error ? <p className="form-error">{error}</p> : null}
      </section>
    )
  }

  return (
    <>
      {activeRunId ? (
        <OptimizationLivePanel runId={activeRunId} onTerminal={handleTerminal} />
      ) : null}
      {replayRunId ? (
        <OptimizationLivePanel
          runId={replayRunId}
          mode="replay"
          onClose={() => setReplayRunId(null)}
        />
      ) : null}

      {result ? (
        <section className="optimization-result" aria-label="Resultado da otimização">
          <header className="result-heading">
            <div>
              <p className="eyebrow eyebrow--dark">Resultado · revisão {result.revision_number}</p>
              <h2>Plano operacional validado</h2>
              <p>
                GA concluído em {result.generations_completed} gerações · {result.stop_reason} · seed{' '}
                {result.random_seed}
              </p>
            </div>
            <div className="result-actions">
              <button
                className="button button--ghost"
                type="button"
                disabled={Boolean(activeRunId)}
                onClick={() => setReplayRunId(result.run_id)}
              >
                Reproduzir otimização
              </button>
              <button
                className="button button--secondary"
                type="button"
                disabled={optimizing || Boolean(activeRunId) || operationStatus === 'DISPATCHED'}
                onClick={() => void optimize()}
              >
                {optimizing ? 'Iniciando…' : activeRunId ? 'Otimizando…' : 'Reotimizar'}
              </button>
              {operationStatus === 'OPTIMIZED' && !activeRunId ? (
                <button
                  className="button button--primary"
                  type="button"
                  disabled={approving || !result.validated}
                  onClick={() => void approve()}
                >
                  {approving ? 'Aprovando…' : 'Aprovar plano'}
                </button>
              ) : null}
            </div>
          </header>

          {operationStatus === 'OUTDATED' ? (
            <div className="result-warning">
              <strong>Este plano está desatualizado.</strong>
              <span>Reotimize antes de aprovar ou despachar.</span>
            </div>
          ) : null}
          {operationStatus === 'APPROVED' ? (
            <div className="result-approved">
              <strong>Plano aprovado</strong>
              <span>A revisão atual está pronta para a etapa de dispatch.</span>
            </div>
          ) : null}
          {error ? <p className="form-error live-error">{error}</p> : null}

          <div className="result-kpis">
            <article><span>Entregas</span><strong>{result.delivery_count}</strong></article>
            <article><span>Veículos usados</span><strong>{result.vehicles_used}</strong></article>
            <article><span>Custo total</span><strong>{money(result.total_cost_brl)}</strong></article>
            <article><span>Distância</span><strong>{decimal(result.distance_km, ' km')}</strong></article>
            <article><span>Makespan</span><strong>{minutes(result.makespan_minutes)}</strong></article>
            <article><span>Atrasos críticos</span><strong>{result.critical_delays}</strong></article>
            <article><span>No prazo</span><strong>{decimal(result.on_time_percentage, '%')}</strong></article>
          </div>

          <div className="result-workspace">
            <div className="result-map-column">
              <OptimizationResultMap
                routes={result.routes}
                selectedRouteId={selectedRoute?.id ?? null}
                onSelectRoute={setSelectedRouteId}
              />
              <div className="route-legend">
                {result.routes.map((route, index) => (
                  <button
                    key={route.id}
                    type="button"
                    className={selectedRoute?.id === route.id ? 'route-legend__item is-active' : 'route-legend__item'}
                    onClick={() => setSelectedRouteId(route.id)}
                  >
                    <i style={{ background: routeColor(index) }} />
                    <span>{route.vehicle.plate}</span>
                    <small>{route.route_code} · {route.delivery_count} entregas</small>
                    <strong>{money(route.cost.total_brl)}</strong>
                  </button>
                ))}
              </div>
            </div>
            {selectedRoute ? (
              <RouteInspector route={selectedRoute} resources={resources} onTeamApplied={refresh} />
            ) : null}
          </div>
        </section>
      ) : null}
    </>
  )
}
