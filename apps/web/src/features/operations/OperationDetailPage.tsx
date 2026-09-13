import { FormEvent, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { getOperation, updateOperation } from '../../services/operations'
import type { Operation, TrafficMode } from '../../types/operations'
import {
  formatOperationDate,
  formatOperationTime,
  operationStatusLabel,
  trafficModeLabel,
} from './operations-format'

export function OperationDetailPage() {
  const { operationId } = useParams<{ operationId: string }>()
  const [operation, setOperation] = useState<Operation | null>(null)
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState(false)
  const [startTime, setStartTime] = useState('')
  const [endTime, setEndTime] = useState('')
  const [trafficMode, setTrafficMode] = useState<TrafficMode>('AUTOMATIC')
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!operationId) return
    let active = true
    void getOperation(operationId)
      .then((result) => {
        if (!active) return
        setOperation(result)
        setStartTime(formatOperationTime(result.operation_start_time))
        setEndTime(formatOperationTime(result.operation_end_time))
        setTrafficMode(result.traffic_mode)
        setError(null)
      })
      .catch((requestError: unknown) => {
        if (active) setError(requestError instanceof Error ? requestError.message : 'Falha ao abrir operação.')
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [operationId])

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!operation || !operationId) return
    if (endTime <= startTime) {
      setError('O horário final deve ser posterior ao horário inicial.')
      return
    }

    setSaving(true)
    setError(null)
    try {
      const updated = await updateOperation(operationId, {
        operation_start_time: `${startTime}:00`,
        operation_end_time: `${endTime}:00`,
        traffic_mode: trafficMode,
      })
      setOperation(updated)
      setEditing(false)
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Não foi possível salvar as alterações.')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return <main className="content-page"><p className="operations-state">Abrindo operação…</p></main>
  }

  if (!operation) {
    return (
      <main className="content-page">
        <p className="form-error">{error ?? 'Operação não encontrada.'}</p>
        <Link className="table-link" to="/operations">Voltar para operações</Link>
      </main>
    )
  }

  const immutable = operation.status === 'DISPATCHED'

  return (
    <main className="content-page operation-detail-page">
      <header className="page-heading operations-heading">
        <div>
          <p className="eyebrow eyebrow--dark">Operações · {formatOperationDate(operation.operation_date)}</p>
          <h1>{operation.operation_code}</h1>
          <p>{operation.city_name} · planejamento diário</p>
        </div>
        <div className="detail-actions">
          <Link className="button button--ghost button-link" to="/operations">Voltar</Link>
          {!immutable ? (
            <button className="button button--secondary" type="button" onClick={() => setEditing((value) => !value)}>
              {editing ? 'Fechar edição' : 'Editar operação'}
            </button>
          ) : null}
        </div>
      </header>

      <section className="operation-detail-grid">
        <article className="operation-overview-card">
          <div className="panel-heading">
            <div>
              <strong>Visão geral</strong>
              <span>Dados persistidos da operação.</span>
            </div>
            <span className={`operation-status operation-status--${operation.status.toLowerCase()}`}>
              {operationStatusLabel(operation.status)}
            </span>
          </div>
          <dl className="operation-details-list">
            <div><dt>Data</dt><dd>{formatOperationDate(operation.operation_date)}</dd></div>
            <div><dt>Saída</dt><dd>{formatOperationTime(operation.operation_start_time)}</dd></div>
            <div><dt>Encerramento</dt><dd>{formatOperationTime(operation.operation_end_time)}</dd></div>
            <div><dt>Trânsito</dt><dd>{trafficModeLabel(operation.traffic_mode)}</dd></div>
            <div><dt>Cidade</dt><dd>{operation.city_name}</dd></div>
            <div><dt>Revisão atual</dt><dd>{operation.current_revision_number || 'Ainda não otimizada'}</dd></div>
          </dl>
          {immutable ? (
            <p className="immutable-note">Esta operação foi despachada e seu snapshot é imutável.</p>
          ) : null}
        </article>

        <article className="operation-stage-card">
          <p className="eyebrow eyebrow--dark">Fluxo da V1</p>
          <strong>Operação criada e persistida</strong>
          <ol>
            <li className="stage-complete">Configuração da operação</li>
            <li>Entregas e endereços</li>
            <li>Frota e equipe</li>
            <li>Preflight e otimização</li>
          </ol>
        </article>
      </section>

      {editing ? (
        <form className="operation-edit-card" onSubmit={(event) => void save(event)}>
          <div className="panel-heading">
            <div><strong>Editar configuração</strong><span>Alterações relevantes serão revalidadas pelo backend.</span></div>
          </div>
          <div className="operation-edit-fields">
            <label>
              Horário de saída
              <input type="time" value={startTime} onChange={(event) => setStartTime(event.target.value)} />
            </label>
            <label>
              Encerramento máximo
              <input type="time" value={endTime} onChange={(event) => setEndTime(event.target.value)} />
            </label>
            <label>
              Modo de trânsito
              <select value={trafficMode} onChange={(event) => setTrafficMode(event.target.value as TrafficMode)}>
                <option value="AUTOMATIC">Automático</option>
                <option value="FREE">Livre</option>
                <option value="CUSTOM">Personalizado</option>
              </select>
            </label>
          </div>
          {error ? <p className="form-error">{error}</p> : null}
          <div className="form-actions">
            <button className="button button--primary" type="submit" disabled={saving}>
              {saving ? 'Salvando…' : 'Salvar alterações'}
            </button>
          </div>
        </form>
      ) : error ? <p className="form-error detail-error">{error}</p> : null}
    </main>
  )
}
