import { FormEvent, useEffect, useMemo, useState } from 'react'

import { listCities } from '../../services/cities'
import {
  confirmDeliveryImport,
  createDelivery,
  createDeliveryImport,
  deleteDelivery,
  generateScenario,
  listDeliveries,
  updateDelivery,
} from '../../services/deliveries'
import { listOperations } from '../../services/operations'
import type { AddressMatch, CitySummary } from '../../types/city'
import type {
  Delivery,
  DeliveryImport,
  DeliveryPriority,
  DeliveryStatus,
  ScenarioProfile,
  TemperatureClass,
} from '../../types/deliveries'
import type { Operation } from '../../types/operations'
import { AddressAutocomplete } from '../city/AddressAutocomplete'

const priorityLabels: Record<DeliveryPriority, string> = {
  CRITICAL: 'Crítica',
  HIGH: 'Alta',
  NORMAL: 'Normal',
  LOW: 'Baixa',
}

const statusLabels: Record<DeliveryStatus, string> = {
  PENDING: 'Pendente',
  PLANNED: 'Planejada',
  LOADED: 'Carregada',
  DISPATCHED: 'Despachada',
  IN_TRANSIT: 'Em trânsito',
  DELIVERED: 'Entregue',
  FAILED: 'Falha',
}

const scenarioLabels: Record<ScenarioProfile, string> = {
  NORMAL: 'Normal',
  BUSY: 'Movimentado',
  HIGH_PRESSURE: 'Alta pressão',
  EMERGENCY: 'Emergência',
}

function decimal(value: string): string {
  return Number(value).toLocaleString('pt-BR', { maximumFractionDigits: 2 })
}

function dateTime(value: string | null): string {
  if (!value) return 'Sem janela'
  return new Intl.DateTimeFormat('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

export function DeliveriesPage() {
  const [operations, setOperations] = useState<Operation[]>([])
  const [city, setCity] = useState<CitySummary | null>(null)
  const [deliveries, setDeliveries] = useState<Delivery[]>([])
  const [loading, setLoading] = useState(true)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const [operationFilter, setOperationFilter] = useState('')
  const [priorityFilter, setPriorityFilter] = useState<DeliveryPriority | ''>('')
  const [temperatureFilter, setTemperatureFilter] = useState<TemperatureClass | ''>('')
  const [statusFilter, setStatusFilter] = useState<DeliveryStatus | ''>('')
  const [query, setQuery] = useState('')

  const [intakeMode, setIntakeMode] = useState<'manual' | 'scenario' | 'import'>('manual')
  const [operationId, setOperationId] = useState('')
  const [selectedAddress, setSelectedAddress] = useState<AddressMatch | null>(null)
  const [manualPending, setManualPending] = useState(false)
  const [scenarioPending, setScenarioPending] = useState(false)
  const [importPending, setImportPending] = useState(false)
  const [importPreview, setImportPreview] = useState<DeliveryImport | null>(null)
  const [selectedDelivery, setSelectedDelivery] = useState<Delivery | null>(null)
  const [editPriority, setEditPriority] = useState<DeliveryPriority>('NORMAL')
  const [editPending, setEditPending] = useState(false)

  const mutableOperations = useMemo(
    () => operations.filter((operation) => operation.status !== 'DISPATCHED'),
    [operations],
  )

  async function refreshDeliveries() {
    const result = await listDeliveries({
      operation_id: operationFilter || undefined,
      priority: priorityFilter || undefined,
      temperature_class: temperatureFilter || undefined,
      status: statusFilter || undefined,
      q: query || undefined,
    })
    setDeliveries(result.items)
  }

  useEffect(() => {
    let active = true
    void Promise.all([listOperations(), listCities()])
      .then(async ([operationResult, cities]) => {
        if (!active) return
        setOperations(operationResult.items)
        const selectedCity = cities.find((item) => item.name === 'Santa Aurora') ?? cities[0] ?? null
        setCity(selectedCity)
        const firstMutable = operationResult.items.find((item) => item.status !== 'DISPATCHED')
        if (firstMutable) setOperationId(firstMutable.id)
        const deliveryResult = await listDeliveries()
        if (active) setDeliveries(deliveryResult.items)
      })
      .catch((requestError: unknown) => {
        if (!active) return
        setError(requestError instanceof Error ? requestError.message : 'Falha ao carregar entregas.')
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [])

  async function applyFilters(event: FormEvent) {
    event.preventDefault()
    setLoading(true)
    setError(null)
    try {
      await refreshDeliveries()
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Falha ao filtrar entregas.')
    } finally {
      setLoading(false)
    }
  }

  async function submitManual(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    if (!operationId) {
      setError('Selecione uma operação para receber a entrega.')
      return
    }
    if (!selectedAddress) {
      setError('Selecione um endereço existente em Santa Aurora.')
      return
    }
    setManualPending(true)
    setError(null)
    setMessage(null)
    try {
      const startValue = String(form.get('time_window_start') ?? '')
      const endValue = String(form.get('time_window_end') ?? '')
      await createDelivery(operationId, {
        invoice_number: String(form.get('invoice_number') ?? ''),
        invoice_series: String(form.get('invoice_series') ?? ''),
        issuer_document: String(form.get('issuer_document') ?? ''),
        issuer_name: String(form.get('issuer_name') ?? '') || null,
        recipient_name: String(form.get('recipient_name') ?? ''),
        destination_address_id: selectedAddress.id,
        package_count: Number(form.get('package_count')),
        total_weight_kg: String(form.get('total_weight_kg') ?? ''),
        total_volume_m3: String(form.get('total_volume_m3') ?? ''),
        priority: String(form.get('priority')) as DeliveryPriority,
        time_window_start: startValue ? new Date(startValue).toISOString() : null,
        time_window_end: endValue ? new Date(endValue).toISOString() : null,
        time_window_policy: String(form.get('time_window_policy')) as 'HARD' | 'SOFT',
        temperature_class: String(form.get('temperature_class')) as TemperatureClass,
        handling_requirement: form.get('two_person') === 'on' ? 'TWO_PERSON' : 'STANDARD',
        service_time_minutes: form.get('service_time_minutes')
          ? Number(form.get('service_time_minutes'))
          : null,
        notes: String(form.get('notes') ?? '') || null,
      })
      event.currentTarget.reset()
      setSelectedAddress(null)
      setMessage('Entrega cadastrada e vinculada ao endereço validado.')
      await refreshDeliveries()
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Falha ao cadastrar entrega.')
    } finally {
      setManualPending(false)
    }
  }

  async function submitScenario(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    if (!operationId) {
      setError('Selecione uma operação antes de gerar o cenário.')
      return
    }
    setScenarioPending(true)
    setError(null)
    setMessage(null)
    try {
      const seedValue = String(form.get('seed') ?? '')
      const result = await generateScenario(operationId, {
        profile: String(form.get('profile')) as ScenarioProfile,
        delivery_count: Number(form.get('delivery_count')),
        ...(seedValue ? { random_seed: Number(seedValue) } : {}),
      })
      setMessage(
        `${result.summary.generated_count} entregas geradas com seed ${result.seed}. ${result.validation.message}`,
      )
      await refreshDeliveries()
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Falha ao gerar cenário.')
    } finally {
      setScenarioPending(false)
    }
  }

  async function submitImport(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const file = form.get('file')
    if (!operationId || !(file instanceof File) || file.size === 0) {
      setError('Selecione uma operação e um arquivo CSV ou XLSX.')
      return
    }
    setImportPending(true)
    setError(null)
    setMessage(null)
    try {
      const preview = await createDeliveryImport(operationId, file)
      setImportPreview(preview)
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Falha ao validar importação.')
    } finally {
      setImportPending(false)
    }
  }

  async function confirmImport() {
    if (!importPreview) return
    setImportPending(true)
    setError(null)
    try {
      const confirmed = await confirmDeliveryImport(importPreview.id)
      setImportPreview(confirmed)
      setMessage(`${confirmed.summary.total_rows} linhas confirmadas na operação.`)
      await refreshDeliveries()
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Falha ao confirmar importação.')
    } finally {
      setImportPending(false)
    }
  }

  function openDetail(delivery: Delivery) {
    setSelectedDelivery(delivery)
    setEditPriority(delivery.priority)
  }

  async function saveSelectedDelivery() {
    if (!selectedDelivery) return
    setEditPending(true)
    setError(null)
    try {
      const updated = await updateDelivery(selectedDelivery.operation_id, selectedDelivery.id, {
        priority: editPriority,
      })
      setSelectedDelivery(updated)
      setMessage(`${updated.delivery_code} atualizado.`)
      await refreshDeliveries()
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Falha ao atualizar entrega.')
    } finally {
      setEditPending(false)
    }
  }

  async function removeSelectedDelivery() {
    if (!selectedDelivery) return
    if (!window.confirm(`Excluir ${selectedDelivery.delivery_code}?`)) return
    setEditPending(true)
    setError(null)
    try {
      await deleteDelivery(selectedDelivery.operation_id, selectedDelivery.id)
      setSelectedDelivery(null)
      setMessage('Entrega removida da operação.')
      await refreshDeliveries()
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Falha ao excluir entrega.')
    } finally {
      setEditPending(false)
    }
  }

  return (
    <main className="content-page deliveries-page">
      <header className="page-heading deliveries-heading">
        <div>
          <p className="eyebrow eyebrow--dark">Demanda operacional</p>
          <h1>Entregas</h1>
          <p>Cadastre, gere ou importe paradas usando somente endereços existentes em Santa Aurora.</p>
        </div>
        <div className="deliveries-kpis" aria-label="Resumo de entregas">
          <span><strong>{deliveries.length}</strong> exibidas</span>
          <span><strong>{deliveries.filter((item) => item.priority === 'CRITICAL').length}</strong> críticas</span>
          <span><strong>{deliveries.filter((item) => item.temperature_class === 'REFRIGERATED').length}</strong> refrigeradas</span>
        </div>
      </header>

      {message ? <p className="delivery-feedback delivery-feedback--success">{message}</p> : null}
      {error ? <p className="delivery-feedback delivery-feedback--error">{error}</p> : null}

      <section className="deliveries-intake-panel">
        <div className="delivery-panel-heading">
          <div>
            <strong>Entrada de demanda</strong>
            <span>Todos os caminhos persistem a mesma entidade Delivery.</span>
          </div>
          <label className="delivery-operation-select">
            Operação de destino
            <select value={operationId} onChange={(event) => setOperationId(event.target.value)}>
              <option value="">Selecione</option>
              {mutableOperations.map((operation) => (
                <option key={operation.id} value={operation.id}>{operation.operation_code}</option>
              ))}
            </select>
          </label>
        </div>

        <div className="delivery-mode-tabs" role="tablist" aria-label="Origem das entregas">
          {(['manual', 'scenario', 'import'] as const).map((mode) => (
            <button
              key={mode}
              type="button"
              role="tab"
              aria-selected={intakeMode === mode}
              className={intakeMode === mode ? 'delivery-mode-tab delivery-mode-tab--active' : 'delivery-mode-tab'}
              onClick={() => setIntakeMode(mode)}
            >
              {mode === 'manual' ? 'Cadastro manual' : mode === 'scenario' ? 'Gerar cenário' : 'Importar arquivo'}
            </button>
          ))}
        </div>

        {intakeMode === 'manual' ? (
          <form className="delivery-form" onSubmit={submitManual}>
            <div className="delivery-form-grid">
              <label>NF<input name="invoice_number" required placeholder="45872" /></label>
              <label>Série<input name="invoice_series" required defaultValue="1" /></label>
              <label>Documento emissor<input name="issuer_document" required placeholder="12.345.678/0001-90" /></label>
              <label>Emissor<input name="issuer_name" placeholder="Distribuidora médica" /></label>
              <label className="delivery-form-wide">Destinatário<input name="recipient_name" required placeholder="Hospital, clínica ou paciente" /></label>
            </div>

            <div className="delivery-address-field">
              <AddressAutocomplete cityId={city?.id ?? ''} onSelect={setSelectedAddress} />
              <div className={selectedAddress ? 'selected-address selected-address--ready' : 'selected-address'}>
                <span>Destino</span>
                <strong>{selectedAddress?.formatted ?? 'Selecione um endereço válido acima'}</strong>
              </div>
            </div>

            <div className="delivery-form-grid delivery-form-grid--cargo">
              <label>Volumes<input name="package_count" required type="number" min="1" defaultValue="1" /></label>
              <label>Peso total (kg)<input name="total_weight_kg" required type="number" min="0.001" step="0.001" /></label>
              <label>Volume total (m³)<input name="total_volume_m3" required type="number" min="0.0001" step="0.0001" /></label>
              <label>Prioridade<select name="priority" defaultValue="NORMAL"><option value="CRITICAL">Crítica</option><option value="HIGH">Alta</option><option value="NORMAL">Normal</option><option value="LOW">Baixa</option></select></label>
              <label>Temperatura<select name="temperature_class" defaultValue="AMBIENT"><option value="AMBIENT">Ambiente</option><option value="REFRIGERATED">Refrigerada</option></select></label>
              <label>Política da janela<select name="time_window_policy" defaultValue="SOFT"><option value="SOFT">Soft</option><option value="HARD">Hard</option></select></label>
              <label>Início da janela<input name="time_window_start" type="datetime-local" /></label>
              <label>Fim da janela<input name="time_window_end" type="datetime-local" /></label>
              <label>Atendimento (min)<input name="service_time_minutes" type="number" min="1" placeholder="Automático" /></label>
              <label className="delivery-checkbox"><input name="two_person" type="checkbox" /> Exige duas pessoas</label>
              <label className="delivery-form-wide">Observações<textarea name="notes" rows={2} /></label>
            </div>
            <div className="delivery-form-actions">
              <span>Sem tempo manual, o FluxMed usa o estimador determinístico.</span>
              <button className="button button--primary" disabled={manualPending || !city} type="submit">
                {manualPending ? 'Salvando…' : 'Adicionar entrega'}
              </button>
            </div>
          </form>
        ) : null}

        {intakeMode === 'scenario' ? (
          <form className="scenario-form" onSubmit={submitScenario}>
            <label>Perfil<select name="profile" defaultValue="NORMAL">{(Object.keys(scenarioLabels) as ScenarioProfile[]).map((profile) => <option key={profile} value={profile}>{scenarioLabels[profile]}</option>)}</select></label>
            <label>Quantidade<select name="delivery_count" defaultValue="20"><option value="20">20 · pequeno</option><option value="40">40 · médio</option><option value="60">60 · grande</option><option value="80">80 · stress</option></select></label>
            <label>Seed opcional<input name="seed" type="number" min="0" placeholder="Aleatória" /></label>
            <div className="scenario-explanation">
              <strong>Geração reproduzível</strong>
              <span>Destinos reais, distribuição ponderada por facilities e cargas correlacionadas.</span>
            </div>
            <button className="button button--primary" disabled={scenarioPending} type="submit">
              {scenarioPending ? 'Gerando…' : 'Gerar entregas'}
            </button>
          </form>
        ) : null}

        {intakeMode === 'import' ? (
          <div className="import-workspace">
            <form className="import-form" onSubmit={submitImport}>
              <label>Arquivo CSV ou XLSX<input name="file" type="file" accept=".csv,.xlsx" required /></label>
              <p>O arquivo é analisado antes de qualquer linha virar entrega. Endereços inexistentes são bloqueados.</p>
              <button className="button button--secondary" disabled={importPending} type="submit">
                {importPending ? 'Validando…' : 'Validar arquivo'}
              </button>
            </form>
            {importPreview ? (
              <div className="import-preview">
                <div className="import-preview-summary">
                  <strong>{importPreview.filename}</strong>
                  <span>{importPreview.summary.valid_rows} válidas · {importPreview.summary.warning_rows} avisos · {importPreview.summary.error_rows} erros</span>
                </div>
                <div className="import-row-list">
                  {importPreview.rows.slice(0, 8).map((row) => (
                    <div key={row.row_number} className={`import-row import-row--${row.status.toLowerCase()}`}>
                      <strong>Linha {row.row_number} · {row.status}</strong>
                      <span>{row.errors[0]?.message ?? row.warnings[0]?.message ?? String(row.normalized.destination_address ?? 'Linha pronta')}</span>
                    </div>
                  ))}
                </div>
                <button
                  className="button button--primary"
                  type="button"
                  disabled={importPending || importPreview.summary.error_rows > 0 || importPreview.status === 'CONFIRMED'}
                  onClick={() => void confirmImport()}
                >
                  {importPreview.status === 'CONFIRMED' ? 'Importação confirmada' : 'Confirmar linhas válidas'}
                </button>
              </div>
            ) : null}
          </div>
        ) : null}
      </section>

      <section className="deliveries-list-panel">
        <form className="delivery-filters" onSubmit={applyFilters}>
          <input aria-label="Buscar entregas" placeholder="Código, NF, destinatário ou rua" value={query} onChange={(event) => setQuery(event.target.value)} />
          <select aria-label="Filtrar por operação" value={operationFilter} onChange={(event) => setOperationFilter(event.target.value)}><option value="">Todas as operações</option>{operations.map((operation) => <option key={operation.id} value={operation.id}>{operation.operation_code}</option>)}</select>
          <select aria-label="Filtrar por prioridade" value={priorityFilter} onChange={(event) => setPriorityFilter(event.target.value as DeliveryPriority | '')}><option value="">Prioridade</option>{(Object.keys(priorityLabels) as DeliveryPriority[]).map((priority) => <option key={priority} value={priority}>{priorityLabels[priority]}</option>)}</select>
          <select aria-label="Filtrar por temperatura" value={temperatureFilter} onChange={(event) => setTemperatureFilter(event.target.value as TemperatureClass | '')}><option value="">Temperatura</option><option value="AMBIENT">Ambiente</option><option value="REFRIGERATED">Refrigerada</option></select>
          <select aria-label="Filtrar por status" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as DeliveryStatus | '')}><option value="">Status</option>{(Object.keys(statusLabels) as DeliveryStatus[]).map((deliveryStatus) => <option key={deliveryStatus} value={deliveryStatus}>{statusLabels[deliveryStatus]}</option>)}</select>
          <button className="button button--secondary" type="submit">Aplicar</button>
        </form>

        {loading ? <p className="deliveries-state">Carregando entregas…</p> : null}
        {!loading && deliveries.length === 0 ? <p className="deliveries-state">Nenhuma entrega corresponde aos filtros.</p> : null}
        {!loading && deliveries.length > 0 ? (
          <div className="deliveries-table-wrap">
            <table className="deliveries-table">
              <thead><tr><th>Entrega</th><th>Destino</th><th>Carga</th><th>Prioridade</th><th>Janela</th><th>Status</th><th /></tr></thead>
              <tbody>
                {deliveries.map((delivery) => (
                  <tr key={delivery.id}>
                    <td><strong>{delivery.delivery_code}</strong><span>NF {delivery.invoice_number}/{delivery.invoice_series}</span></td>
                    <td><strong>{delivery.recipient_name}</strong><span>{delivery.destination_address}</span></td>
                    <td>{delivery.package_count} vol.<span>{decimal(delivery.total_weight_kg)} kg · {decimal(delivery.total_volume_m3)} m³</span></td>
                    <td><span className={`priority-chip priority-chip--${delivery.priority.toLowerCase()}`}>{priorityLabels[delivery.priority]}</span></td>
                    <td>{dateTime(delivery.time_window_start)}<span>{delivery.time_window_policy}</span></td>
                    <td>{statusLabels[delivery.status]}</td>
                    <td><button className="table-link table-link--button" type="button" onClick={() => openDetail(delivery)}>Detalhes</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>

      {selectedDelivery ? (
        <aside className="delivery-detail" aria-label="Detalhes da entrega">
          <div className="delivery-detail-heading">
            <div><span>Entrega selecionada</span><strong>{selectedDelivery.delivery_code}</strong></div>
            <button type="button" aria-label="Fechar detalhes" onClick={() => setSelectedDelivery(null)}>×</button>
          </div>
          <dl>
            <div><dt>Destino</dt><dd>{selectedDelivery.destination_address}</dd></div>
            <div><dt>Destinatário</dt><dd>{selectedDelivery.recipient_name}</dd></div>
            <div><dt>Carga</dt><dd>{selectedDelivery.package_count} volumes · {decimal(selectedDelivery.total_weight_kg)} kg</dd></div>
            <div><dt>Temperatura</dt><dd>{selectedDelivery.temperature_class === 'REFRIGERATED' ? 'Refrigerada' : 'Ambiente'}</dd></div>
            <div><dt>Atendimento</dt><dd>{selectedDelivery.service_time_minutes} min · {selectedDelivery.service_time_source}</dd></div>
          </dl>
          <label>Prioridade<select value={editPriority} onChange={(event) => setEditPriority(event.target.value as DeliveryPriority)}>{(Object.keys(priorityLabels) as DeliveryPriority[]).map((priority) => <option key={priority} value={priority}>{priorityLabels[priority]}</option>)}</select></label>
          <div className="delivery-detail-actions">
            <button className="button button--secondary" disabled={editPending} type="button" onClick={() => void saveSelectedDelivery()}>Salvar alteração</button>
            <button className="button button--ghost delivery-delete" disabled={editPending} type="button" onClick={() => void removeSelectedDelivery()}>Excluir</button>
          </div>
        </aside>
      ) : null}
    </main>
  )
}
