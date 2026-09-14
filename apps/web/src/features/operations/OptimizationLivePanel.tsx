import { useEffect, useMemo, useRef, useState } from 'react'

import {
  cancelOptimizationRun,
  getOptimizationRun,
  getOptimizationTrace,
  subscribeOptimizationEvents,
} from '../../services/optimization'
import type {
  LiveDeliveryPoint,
  LiveRoute,
  OptimizationRunStatus,
  OptimizationTraceEvent,
} from '../../types/optimization'
import { OptimizationLiveMap } from './OptimizationLiveMap'
import './optimization-live.css'

interface OptimizationLivePanelProps {
  runId: string
  mode?: 'live' | 'replay'
  onTerminal?: (status: OptimizationRunStatus) => Promise<void> | void
  onClose?: () => void
}

const TERMINAL = new Set<OptimizationRunStatus>([
  'COMPLETED',
  'FAILED',
  'CANCELLED',
  'INTERRUPTED',
])

function eventStatus(event: OptimizationTraceEvent): OptimizationRunStatus | null {
  if (event.event_type === 'optimization_completed') return 'COMPLETED'
  if (event.event_type === 'optimization_cancelled') return 'CANCELLED'
  if (event.event_type === 'optimization_failed') {
    return event.payload.status === 'INTERRUPTED' ? 'INTERRUPTED' : 'FAILED'
  }
  return null
}

function mergeEvents(
  current: OptimizationTraceEvent[],
  incoming: OptimizationTraceEvent[],
): OptimizationTraceEvent[] {
  const bySequence = new Map(current.map((event) => [event.sequence, event]))
  incoming.forEach((event) => bySequence.set(event.sequence, event))
  return [...bySequence.values()].sort((left, right) => left.sequence - right.sequence)
}

function formatMoney(value?: string): string {
  if (value === undefined) return '—'
  return Number(value).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

function formatMinutes(value?: string): string {
  if (value === undefined) return '—'
  const total = Math.round(Number(value))
  const hours = Math.floor(total / 60)
  const minutes = total % 60
  return hours ? `${hours}h ${minutes}min` : `${minutes}min`
}

function formatPercent(value?: number): string {
  return value === undefined ? '—' : `${(value * 100).toFixed(1)}%`
}

function elapsedLabel(milliseconds: number | null | undefined): string {
  const seconds = Math.max(0, Math.round((milliseconds ?? 0) / 1000))
  if (seconds < 60) return `${seconds}s`
  return `${Math.floor(seconds / 60)}min ${seconds % 60}s`
}

function statusLabel(status: OptimizationRunStatus | null, replay: boolean): string {
  if (replay) return 'Replay persistido'
  const labels: Record<OptimizationRunStatus, string> = {
    QUEUED: 'Na fila',
    RUNNING: 'Otimizando',
    COMPLETED: 'Concluída',
    FAILED: 'Falhou',
    CANCELLED: 'Cancelada',
    INTERRUPTED: 'Interrompida',
  }
  return status ? labels[status] : 'Conectando'
}

function ConvergenceChart({ events }: { events: OptimizationTraceEvent[] }) {
  const points = events
    .filter((event) => event.event_type === 'generation_snapshot' && event.payload.cost_brl)
    .map((event) => ({
      generation: event.generation ?? 0,
      cost: Number(event.payload.cost_brl),
    }))
    .filter((point) => Number.isFinite(point.cost))

  if (points.length < 2) {
    return <div className="live-chart-empty">A curva aparece após as primeiras gerações.</div>
  }

  const width = 420
  const height = 110
  const padding = 10
  const minCost = Math.min(...points.map((point) => point.cost))
  const maxCost = Math.max(...points.map((point) => point.cost))
  const maxGeneration = Math.max(...points.map((point) => point.generation), 1)
  const range = Math.max(maxCost - minCost, 1)
  const polyline = points
    .map((point) => {
      const x = padding + (point.generation / maxGeneration) * (width - padding * 2)
      const y = padding + ((maxCost - point.cost) / range) * (height - padding * 2)
      return `${x},${height - y}`
    })
    .join(' ')

  return (
    <div className="live-chart" aria-label="Convergência do custo por geração">
      <svg viewBox={`0 0 ${width} ${height}`} role="img">
        <polyline points={polyline} fill="none" stroke="currentColor" strokeWidth="3" />
      </svg>
      <div><span>Geração 0</span><span>Geração {maxGeneration}</span></div>
    </div>
  )
}

export function OptimizationLivePanel({
  runId,
  mode = 'live',
  onTerminal,
  onClose,
}: OptimizationLivePanelProps) {
  const [events, setEvents] = useState<OptimizationTraceEvent[]>([])
  const [visibleCount, setVisibleCount] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [connectionState, setConnectionState] = useState<'connecting' | 'connected' | 'reconnecting'>(
    'connecting',
  )
  const [status, setStatus] = useState<OptimizationRunStatus | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [cancelling, setCancelling] = useState(false)
  const terminalReportedRef = useRef<OptimizationRunStatus | null>(null)

  useEffect(() => {
    let active = true
    let unsubscribe: (() => void) | undefined

    async function reportTerminal(nextStatus: OptimizationRunStatus) {
      setStatus(nextStatus)
      if (mode === 'live' && terminalReportedRef.current !== nextStatus) {
        terminalReportedRef.current = nextStatus
        await onTerminal?.(nextStatus)
      }
    }

    async function load() {
      try {
        const trace = await getOptimizationTrace(runId)
        if (!active) return
        setEvents(trace)
        setVisibleCount(mode === 'replay' ? Math.min(1, trace.length) : trace.length)
        const traceTerminal = [...trace].reverse().map(eventStatus).find(Boolean) ?? null
        if (traceTerminal) {
          await reportTerminal(traceTerminal)
          return
        }
        const run = await getOptimizationRun(runId)
        if (!active) return
        setStatus(run.status)
        if (TERMINAL.has(run.status)) {
          await reportTerminal(run.status)
          return
        }
        if (mode === 'replay') return

        const lastSequence = trace.at(-1)?.sequence ?? 0
        setConnectionState('connected')
        unsubscribe = subscribeOptimizationEvents(
          runId,
          lastSequence,
          (event) => {
            if (!active) return
            setConnectionState('connected')
            setEvents((current) => mergeEvents(current, [event]))
            const nextStatus = eventStatus(event)
            if (nextStatus) void reportTerminal(nextStatus)
            else setStatus('RUNNING')
          },
          () => {
            if (!active) return
            setConnectionState('reconnecting')
            void getOptimizationRun(runId)
              .then((latest) => {
                if (!active) return
                setStatus(latest.status)
                if (TERMINAL.has(latest.status)) void reportTerminal(latest.status)
              })
              .catch(() => undefined)
          },
        )
      } catch (requestError) {
        if (active) {
          setError(
            requestError instanceof Error
              ? requestError.message
              : 'Não foi possível carregar a execução da otimização.',
          )
        }
      }
    }

    void load()
    return () => {
      active = false
      unsubscribe?.()
    }
  }, [mode, onTerminal, runId])

  useEffect(() => {
    if (mode !== 'replay' || !playing || visibleCount >= events.length) return
    const timer = window.setInterval(() => {
      setVisibleCount((current) => {
        if (current >= events.length) {
          setPlaying(false)
          return current
        }
        return current + 1
      })
    }, 450)
    return () => window.clearInterval(timer)
  }, [events.length, mode, playing, visibleCount])

  useEffect(() => {
    if (mode === 'replay' && visibleCount >= events.length && events.length > 0) setPlaying(false)
  }, [events.length, mode, visibleCount])

  const shownEvents = mode === 'replay' ? events.slice(0, visibleCount) : events
  const started = shownEvents.find((event) => event.event_type === 'optimization_started')
  const latestSnapshot = [...shownEvents]
    .reverse()
    .find((event) => event.event_type === 'generation_snapshot')
  const latestBest = [...shownEvents]
    .reverse()
    .find((event) => event.event_type === 'best_solution_updated')
  const latestPruning = [...shownEvents]
    .reverse()
    .find((event) => event.event_type === 'pruning_summary')
  const latestEvent = shownEvents.at(-1)
  const routes: LiveRoute[] = latestBest?.payload.routes ?? []
  const deliveries: LiveDeliveryPoint[] = started?.payload.deliveries ?? []
  const pruning = latestPruning?.payload.counts ?? latestSnapshot?.payload.pruning_counts ?? {}
  const pruningTotal = Object.values(pruning).reduce((total, count) => total + count, 0)
  const generation = latestSnapshot?.generation ?? 0

  const visibleStatus = useMemo(() => {
    if (mode === 'replay') {
      const replayTerminal = [...shownEvents].reverse().map(eventStatus).find(Boolean)
      return replayTerminal ?? (shownEvents.length ? 'RUNNING' : null)
    }
    return status
  }, [mode, shownEvents, status])

  async function cancel() {
    setCancelling(true)
    setError(null)
    try {
      const run = await cancelOptimizationRun(runId)
      setStatus(run.status)
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Não foi possível cancelar.')
    } finally {
      setCancelling(false)
    }
  }

  function restartReplay() {
    setVisibleCount(Math.min(1, events.length))
    setPlaying(events.length > 1)
  }

  return (
    <section className="optimization-live" aria-label={mode === 'replay' ? 'Replay da otimização' : 'Otimização em tempo real'}>
      <header className="live-heading">
        <div>
          <p className="eyebrow eyebrow--dark">{mode === 'replay' ? 'Decision Trace' : 'Algoritmo genético em execução'}</p>
          <h2>{statusLabel(visibleStatus, mode === 'replay')}</h2>
          <p>
            {mode === 'replay'
              ? 'Reprodução dos eventos persistidos; o algoritmo não é recalculado.'
              : connectionState === 'reconnecting'
                ? 'Conexão perdida. Recuperando eventos persistidos…'
                : 'Snapshots reais emitidos pelo otimizador e persistidos para auditoria.'}
          </p>
        </div>
        <div className="live-actions">
          {mode === 'replay' ? (
            <>
              <button className="button button--secondary" type="button" onClick={() => setPlaying((value) => !value)} disabled={events.length < 2}>
                {playing ? 'Pausar replay' : 'Reproduzir'}
              </button>
              <button className="button button--ghost" type="button" onClick={restartReplay} disabled={events.length < 2}>
                Reiniciar
              </button>
              {onClose ? <button className="button button--ghost" type="button" onClick={onClose}>Fechar</button> : null}
            </>
          ) : !visibleStatus || !TERMINAL.has(visibleStatus) ? (
            <button className="button button--ghost live-cancel" type="button" disabled={cancelling} onClick={() => void cancel()}>
              {cancelling ? 'Solicitando cancelamento…' : 'Cancelar otimização'}
            </button>
          ) : null}
        </div>
      </header>

      {error ? <p className="form-error live-error">{error}</p> : null}
      {visibleStatus === 'FAILED' || visibleStatus === 'INTERRUPTED' ? (
        <div className="result-warning">
          <strong>{visibleStatus === 'INTERRUPTED' ? 'Execução interrompida.' : 'A otimização falhou.'}</strong>
          <span>{latestEvent?.payload.message ?? 'A operação pode ser executada novamente.'}</span>
        </div>
      ) : null}
      {visibleStatus === 'CANCELLED' ? (
        <div className="result-warning"><strong>Otimização cancelada.</strong><span>Nenhum resultado parcial foi aprovado.</span></div>
      ) : null}

      <div className="live-kpis">
        <article><span>Geração</span><strong>{generation}</strong></article>
        <article><span>Tempo</span><strong>{elapsedLabel(latestEvent?.elapsed_ms)}</strong></article>
        <article><span>Melhor custo</span><strong>{formatMoney(latestSnapshot?.payload.cost_brl)}</strong></article>
        <article><span>Makespan</span><strong>{formatMinutes(latestSnapshot?.payload.makespan_minutes)}</strong></article>
        <article><span>Diversidade</span><strong>{formatPercent(latestSnapshot?.payload.diversity_ratio)}</strong></article>
        <article><span>Mutação</span><strong>{formatPercent(latestSnapshot?.payload.mutation_rate)}</strong></article>
        <article><span>Podas</span><strong>{pruningTotal}</strong></article>
      </div>

      <div className="live-workspace">
        <div>
          <OptimizationLiveMap routes={routes} deliveries={deliveries} />
          <div className="live-route-summary">
            {routes.length ? routes.map((route) => (
              <span key={`${route.route_code}-${route.vehicle_id}`}>
                <strong>{route.route_code}</strong> · {route.stops.length} entregas · {Number(route.distance_km).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} km
              </span>
            )) : <span>Aguardando a primeira melhor solução roteável…</span>}
          </div>
        </div>
        <aside className="live-inspector">
          <section>
            <div className="live-section-title"><strong>Convergência</strong><span>custo por geração</span></div>
            <ConvergenceChart events={shownEvents} />
          </section>
          <section>
            <div className="live-section-title"><strong>Decision Trace</strong><span>{shownEvents.length} eventos</span></div>
            <ol className="trace-list">
              {[...shownEvents].reverse().slice(0, 8).map((event) => (
                <li key={event.id}>
                  <span>#{event.sequence}</span>
                  <div>
                    <strong>{event.event_type.replaceAll('_', ' ')}</strong>
                    <small>
                      {event.generation === null ? 'execução' : `geração ${event.generation}`} · {elapsedLabel(event.elapsed_ms)}
                    </small>
                  </div>
                </li>
              ))}
            </ol>
          </section>
          <section>
            <div className="live-section-title"><strong>Podas</strong><span>razões estruturadas</span></div>
            <dl className="live-pruning">
              {Object.entries(pruning).length ? Object.entries(pruning).map(([reason, count]) => (
                <div key={reason}><dt>{reason.replaceAll('_', ' ')}</dt><dd>{count}</dd></div>
              )) : <div><dt>Nenhuma poda registrada</dt><dd>0</dd></div>}
            </dl>
          </section>
        </aside>
      </div>

      {mode === 'replay' ? (
        <footer className="replay-progress">
          <progress max={Math.max(events.length, 1)} value={visibleCount} />
          <span>{visibleCount} / {events.length} eventos</span>
        </footer>
      ) : null}
    </section>
  )
}
