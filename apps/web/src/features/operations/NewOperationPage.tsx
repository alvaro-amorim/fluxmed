import { type FormEvent, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { createOperation } from '../../services/operations'
import type { TrafficMode } from '../../types/operations'

function localDate(): string {
  const now = new Date()
  const offset = now.getTimezoneOffset() * 60_000
  return new Date(now.getTime() - offset).toISOString().slice(0, 10)
}

export function NewOperationPage() {
  const navigate = useNavigate()
  const [operationDate, setOperationDate] = useState(localDate())
  const [startTime, setStartTime] = useState('07:30')
  const [endTime, setEndTime] = useState('18:00')
  const [trafficMode, setTrafficMode] = useState<TrafficMode>('AUTOMATIC')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (endTime <= startTime) {
      setError('O horário final deve ser posterior ao horário inicial.')
      return
    }

    setSubmitting(true)
    setError(null)
    try {
      const operation = await createOperation({
        operation_date: operationDate,
        operation_start_time: `${startTime}:00`,
        operation_end_time: `${endTime}:00`,
        traffic_mode: trafficMode,
      })
      navigate(`/operations/${operation.id}`)
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Não foi possível criar a operação.',
      )
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="content-page operation-form-page">
      <header className="page-heading">
        <div>
          <p className="eyebrow eyebrow--dark">Operações · criação</p>
          <h1>Nova operação</h1>
          <p>
            Defina a janela operacional e o modo de trânsito. As demais etapas entram no wizard completo.
          </p>
        </div>
        <Link className="button button--ghost button-link" to="/operations">
          Voltar
        </Link>
      </header>

      <div className="operation-form-layout">
        <form className="operation-form-card" onSubmit={(event) => void submit(event)}>
          <div className="form-section-heading">
            <span>01</span>
            <div>
              <strong>Configuração da operação</strong>
              <p>Esses dados serão persistidos no PostgreSQL e poderão ser reabertos depois.</p>
            </div>
          </div>

          <div className="operation-form-grid">
            <label>
              Data da operação
              <input
                aria-label="Data da operação"
                type="date"
                value={operationDate}
                onChange={(event) => setOperationDate(event.target.value)}
                required
              />
            </label>
            <label>
              Cidade
              <input value="Santa Aurora" readOnly aria-label="Cidade" />
              <small>Cidade configurada para a V1.</small>
            </label>
            <label>
              Horário de saída
              <input
                aria-label="Horário de saída"
                type="time"
                value={startTime}
                onChange={(event) => setStartTime(event.target.value)}
                required
              />
            </label>
            <label>
              Encerramento máximo
              <input
                aria-label="Encerramento máximo"
                type="time"
                value={endTime}
                onChange={(event) => setEndTime(event.target.value)}
                required
              />
            </label>
            <label className="field-span">
              Modo de trânsito
              <select
                aria-label="Modo de trânsito"
                value={trafficMode}
                onChange={(event) => setTrafficMode(event.target.value as TrafficMode)}
              >
                <option value="AUTOMATIC">Automático</option>
                <option value="FREE">Livre</option>
                <option value="CUSTOM">Personalizado</option>
              </select>
              <small>
                O modo automático será conectado aos perfis viários de Santa Aurora nas próximas fases.
              </small>
            </label>
          </div>

          {error ? <p className="form-error">{error}</p> : null}

          <div className="form-actions">
            <Link className="button button--ghost button-link" to="/operations">
              Cancelar
            </Link>
            <button className="button button--primary" type="submit" disabled={submitting}>
              {submitting ? 'Criando…' : 'Criar operação'}
            </button>
          </div>
        </form>

        <aside className="operation-context-card">
          <p className="eyebrow eyebrow--dark">Escopo desta fase</p>
          <strong>Primeira feature operacional real</strong>
          <p>
            A operação nasce como rascunho. Entregas, recursos, preflight e otimização serão adicionados em
            fases seguintes sem substituir este fluxo.
          </p>
          <dl>
            <div>
              <dt>Origem</dt>
              <dd>Centro de Distribuição FluxMed</dd>
            </div>
            <div>
              <dt>Cidade</dt>
              <dd>Santa Aurora</dd>
            </div>
            <div>
              <dt>Estado inicial</dt>
              <dd>Rascunho</dd>
            </div>
          </dl>
        </aside>
      </div>
    </main>
  )
}
