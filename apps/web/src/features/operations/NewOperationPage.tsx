import { type FormEvent, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { listCities } from '../../services/cities'
import {
  confirmDeliveryImport,
  createDelivery,
  createDeliveryImport,
  generateScenario,
  listDeliveries,
} from '../../services/deliveries'
import {
  createOperation,
  updateOperation,
  validateOperation,
} from '../../services/operations'
import type { AddressMatch } from '../../types/city'
import type {
  Delivery,
  DeliveryImport,
  DeliveryPriority,
  ScenarioProfile,
  TemperatureClass,
} from '../../types/deliveries'
import type { Operation, PreflightResponse, TrafficMode } from '../../types/operations'
import { AddressAutocomplete } from '../city/AddressAutocomplete'
import { OperationResourcesPanel } from '../resources/OperationResourcesPanel'

type WizardStep = 1 | 2 | 3 | 4
type DeliverySource = 'scenario' | 'import' | 'existing' | 'manual'

const stepLabels = ['Configuração', 'Entregas', 'Recursos', 'Revisão'] as const

function localDate(): string {
  const now = new Date()
  const offset = now.getTimezoneOffset() * 60_000
  return new Date(now.getTime() - offset).toISOString().slice(0, 10)
}

function decimal(value: string): string {
  return Number(value).toLocaleString('pt-BR', { maximumFractionDigits: 2 })
}

export function NewOperationPage() {
  const navigate = useNavigate()
  const [step, setStep] = useState<WizardStep>(1)
  const [operation, setOperation] = useState<Operation | null>(null)
  const [operationDate, setOperationDate] = useState(localDate())
  const [startTime, setStartTime] = useState('07:30')
  const [endTime, setEndTime] = useState('18:00')
  const [trafficMode, setTrafficMode] = useState<TrafficMode>('AUTOMATIC')
  const [deliverySource, setDeliverySource] = useState<DeliverySource>('scenario')
  const [deliveries, setDeliveries] = useState<Delivery[]>([])
  const [cityId, setCityId] = useState('')
  const [selectedAddress, setSelectedAddress] = useState<AddressMatch | null>(null)
  const [scenarioProfile, setScenarioProfile] = useState<ScenarioProfile>('NORMAL')
  const [scenarioCount, setScenarioCount] = useState(20)
  const [scenarioSeed, setScenarioSeed] = useState('')
  const [importPreview, setImportPreview] = useState<DeliveryImport | null>(null)
  const [preflight, setPreflight] = useState<PreflightResponse | null>(null)
  const [pending, setPending] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    void listCities()
      .then((cities) => {
        if (!active) return
        const santaAurora = cities.find((city) => city.name === 'Santa Aurora') ?? cities[0]
        if (santaAurora) setCityId(santaAurora.id)
      })
      .catch(() => {
        if (active) setCityId('')
      })
    return () => {
      active = false
    }
  }, [])

  const deliverySummary = useMemo(
    () => ({
      total: deliveries.length,
      weight: deliveries.reduce((sum, item) => sum + Number(item.total_weight_kg), 0),
      volume: deliveries.reduce((sum, item) => sum + Number(item.total_volume_m3), 0),
      critical: deliveries.filter((item) => item.priority === 'CRITICAL').length,
      refrigerated: deliveries.filter((item) => item.temperature_class === 'REFRIGERATED').length,
      hard: deliveries.filter((item) => item.time_window_policy === 'HARD').length,
      twoPerson: deliveries.filter((item) => item.handling_requirement === 'TWO_PERSON').length,
    }),
    [deliveries],
  )

  async function loadDeliveries(operationId: string) {
    const result = await listDeliveries({ operation_id: operationId })
    setDeliveries(result.items)
  }

  async function saveConfiguration(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (endTime <= startTime) {
      setError('O horário final deve ser posterior ao horário inicial.')
      return
    }

    setPending(true)
    setError(null)
    setMessage(null)
    try {
      const payload = {
        operation_date: operationDate,
        operation_start_time: `${startTime}:00`,
        operation_end_time: `${endTime}:00`,
        traffic_mode: trafficMode,
      }
      const saved = operation
        ? await updateOperation(operation.id, payload)
        : await createOperation(payload)
      setOperation(saved)
      await loadDeliveries(saved.id)
      setStep(2)
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Não foi possível salvar a configuração.',
      )
    } finally {
      setPending(false)
    }
  }

  async function submitScenario(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!operation) return
    setPending(true)
    setError(null)
    setMessage(null)
    try {
      const result = await generateScenario(operation.id, {
        profile: scenarioProfile,
        delivery_count: scenarioCount,
        ...(scenarioSeed ? { random_seed: Number(scenarioSeed) } : {}),
      })
      setDeliveries(result.deliveries)
      setMessage(
        `${result.summary.generated_count} entregas geradas com seed ${result.seed}. ${result.validation.message}`,
      )
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Falha ao gerar cenário.')
    } finally {
      setPending(false)
    }
  }

  async function submitImport(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!operation) return
    const form = new FormData(event.currentTarget)
    const file = form.get('file')
    if (!(file instanceof File) || file.size === 0) {
      setError('Selecione um arquivo CSV ou XLSX.')
      return
    }
    setPending(true)
    setError(null)
    try {
      setImportPreview(await createDeliveryImport(operation.id, file))
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Falha ao validar arquivo.')
    } finally {
      setPending(false)
    }
  }

  async function confirmImport() {
    if (!operation || !importPreview) return
    setPending(true)
    setError(null)
    try {
      const confirmed = await confirmDeliveryImport(importPreview.id)
      setImportPreview(confirmed)
      await loadDeliveries(operation.id)
      setMessage('Importação confirmada e vinculada à operação.')
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Falha ao confirmar importação.')
    } finally {
      setPending(false)
    }
  }

  async function submitManual(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!operation || !selectedAddress) {
      setError('Selecione um endereço válido em Santa Aurora.')
      return
    }
    const form = new FormData(event.currentTarget)
    setPending(true)
    setError(null)
    try {
      const created = await createDelivery(operation.id, {
        invoice_number: String(form.get('invoice_number') ?? ''),
        invoice_series: String(form.get('invoice_series') ?? ''),
        issuer_document: String(form.get('issuer_document') ?? ''),
        recipient_name: String(form.get('recipient_name') ?? ''),
        destination_address_id: selectedAddress.id,
        package_count: Number(form.get('package_count')),
        total_weight_kg: String(form.get('total_weight_kg') ?? ''),
        total_volume_m3: String(form.get('total_volume_m3') ?? ''),
        priority: String(form.get('priority')) as DeliveryPriority,
        time_window_policy: 'SOFT',
        temperature_class: String(form.get('temperature_class')) as TemperatureClass,
        handling_requirement: form.get('two_person') === 'on' ? 'TWO_PERSON' : 'STANDARD',
      })
      setDeliveries((current) => [...current, created])
      setSelectedAddress(null)
      event.currentTarget.reset()
      setMessage(`${created.delivery_code} adicionada à operação.`)
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Falha ao cadastrar entrega.')
    } finally {
      setPending(false)
    }
  }

  async function refreshExisting() {
    if (!operation) return
    setPending(true)
    setError(null)
    try {
      await loadDeliveries(operation.id)
      setMessage('Entregas cadastradas atualizadas.')
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Falha ao carregar entregas.')
    } finally {
      setPending(false)
    }
  }

  function continueToResources() {
    if (deliveries.length === 0) {
      setError('Adicione ao menos uma entrega para continuar.')
      return
    }
    setError(null)
    setMessage(null)
    setStep(3)
  }

  async function openReview() {
    if (!operation) return
    setStep(4)
    setPending(true)
    setError(null)
    setMessage(null)
    try {
      const result = await validateOperation(operation.id)
      setPreflight(result)
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Falha ao validar operação.')
    } finally {
      setPending(false)
    }
  }

  return (
    <main className="content-page operation-wizard-page">
      <header className="page-heading operations-heading">
        <div>
          <p className="eyebrow eyebrow--dark">Operações · preparação</p>
          <h1>{operation ? operation.operation_code : 'Nova operação'}</h1>
          <p>Prepare demanda e recursos, revise os bloqueios e só então libere a otimização.</p>
        </div>
        <Link className="button button--ghost button-link" to="/operations">
          Sair do wizard
        </Link>
      </header>

      <ol className="wizard-steps" aria-label="Etapas da operação">
        {stepLabels.map((label, index) => {
          const number = (index + 1) as WizardStep
          return (
            <li
              key={label}
              className={number === step ? 'wizard-step wizard-step--active' : number < step ? 'wizard-step wizard-step--complete' : 'wizard-step'}
            >
              <span>{number}</span>
              <strong>{label}</strong>
            </li>
          )
        })}
      </ol>

      {message ? <p className="delivery-feedback delivery-feedback--success">{message}</p> : null}
      {error ? <p className="delivery-feedback delivery-feedback--error">{error}</p> : null}

      {step === 1 ? (
        <form className="wizard-card" onSubmit={(event) => void saveConfiguration(event)}>
          <div className="form-section-heading">
            <span>01</span>
            <div>
              <strong>Configuração</strong>
              <p>Defina a janela operacional de Santa Aurora antes de carregar a demanda.</p>
            </div>
          </div>
          <div className="operation-form-grid">
            <label>
              Data da operação
              <input type="date" value={operationDate} onChange={(event) => setOperationDate(event.target.value)} required />
            </label>
            <label>
              Cidade
              <input value="Santa Aurora" readOnly />
            </label>
            <label>
              Depósito
              <input value="Centro de Distribuição FluxMed" readOnly />
            </label>
            <label>
              Horário de saída
              <input type="time" value={startTime} onChange={(event) => setStartTime(event.target.value)} required />
            </label>
            <label>
              Encerramento máximo
              <input type="time" value={endTime} onChange={(event) => setEndTime(event.target.value)} required />
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
          <div className="form-actions">
            <button className="button button--primary" type="submit" disabled={pending}>
              {pending ? 'Salvando…' : 'Salvar e continuar'}
            </button>
          </div>
        </form>
      ) : null}

      {step === 2 && operation ? (
        <section className="wizard-card">
          <div className="form-section-heading">
            <span>02</span>
            <div>
              <strong>Entregas</strong>
              <p>Escolha a fonte da demanda. Todos os caminhos persistem Delivery real.</p>
            </div>
          </div>

          <div className="wizard-source-grid" role="radiogroup" aria-label="Fonte das entregas">
            {([
              ['scenario', 'Gerar cenário'],
              ['import', 'Importar arquivo'],
              ['existing', 'Já cadastradas'],
              ['manual', 'Adicionar manualmente'],
            ] as const).map(([value, label]) => (
              <button
                key={value}
                className={deliverySource === value ? 'wizard-source wizard-source--active' : 'wizard-source'}
                type="button"
                role="radio"
                aria-checked={deliverySource === value}
                onClick={() => {
                  setDeliverySource(value)
                  setMessage(null)
                  setError(null)
                }}
              >
                {label}
              </button>
            ))}
          </div>

          {deliverySource === 'scenario' ? (
            <form className="wizard-inline-form" onSubmit={(event) => void submitScenario(event)}>
              <label>
                Perfil
                <select value={scenarioProfile} onChange={(event) => setScenarioProfile(event.target.value as ScenarioProfile)}>
                  <option value="NORMAL">Normal</option>
                  <option value="BUSY">Movimentado</option>
                  <option value="HIGH_PRESSURE">Alta pressão</option>
                  <option value="EMERGENCY">Emergência</option>
                </select>
              </label>
              <label>
                Quantidade
                <select value={scenarioCount} onChange={(event) => setScenarioCount(Number(event.target.value))}>
                  <option value={20}>20</option>
                  <option value={40}>40</option>
                  <option value={60}>60</option>
                  <option value={80}>80</option>
                </select>
              </label>
              <label>
                Seed avançada
                <input type="number" value={scenarioSeed} onChange={(event) => setScenarioSeed(event.target.value)} placeholder="Automática" />
              </label>
              <button className="button button--secondary" type="submit" disabled={pending}>
                {pending ? 'Gerando…' : 'Gerar cenário'}
              </button>
            </form>
          ) : null}

          {deliverySource === 'import' ? (
            <div className="wizard-import-block">
              <form className="wizard-inline-form" onSubmit={(event) => void submitImport(event)}>
                <label className="field-span">
                  Arquivo CSV ou XLSX
                  <input name="file" type="file" accept=".csv,.xlsx" required />
                </label>
                <button className="button button--secondary" type="submit" disabled={pending}>
                  Validar arquivo
                </button>
              </form>
              {importPreview ? (
                <div className="wizard-import-preview">
                  <strong>{importPreview.filename}</strong>
                  <span>{importPreview.summary.valid_rows} válidas · {importPreview.summary.warning_rows} avisos · {importPreview.summary.error_rows} erros</span>
                  <button
                    className="button button--primary"
                    type="button"
                    disabled={pending || importPreview.summary.error_rows > 0 || importPreview.status === 'CONFIRMED'}
                    onClick={() => void confirmImport()}
                  >
                    {importPreview.status === 'CONFIRMED' ? 'Importação confirmada' : 'Confirmar importação'}
                  </button>
                </div>
              ) : null}
            </div>
          ) : null}

          {deliverySource === 'existing' ? (
            <div className="wizard-existing-block">
              <p>Use as entregas que já estão vinculadas a {operation.operation_code}.</p>
              <button className="button button--secondary" type="button" disabled={pending} onClick={() => void refreshExisting()}>
                Atualizar entregas cadastradas
              </button>
            </div>
          ) : null}

          {deliverySource === 'manual' ? (
            <form className="wizard-manual-form" onSubmit={(event) => void submitManual(event)}>
              <div className="operation-form-grid">
                <label>NF<input name="invoice_number" required /></label>
                <label>Série<input name="invoice_series" required defaultValue="1" /></label>
                <label>Documento emissor<input name="issuer_document" required /></label>
                <label>Destinatário<input name="recipient_name" required /></label>
                <label>Volumes<input name="package_count" type="number" min="1" defaultValue="1" required /></label>
                <label>Peso total (kg)<input name="total_weight_kg" type="number" min="0.001" step="0.001" required /></label>
                <label>Volume total (m³)<input name="total_volume_m3" type="number" min="0.0001" step="0.0001" required /></label>
                <label>Prioridade<select name="priority" defaultValue="NORMAL"><option value="CRITICAL">Crítica</option><option value="HIGH">Alta</option><option value="NORMAL">Normal</option><option value="LOW">Baixa</option></select></label>
                <label>Temperatura<select name="temperature_class" defaultValue="AMBIENT"><option value="AMBIENT">Ambiente</option><option value="REFRIGERATED">Refrigerada</option></select></label>
                <label className="wizard-check"><input name="two_person" type="checkbox" /> Exige duas pessoas</label>
              </div>
              <AddressAutocomplete cityId={cityId} onSelect={setSelectedAddress} />
              <p className="wizard-address-selection">{selectedAddress?.formatted ?? 'Nenhum endereço selecionado.'}</p>
              <button className="button button--secondary" type="submit" disabled={pending || !selectedAddress}>Adicionar entrega</button>
            </form>
          ) : null}

          <div className="wizard-demand-summary" aria-label="Resumo da demanda">
            <article><strong>{deliverySummary.total}</strong><span>entregas</span></article>
            <article><strong>{decimal(String(deliverySummary.weight))} kg</strong><span>peso</span></article>
            <article><strong>{decimal(String(deliverySummary.volume))} m³</strong><span>volume</span></article>
            <article><strong>{deliverySummary.critical}</strong><span>críticas</span></article>
            <article><strong>{deliverySummary.refrigerated}</strong><span>refrigeradas</span></article>
            <article><strong>{deliverySummary.hard}</strong><span>janelas HARD</span></article>
            <article><strong>{deliverySummary.twoPerson}</strong><span>duas pessoas</span></article>
          </div>

          <div className="form-actions form-actions--between">
            <button className="button button--ghost" type="button" onClick={() => setStep(1)}>Voltar</button>
            <button className="button button--primary" type="button" disabled={deliveries.length === 0} onClick={continueToResources}>Continuar para recursos</button>
          </div>
        </section>
      ) : null}

      {step === 3 && operation ? (
        <section className="wizard-card">
          <div className="form-section-heading">
            <span>03</span>
            <div>
              <strong>Recursos</strong>
              <p>Selecione frota e equipe disponíveis. O preflight fará a validação final.</p>
            </div>
          </div>
          <OperationResourcesPanel operationId={operation.id} />
          <div className="form-actions form-actions--between">
            <button className="button button--ghost" type="button" onClick={() => setStep(2)}>Voltar</button>
            <button className="button button--primary" type="button" onClick={() => void openReview()}>Ir para revisão</button>
          </div>
        </section>
      ) : null}

      {step === 4 && operation ? (
        <section className="wizard-card wizard-review-card">
          <div className="form-section-heading">
            <span>04</span>
            <div>
              <strong>Revisão e preflight</strong>
              <p>O backend verifica bloqueios reais antes de liberar o plano para otimização.</p>
            </div>
          </div>

          {pending ? <p className="operations-state">Validando operação…</p> : null}
          {preflight ? (
            <>
              <div className="wizard-review-kpis">
                <article><strong>{preflight.summary.delivery_count}</strong><span>entregas</span></article>
                <article><strong>{preflight.summary.vehicle_count}</strong><span>veículos</span></article>
                <article><strong>{preflight.summary.worker_count}</strong><span>pessoas</span></article>
                <article><strong>{preflight.summary.critical_count}</strong><span>críticas</span></article>
                <article><strong>{preflight.summary.refrigerated_count}</strong><span>refrigeradas</span></article>
                <article><strong>{preflight.summary.hard_window_count}</strong><span>HARD</span></article>
                <article><strong>{preflight.summary.operation_window_minutes} min</strong><span>janela</span></article>
              </div>

              <div className={preflight.status === 'VALID' ? 'preflight-status preflight-status--valid' : 'preflight-status preflight-status--invalid'}>
                <strong>{preflight.status === 'VALID' ? 'Operação pronta para otimização' : 'Operação com bloqueios'}</strong>
                <span>{preflight.status === 'VALID' ? 'Nenhuma restrição bloqueante foi encontrada.' : 'Corrija os itens abaixo e valide novamente.'}</span>
              </div>

              {preflight.blocking_errors.length > 0 ? (
                <div className="preflight-list preflight-list--blocking">
                  <h3>Bloqueios</h3>
                  {preflight.blocking_errors.map((issue, index) => (
                    <article key={`${issue.code}-${index}`}><strong>{issue.code}</strong><span>{issue.message}</span></article>
                  ))}
                </div>
              ) : null}

              {preflight.warnings.length > 0 ? (
                <div className="preflight-list preflight-list--warning">
                  <h3>Avisos</h3>
                  {preflight.warnings.map((issue, index) => (
                    <article key={`${issue.code}-${index}`}><strong>{issue.code}</strong><span>{issue.message}</span></article>
                  ))}
                </div>
              ) : null}
            </>
          ) : null}

          <div className="form-actions form-actions--between">
            <button className="button button--ghost" type="button" onClick={() => setStep(3)}>Voltar aos recursos</button>
            <div className="wizard-final-actions">
              <button className="button button--secondary" type="button" disabled={pending} onClick={() => void openReview()}>Validar novamente</button>
              <button
                className="button button--primary"
                type="button"
                disabled={!preflight || preflight.status !== 'VALID'}
                onClick={() => navigate(`/operations/${operation.id}`)}
              >
                Otimizar rotas
              </button>
            </div>
          </div>
          {preflight?.status === 'VALID' ? (
            <p className="wizard-phase-note">A preparação está concluída. O clique abre o planejamento da operação; o motor GA será conectado na Fase 11, sem simular uma otimização inexistente.</p>
          ) : null}
        </section>
      ) : null}
    </main>
  )
}
