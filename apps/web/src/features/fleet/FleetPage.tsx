import { type FormEvent, useEffect, useMemo, useState } from 'react'

import {
  createVehicle,
  deactivateVehicle,
  listVehicles,
  updateVehicle,
} from '../../services/resources'
import type {
  HelperPolicy,
  Vehicle,
  VehicleCreateInput,
  VehicleOwnershipType,
  VehicleStatus,
  VehicleType,
} from '../../types/resources'

const vehicleTypeLabels: Record<VehicleType, string> = {
  MOTO: 'Moto',
  VAN_COMPACT: 'Van compacta',
  CARGO_VAN: 'Van de carga',
  LIGHT_TRUCK: 'Caminhão leve',
}

const statusLabels: Record<VehicleStatus, string> = {
  AVAILABLE: 'Disponível',
  UNAVAILABLE: 'Indisponível',
  MAINTENANCE: 'Manutenção',
  INACTIVE: 'Inativo',
}

function formatMoney(value: string | null) {
  if (value === null) return '—'
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    maximumFractionDigits: 2,
  }).format(Number(value))
}

function emptyForm(): VehicleCreateInput {
  return {
    plate: '',
    type: 'CARGO_VAN',
    ownership_type: 'OWNED',
    max_payload_kg: '1500',
    max_volume_m3: '8.5',
    max_range_km: '450',
    refrigerated: false,
    status: 'AVAILABLE',
    helper_policy: 'OPTIONAL',
    fuel_type: 'DIESEL',
    fuel_efficiency_km_per_l: '10',
    owned_cost: {
      acquisition_value_brl: '120000',
      residual_value_brl: '20000',
      useful_life_km: '200000',
      annual_ipva_brl: '2400',
      annual_insurance_brl: '3600',
      annual_fixed_costs_brl: '6000',
      expected_productive_hours_per_year: '2000',
      maintenance_items: [
        {
          name: 'Revisão preventiva',
          cost_brl: '1200',
          interval_km: '10000',
        },
      ],
    },
    aggregated_contract: null,
  }
}

export function FleetPage() {
  const [vehicles, setVehicles] = useState<Vehicle[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState<VehicleCreateInput>(() => emptyForm())

  async function reload() {
    setLoading(true)
    try {
      setVehicles(await listVehicles())
      setError(null)
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Falha ao carregar frota.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void reload()
  }, [])

  const summary = useMemo(() => {
    const active = vehicles.filter((item) => item.active)
    return {
      active: active.length,
      refrigerated: active.filter((item) => item.refrigerated).length,
      owned: active.filter((item) => item.ownership_type === 'OWNED').length,
      aggregated: active.filter((item) => item.ownership_type === 'AGGREGATED').length,
    }
  }, [vehicles])

  function setOwnership(ownership: VehicleOwnershipType) {
    setForm((current) => ({
      ...current,
      ownership_type: ownership,
      owned_cost:
        ownership === 'OWNED'
          ? current.owned_cost ?? emptyForm().owned_cost
          : null,
      aggregated_contract:
        ownership === 'AGGREGATED'
          ? current.aggregated_contract ?? {
              price_brl: '480',
              fuel_included: false,
              driver_included: false,
              helper_included: false,
            }
          : null,
    }))
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSaving(true)
    setError(null)
    try {
      await createVehicle(form)
      setForm(emptyForm())
      setShowForm(false)
      await reload()
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Falha ao cadastrar veículo.')
    } finally {
      setSaving(false)
    }
  }

  async function setStatus(vehicle: Vehicle, status: VehicleStatus) {
    try {
      await updateVehicle(vehicle.id, { status })
      await reload()
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Falha ao atualizar veículo.')
    }
  }

  async function deactivate(vehicle: Vehicle) {
    if (!window.confirm(`Inativar o veículo ${vehicle.plate}?`)) return
    try {
      await deactivateVehicle(vehicle.id)
      await reload()
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Falha ao inativar veículo.')
    }
  }

  return (
    <main className="content-page resources-page">
      <header className="page-heading resources-heading">
        <div>
          <p className="eyebrow eyebrow--dark">Recursos operacionais</p>
          <h1>Frota</h1>
          <p>Capacidade, autonomia, refrigeração e estrutura real de custos por veículo.</p>
        </div>
        <button
          className="button button--primary"
          type="button"
          onClick={() => setShowForm((value) => !value)}
        >
          {showForm ? 'Fechar cadastro' : 'Novo veículo'}
        </button>
      </header>

      <section className="resource-kpis" aria-label="Resumo da frota">
        <article><strong>{summary.active}</strong><span>ativos</span></article>
        <article><strong>{summary.refrigerated}</strong><span>refrigerados</span></article>
        <article><strong>{summary.owned}</strong><span>próprios</span></article>
        <article><strong>{summary.aggregated}</strong><span>agregados</span></article>
      </section>

      {showForm ? (
        <form className="resource-form" onSubmit={(event) => void submit(event)}>
          <div className="panel-heading">
            <div>
              <strong>Cadastrar veículo</strong>
              <span>Os custos informados serão usados pelo otimizador.</span>
            </div>
          </div>

          <div className="resource-form-grid">
            <label>
              Placa
              <input
                value={form.plate}
                onChange={(event) => setForm({ ...form, plate: event.target.value })}
                placeholder="ABC1D23"
                required
              />
            </label>
            <label>
              Tipo
              <select
                value={form.type}
                onChange={(event) => {
                  const type = event.target.value as VehicleType
                  setForm({
                    ...form,
                    type,
                    helper_policy: type === 'MOTO' ? 'FORBIDDEN' : form.helper_policy,
                  })
                }}
              >
                {Object.entries(vehicleTypeLabels).map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </label>
            <label>
              Propriedade
              <select
                value={form.ownership_type}
                onChange={(event) => setOwnership(event.target.value as VehicleOwnershipType)}
              >
                <option value="OWNED">Próprio</option>
                <option value="AGGREGATED">Agregado</option>
              </select>
            </label>
            <label>
              Capacidade de peso (kg)
              <input
                type="number"
                min="0.001"
                step="0.001"
                value={form.max_payload_kg}
                onChange={(event) => setForm({ ...form, max_payload_kg: event.target.value })}
                required
              />
            </label>
            <label>
              Capacidade de volume (m³)
              <input
                type="number"
                min="0.0001"
                step="0.0001"
                value={form.max_volume_m3}
                onChange={(event) => setForm({ ...form, max_volume_m3: event.target.value })}
                required
              />
            </label>
            <label>
              Autonomia máxima (km)
              <input
                type="number"
                min="0.01"
                step="0.01"
                value={form.max_range_km}
                onChange={(event) => setForm({ ...form, max_range_km: event.target.value })}
                required
              />
            </label>
            <label>
              Política de ajudante
              <select
                value={form.helper_policy}
                disabled={form.type === 'MOTO'}
                onChange={(event) =>
                  setForm({ ...form, helper_policy: event.target.value as HelperPolicy })
                }
              >
                <option value="FORBIDDEN">Proibido</option>
                <option value="OPTIONAL">Opcional</option>
                <option value="REQUIRED">Obrigatório</option>
              </select>
            </label>
            <label>
              Combustível
              <select
                value={form.fuel_type ?? ''}
                onChange={(event) =>
                  setForm({
                    ...form,
                    fuel_type: event.target.value
                      ? (event.target.value as VehicleCreateInput['fuel_type'])
                      : null,
                  })
                }
              >
                <option value="">Não informado</option>
                <option value="GASOLINE">Gasolina</option>
                <option value="ETHANOL">Etanol</option>
                <option value="DIESEL">Diesel</option>
                <option value="FLEX">Flex</option>
                <option value="OTHER">Outro</option>
              </select>
            </label>
            <label>
              Eficiência (km/l)
              <input
                type="number"
                min="0.001"
                step="0.001"
                value={form.fuel_efficiency_km_per_l ?? ''}
                onChange={(event) =>
                  setForm({ ...form, fuel_efficiency_km_per_l: event.target.value || null })
                }
              />
            </label>
            <label className="resource-checkbox">
              <input
                type="checkbox"
                checked={form.refrigerated}
                onChange={(event) => setForm({ ...form, refrigerated: event.target.checked })}
              />
              Refrigerado
            </label>
          </div>

          {form.ownership_type === 'OWNED' && form.owned_cost ? (
            <section className="resource-cost-editor">
              <h3>Estrutura de custo próprio</h3>
              <div className="resource-form-grid">
                {[
                  ['acquisition_value_brl', 'Valor de aquisição (R$)'],
                  ['residual_value_brl', 'Valor residual (R$)'],
                  ['useful_life_km', 'Vida útil (km)'],
                  ['annual_ipva_brl', 'IPVA anual (R$)'],
                  ['annual_insurance_brl', 'Seguro anual (R$)'],
                  ['annual_fixed_costs_brl', 'Outros custos fixos anuais (R$)'],
                  ['expected_productive_hours_per_year', 'Horas produtivas/ano'],
                ].map(([field, label]) => (
                  <label key={field}>
                    {label}
                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      value={form.owned_cost?.[field as keyof typeof form.owned_cost] as string}
                      onChange={(event) =>
                        setForm({
                          ...form,
                          owned_cost: {
                            ...form.owned_cost!,
                            [field]: event.target.value,
                          },
                        })
                      }
                      required
                    />
                  </label>
                ))}
              </div>
              <div className="maintenance-row">
                <label>
                  Manutenção
                  <input
                    value={form.owned_cost.maintenance_items[0]?.name ?? ''}
                    onChange={(event) =>
                      setForm({
                        ...form,
                        owned_cost: {
                          ...form.owned_cost!,
                          maintenance_items: [
                            {
                              ...form.owned_cost!.maintenance_items[0],
                              name: event.target.value,
                              cost_brl: form.owned_cost!.maintenance_items[0]?.cost_brl ?? '0',
                              interval_km: form.owned_cost!.maintenance_items[0]?.interval_km ?? '1',
                            },
                          ],
                        },
                      })
                    }
                  />
                </label>
                <label>
                  Custo (R$)
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={form.owned_cost.maintenance_items[0]?.cost_brl ?? ''}
                    onChange={(event) =>
                      setForm({
                        ...form,
                        owned_cost: {
                          ...form.owned_cost!,
                          maintenance_items: [
                            {
                              ...form.owned_cost!.maintenance_items[0],
                              name: form.owned_cost!.maintenance_items[0]?.name ?? 'Manutenção',
                              cost_brl: event.target.value,
                              interval_km: form.owned_cost!.maintenance_items[0]?.interval_km ?? '1',
                            },
                          ],
                        },
                      })
                    }
                  />
                </label>
                <label>
                  Intervalo (km)
                  <input
                    type="number"
                    min="1"
                    step="1"
                    value={form.owned_cost.maintenance_items[0]?.interval_km ?? ''}
                    onChange={(event) =>
                      setForm({
                        ...form,
                        owned_cost: {
                          ...form.owned_cost!,
                          maintenance_items: [
                            {
                              ...form.owned_cost!.maintenance_items[0],
                              name: form.owned_cost!.maintenance_items[0]?.name ?? 'Manutenção',
                              cost_brl: form.owned_cost!.maintenance_items[0]?.cost_brl ?? '0',
                              interval_km: event.target.value,
                            },
                          ],
                        },
                      })
                    }
                  />
                </label>
              </div>
            </section>
          ) : null}

          {form.ownership_type === 'AGGREGATED' && form.aggregated_contract ? (
            <section className="resource-cost-editor">
              <h3>Contrato agregado</h3>
              <div className="resource-form-grid">
                <label>
                  Preço por rota (R$)
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={form.aggregated_contract.price_brl}
                    onChange={(event) =>
                      setForm({
                        ...form,
                        aggregated_contract: {
                          ...form.aggregated_contract!,
                          price_brl: event.target.value,
                        },
                      })
                    }
                    required
                  />
                </label>
                {[
                  ['fuel_included', 'Combustível incluído'],
                  ['driver_included', 'Motorista incluído'],
                  ['helper_included', 'Ajudante incluído'],
                ].map(([field, label]) => (
                  <label className="resource-checkbox" key={field}>
                    <input
                      type="checkbox"
                      checked={Boolean(
                        form.aggregated_contract?.[
                          field as keyof typeof form.aggregated_contract
                        ],
                      )}
                      onChange={(event) =>
                        setForm({
                          ...form,
                          aggregated_contract: {
                            ...form.aggregated_contract!,
                            [field]: event.target.checked,
                          },
                        })
                      }
                    />
                    {label}
                  </label>
                ))}
              </div>
            </section>
          ) : null}

          {error ? <p className="form-error">{error}</p> : null}
          <div className="form-actions">
            <button className="button button--primary" type="submit" disabled={saving}>
              {saving ? 'Salvando…' : 'Cadastrar veículo'}
            </button>
          </div>
        </form>
      ) : null}

      {error && !showForm ? <p className="form-error">{error}</p> : null}

      {loading ? (
        <p className="operations-state">Carregando frota…</p>
      ) : vehicles.length === 0 ? (
        <section className="resource-empty">
          <strong>Nenhum veículo cadastrado.</strong>
          <span>Cadastre o primeiro recurso para preparar as operações.</span>
        </section>
      ) : (
        <section className="resource-list">
          {vehicles.map((vehicle) => (
            <article className={`resource-card ${!vehicle.active ? 'resource-card--inactive' : ''}`} key={vehicle.id}>
              <header>
                <div>
                  <span className="resource-badge">{vehicleTypeLabels[vehicle.type]}</span>
                  <h2>{vehicle.plate}</h2>
                  <p>{vehicle.ownership_type === 'OWNED' ? 'Próprio' : 'Agregado'}</p>
                </div>
                <span className={`resource-status resource-status--${vehicle.status.toLowerCase()}`}>
                  {statusLabels[vehicle.status]}
                </span>
              </header>

              <dl className="resource-spec-grid">
                <div><dt>Peso</dt><dd>{Number(vehicle.max_payload_kg).toLocaleString('pt-BR')} kg</dd></div>
                <div><dt>Volume</dt><dd>{vehicle.max_volume_m3} m³</dd></div>
                <div><dt>Autonomia</dt><dd>{vehicle.max_range_km} km</dd></div>
                <div><dt>Refrigeração</dt><dd>{vehicle.refrigerated ? 'Sim' : 'Não'}</dd></div>
                <div><dt>Ajudante</dt><dd>{vehicle.helper_policy}</dd></div>
                <div><dt>Combustível</dt><dd>{vehicle.fuel_type ?? '—'}</dd></div>
              </dl>

              <div className="resource-cost-view">
                <strong>Custo operacional</strong>
                {vehicle.ownership_type === 'OWNED' ? (
                  <div className="resource-cost-grid">
                    <span>Depreciação/km <b>{formatMoney(vehicle.cost.depreciation_per_km)}</b></span>
                    <span>Manutenção/km <b>{formatMoney(vehicle.cost.maintenance_per_km)}</b></span>
                    <span>Fixo/h <b>{formatMoney(vehicle.cost.fixed_cost_per_hour)}</b></span>
                  </div>
                ) : (
                  <div className="resource-cost-grid">
                    <span>Contrato/rota <b>{formatMoney(vehicle.cost.contract_price_brl)}</b></span>
                    <span>Combustível <b>{vehicle.cost.fuel_included ? 'incluído' : 'à parte'}</b></span>
                    <span>Motorista <b>{vehicle.cost.driver_included ? 'incluído' : 'à parte'}</b></span>
                  </div>
                )}
              </div>

              {vehicle.active ? (
                <footer className="resource-card-actions">
                  <button
                    className="button button--ghost"
                    type="button"
                    onClick={() =>
                      void setStatus(
                        vehicle,
                        vehicle.status === 'AVAILABLE' ? 'UNAVAILABLE' : 'AVAILABLE',
                      )
                    }
                  >
                    {vehicle.status === 'AVAILABLE' ? 'Marcar indisponível' : 'Marcar disponível'}
                  </button>
                  <button
                    className="button button--danger"
                    type="button"
                    onClick={() => void deactivate(vehicle)}
                  >
                    Inativar
                  </button>
                </footer>
              ) : null}
            </article>
          ))}
        </section>
      )}
    </main>
  )
}
