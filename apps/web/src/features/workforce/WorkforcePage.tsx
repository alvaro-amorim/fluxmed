import { type FormEvent, useEffect, useMemo, useState } from 'react'

import {
  createWorker,
  deactivateWorker,
  getWorkerAvailability,
  listWorkers,
  setWorkerAvailability,
} from '../../services/resources'
import type {
  CompensationModel,
  Worker,
  WorkerCreateInput,
  WorkerEngagementType,
  WorkerRole,
} from '../../types/resources'

const roleLabels: Record<WorkerRole, string> = {
  DRIVER: 'Motorista',
  HELPER: 'Ajudante',
  MOTORCYCLE_COURIER: 'Motociclista',
}

const engagementLabels: Record<WorkerEngagementType, string> = {
  EMPLOYEE: 'Funcionário',
  DAY_WORKER: 'Diarista',
  AGGREGATED: 'Agregado',
}

const compensationLabels: Record<CompensationModel, string> = {
  HOURLY: 'Por hora',
  DAILY: 'Por dia',
  PER_ROUTE: 'Por rota',
  INCLUDED_IN_VEHICLE_CONTRACT: 'Incluído no veículo',
}

function todayLocal() {
  const now = new Date()
  const year = now.getFullYear()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function formatMoney(value: string) {
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    maximumFractionDigits: 2,
  }).format(Number(value))
}

const initialForm: WorkerCreateInput = {
  name: '',
  role: 'DRIVER',
  engagement_type: 'EMPLOYEE',
  compensation_model: 'HOURLY',
  compensation_value_brl: '28.50',
}

export function WorkforcePage() {
  const [workers, setWorkers] = useState<Worker[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState<WorkerCreateInput>(initialForm)
  const [error, setError] = useState<string | null>(null)
  const [availabilityDate, setAvailabilityDate] = useState(todayLocal())
  const [availability, setAvailability] = useState<Record<string, boolean>>({})

  async function reload() {
    setLoading(true)
    try {
      setWorkers(await listWorkers())
      setError(null)
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Falha ao carregar equipe.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void reload()
  }, [])

  useEffect(() => {
    const activeWorkers = workers.filter((worker) => worker.active)
    if (activeWorkers.length === 0) {
      setAvailability({})
      return
    }

    let active = true
    void Promise.all(
      activeWorkers.map((worker) => getWorkerAvailability(worker.id, availabilityDate)),
    )
      .then((results) => {
        if (!active) return
        setAvailability(
          Object.fromEntries(results.map((item) => [item.worker_id, item.available])),
        )
      })
      .catch((requestError: unknown) => {
        if (!active) return
        setError(
          requestError instanceof Error
            ? requestError.message
            : 'Falha ao carregar disponibilidade da equipe.',
        )
      })
    return () => {
      active = false
    }
  }, [availabilityDate, workers])

  const summary = useMemo(() => {
    const active = workers.filter((worker) => worker.active)
    return {
      active: active.length,
      drivers: active.filter((worker) => worker.role === 'DRIVER').length,
      helpers: active.filter((worker) => worker.role === 'HELPER').length,
      couriers: active.filter((worker) => worker.role === 'MOTORCYCLE_COURIER').length,
    }
  }, [workers])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSaving(true)
    setError(null)
    try {
      await createWorker(form)
      setForm(initialForm)
      setShowForm(false)
      await reload()
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Falha ao cadastrar pessoa.')
    } finally {
      setSaving(false)
    }
  }

  async function toggleAvailability(worker: Worker) {
    const next = !(availability[worker.id] ?? true)
    try {
      const result = await setWorkerAvailability(worker.id, {
        date: availabilityDate,
        available: next,
      })
      setAvailability((current) => ({ ...current, [worker.id]: result.available }))
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Falha ao atualizar disponibilidade.',
      )
    }
  }

  async function deactivate(worker: Worker) {
    if (!window.confirm(`Inativar ${worker.name}?`)) return
    try {
      await deactivateWorker(worker.id)
      await reload()
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Falha ao inativar pessoa.')
    }
  }

  return (
    <main className="content-page resources-page">
      <header className="page-heading resources-heading">
        <div>
          <p className="eyebrow eyebrow--dark">Recursos operacionais</p>
          <h1>Equipe</h1>
          <p>Motoristas, ajudantes, motociclistas, vínculos, custos e disponibilidade.</p>
        </div>
        <button
          className="button button--primary"
          type="button"
          onClick={() => setShowForm((value) => !value)}
        >
          {showForm ? 'Fechar cadastro' : 'Nova pessoa'}
        </button>
      </header>

      <section className="resource-kpis" aria-label="Resumo da equipe">
        <article><strong>{summary.active}</strong><span>ativos</span></article>
        <article><strong>{summary.drivers}</strong><span>motoristas</span></article>
        <article><strong>{summary.helpers}</strong><span>ajudantes</span></article>
        <article><strong>{summary.couriers}</strong><span>motociclistas</span></article>
      </section>

      {showForm ? (
        <form className="resource-form" onSubmit={(event) => void submit(event)}>
          <div className="panel-heading">
            <div>
              <strong>Cadastrar pessoa</strong>
              <span>O modelo de pagamento será considerado no custo das rotas.</span>
            </div>
          </div>
          <div className="resource-form-grid">
            <label>
              Nome
              <input
                value={form.name}
                onChange={(event) => setForm({ ...form, name: event.target.value })}
                required
              />
            </label>
            <label>
              Função
              <select
                value={form.role}
                onChange={(event) =>
                  setForm({ ...form, role: event.target.value as WorkerRole })
                }
              >
                {Object.entries(roleLabels).map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </label>
            <label>
              Vínculo
              <select
                value={form.engagement_type}
                onChange={(event) =>
                  setForm({
                    ...form,
                    engagement_type: event.target.value as WorkerEngagementType,
                  })
                }
              >
                {Object.entries(engagementLabels).map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </label>
            <label>
              Pagamento
              <select
                value={form.compensation_model}
                onChange={(event) => {
                  const compensationModel = event.target.value as CompensationModel
                  setForm({
                    ...form,
                    compensation_model: compensationModel,
                    compensation_value_brl:
                      compensationModel === 'INCLUDED_IN_VEHICLE_CONTRACT'
                        ? '0'
                        : form.compensation_value_brl,
                  })
                }}
              >
                {Object.entries(compensationLabels).map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </label>
            <label>
              Valor (R$)
              <input
                type="number"
                min="0"
                step="0.01"
                value={form.compensation_value_brl}
                disabled={form.compensation_model === 'INCLUDED_IN_VEHICLE_CONTRACT'}
                onChange={(event) =>
                  setForm({ ...form, compensation_value_brl: event.target.value })
                }
                required
              />
            </label>
          </div>
          {error ? <p className="form-error">{error}</p> : null}
          <div className="form-actions">
            <button className="button button--primary" type="submit" disabled={saving}>
              {saving ? 'Salvando…' : 'Cadastrar pessoa'}
            </button>
          </div>
        </form>
      ) : null}

      <section className="availability-toolbar">
        <div>
          <strong>Disponibilidade operacional</strong>
          <span>Ausência de exceção significa disponível por padrão.</span>
        </div>
        <label>
          Data
          <input
            type="date"
            value={availabilityDate}
            onChange={(event) => setAvailabilityDate(event.target.value)}
          />
        </label>
      </section>

      {error && !showForm ? <p className="form-error">{error}</p> : null}

      {loading ? (
        <p className="operations-state">Carregando equipe…</p>
      ) : workers.length === 0 ? (
        <section className="resource-empty">
          <strong>Nenhuma pessoa cadastrada.</strong>
          <span>Cadastre a equipe que poderá ser selecionada nas operações.</span>
        </section>
      ) : (
        <section className="resource-list resource-list--workers">
          {workers.map((worker) => {
            const isAvailable = availability[worker.id] ?? true
            return (
              <article
                className={`resource-card ${!worker.active ? 'resource-card--inactive' : ''}`}
                key={worker.id}
              >
                <header>
                  <div>
                    <span className="resource-badge">{roleLabels[worker.role]}</span>
                    <h2>{worker.name}</h2>
                    <p>{engagementLabels[worker.engagement_type]}</p>
                  </div>
                  <span
                    className={`resource-status ${
                      worker.active && isAvailable
                        ? 'resource-status--available'
                        : 'resource-status--unavailable'
                    }`}
                  >
                    {!worker.active ? 'Inativo' : isAvailable ? 'Disponível' : 'Indisponível'}
                  </span>
                </header>

                <dl className="resource-spec-grid">
                  <div>
                    <dt>Pagamento</dt>
                    <dd>{compensationLabels[worker.compensation_model]}</dd>
                  </div>
                  <div>
                    <dt>Valor</dt>
                    <dd>
                      {worker.compensation_model === 'INCLUDED_IN_VEHICLE_CONTRACT'
                        ? 'Incluído'
                        : formatMoney(worker.compensation_value_brl)}
                    </dd>
                  </div>
                </dl>

                {worker.active ? (
                  <footer className="resource-card-actions">
                    <button
                      className="button button--ghost"
                      type="button"
                      onClick={() => void toggleAvailability(worker)}
                    >
                      {isAvailable ? 'Marcar indisponível' : 'Marcar disponível'}
                    </button>
                    <button
                      className="button button--danger"
                      type="button"
                      onClick={() => void deactivate(worker)}
                    >
                      Inativar
                    </button>
                  </footer>
                ) : null}
              </article>
            )
          })}
        </section>
      )}
    </main>
  )
}
