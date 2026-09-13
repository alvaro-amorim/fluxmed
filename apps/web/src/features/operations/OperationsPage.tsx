import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { listOperations } from '../../services/operations'
import type { Operation } from '../../types/operations'
import {
  formatOperationDate,
  formatOperationTime,
  operationStatusLabel,
  trafficModeLabel,
} from './operations-format'

export function OperationsPage() {
  const [operations, setOperations] = useState<Operation[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    void listOperations()
      .then((result) => {
        if (!active) return
        setOperations(result.items)
        setError(null)
      })
      .catch((requestError: unknown) => {
        if (!active) return
        setError(requestError instanceof Error ? requestError.message : 'Falha ao carregar operações.')
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    return () => {
      active = false
    }
  }, [])

  return (
    <main className="content-page operations-page">
      <header className="page-heading operations-heading">
        <div>
          <p className="eyebrow eyebrow--dark">Planejamento diário</p>
          <h1>Operações</h1>
          <p>Crie, revise e reabra operações persistidas no FluxMed.</p>
        </div>
        <Link className="button button--primary button-link" to="/operations/new">
          Nova operação
        </Link>
      </header>

      <section className="operations-summary" aria-label="Resumo de operações">
        <article>
          <span>Total carregado</span>
          <strong>{operations.length}</strong>
        </article>
        <article>
          <span>Em planejamento</span>
          <strong>{operations.filter((operation) => operation.status !== 'DISPATCHED').length}</strong>
        </article>
        <article>
          <span>Despachadas</span>
          <strong>{operations.filter((operation) => operation.status === 'DISPATCHED').length}</strong>
        </article>
      </section>

      <section className="operations-panel">
        <div className="panel-heading">
          <div>
            <strong>Histórico operacional</strong>
            <span>Dados reais do PostgreSQL, sem mocks de negócio.</span>
          </div>
        </div>

        {loading ? <p className="operations-state">Carregando operações…</p> : null}
        {!loading && error ? <p className="form-error">{error}</p> : null}
        {!loading && !error && operations.length === 0 ? (
          <div className="operations-empty">
            <strong>Nenhuma operação criada ainda</strong>
            <p>Crie a primeira operação para iniciar o planejamento diário de Santa Aurora.</p>
            <Link className="button button--secondary button-link" to="/operations/new">
              Criar primeira operação
            </Link>
          </div>
        ) : null}

        {!loading && !error && operations.length > 0 ? (
          <div className="operations-table-wrap">
            <table className="operations-table">
              <thead>
                <tr>
                  <th>Operação</th>
                  <th>Data</th>
                  <th>Janela</th>
                  <th>Trânsito</th>
                  <th>Status</th>
                  <th aria-label="Ações" />
                </tr>
              </thead>
              <tbody>
                {operations.map((operation) => (
                  <tr key={operation.id}>
                    <td>
                      <strong>{operation.operation_code}</strong>
                      <span>{operation.city_name}</span>
                    </td>
                    <td>{formatOperationDate(operation.operation_date)}</td>
                    <td>
                      {formatOperationTime(operation.operation_start_time)}–
                      {formatOperationTime(operation.operation_end_time)}
                    </td>
                    <td>{trafficModeLabel(operation.traffic_mode)}</td>
                    <td>
                      <span className={`operation-status operation-status--${operation.status.toLowerCase()}`}>
                        {operationStatusLabel(operation.status)}
                      </span>
                    </td>
                    <td>
                      <Link className="table-link" to={`/operations/${operation.id}`}>
                        Abrir
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>
    </main>
  )
}
