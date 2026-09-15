import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import { listOperations } from '../../services/operations'
import { createReport, downloadReport, listReports, retryReport } from '../../services/reports'
import type { Operation } from '../../types/operations'
import type { ReportFormat, ReportItem } from '../../types/reports'
import './reports.css'

const reportFormats: Array<{ value: ReportFormat; label: string; description: string }> = [
  { value: 'PDF', label: 'PDF', description: 'Resumo operacional pronto para apresentação.' },
  { value: 'XLSX', label: 'XLSX', description: 'Planilha detalhada em seis abas.' },
  { value: 'CSV', label: 'CSV', description: 'Exportação tabular das entregas e rotas.' },
]

function dateTime(value: string): string {
  return new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(new Date(value))
}

function statusLabel(status: ReportItem['status']): string {
  if (status === 'COMPLETED') return 'Pronto'
  if (status === 'FAILED') return 'Falhou'
  return 'Gerando'
}

function eligible(operation: Operation): boolean {
  return ['OPTIMIZED', 'APPROVED', 'DISPATCHED'].includes(operation.status)
}

export function ReportsPage() {
  const [searchParams] = useSearchParams()
  const [operations, setOperations] = useState<Operation[]>([])
  const [reports, setReports] = useState<ReportItem[]>([])
  const [operationId, setOperationId] = useState(searchParams.get('operation_id') ?? '')
  const [format, setFormat] = useState<ReportFormat>('PDF')
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [downloadingId, setDownloadingId] = useState<string | null>(null)
  const [retryingId, setRetryingId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    setLoading(true)
    Promise.all([listOperations(), listReports()])
      .then(([operationPage, reportPage]) => {
        if (!active) return
        const validOperations = operationPage.items.filter(eligible)
        setOperations(validOperations)
        setReports(reportPage.items)
        setOperationId((current) => {
          if (current && validOperations.some((operation) => operation.id === current)) return current
          return validOperations[0]?.id ?? ''
        })
      })
      .catch((requestError: unknown) => {
        if (active) {
          setError(
            requestError instanceof Error
              ? requestError.message
              : 'Não foi possível carregar os relatórios.',
          )
        }
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [])

  const selectedOperation = useMemo(
    () => operations.find((operation) => operation.id === operationId) ?? null,
    [operationId, operations],
  )

  async function refreshReports() {
    const page = await listReports()
    setReports(page.items)
  }

  async function generate() {
    if (!operationId) return
    setCreating(true)
    setError(null)
    try {
      const report = await createReport(operationId, format)
      await refreshReports()
      if (report.status === 'FAILED') {
        setError(report.error_message ?? 'A geração do relatório falhou.')
      }
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Não foi possível gerar o relatório.',
      )
    } finally {
      setCreating(false)
    }
  }

  async function retry(report: ReportItem) {
    setRetryingId(report.id)
    setError(null)
    try {
      const retried = await retryReport(report.id)
      await refreshReports()
      if (retried.status === 'FAILED') {
        setError(retried.error_message ?? 'A nova tentativa de geração falhou.')
      }
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Não foi possível tentar gerar o relatório novamente.',
      )
    } finally {
      setRetryingId(null)
    }
  }

  async function download(report: ReportItem) {
    setDownloadingId(report.id)
    setError(null)
    try {
      await downloadReport(report)
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Não foi possível baixar o relatório.',
      )
    } finally {
      setDownloadingId(null)
    }
  }

  if (loading) return <section className="reports-state">Carregando relatórios…</section>

  return (
    <div className="reports-page">
      <header className="reports-heading">
        <div>
          <p className="eyebrow eyebrow--dark">Relatórios</p>
          <h1>Artefatos da operação</h1>
          <p>
            Gere arquivos a partir de um snapshot imutável do plano otimizado. O conteúdo de um
            relatório pronto não muda mesmo que a operação seja reotimizada depois.
          </p>
        </div>
      </header>

      <section className="reports-generator" aria-label="Gerar relatório">
        <div className="reports-generator__field">
          <label htmlFor="report-operation">Operação</label>
          <select
            id="report-operation"
            value={operationId}
            onChange={(event) => setOperationId(event.target.value)}
          >
            {operations.length === 0 ? <option value="">Nenhuma operação otimizada</option> : null}
            {operations.map((operation) => (
              <option key={operation.id} value={operation.id}>
                {operation.operation_code} · {operation.operation_date} · {operation.status}
              </option>
            ))}
          </select>
        </div>

        <div className="report-format-grid" role="radiogroup" aria-label="Formato do relatório">
          {reportFormats.map((item) => (
            <label
              key={item.value}
              className={format === item.value ? 'report-format is-selected' : 'report-format'}
            >
              <input
                type="radio"
                name="report-format"
                value={item.value}
                checked={format === item.value}
                onChange={() => setFormat(item.value)}
              />
              <strong>{item.label}</strong>
              <span>{item.description}</span>
            </label>
          ))}
        </div>

        <div className="reports-generator__footer">
          <div>
            {selectedOperation ? (
              <span>
                Revisão atual {selectedOperation.current_revision_number} ·{' '}
                {selectedOperation.city_name}
              </span>
            ) : (
              <span>Otimize uma operação antes de gerar arquivos.</span>
            )}
          </div>
          <button
            className="button button--primary"
            type="button"
            disabled={!operationId || creating}
            onClick={() => void generate()}
          >
            {creating ? 'Gerando…' : `Gerar ${format}`}
          </button>
        </div>
        {error ? <p className="form-error reports-error">{error}</p> : null}
      </section>

      <section className="reports-history" aria-label="Histórico de relatórios">
        <div className="reports-history__heading">
          <div>
            <p className="eyebrow eyebrow--dark">Histórico</p>
            <h2>Relatórios gerados</h2>
          </div>
          <span>{reports.length} arquivo(s)</span>
        </div>

        {reports.length === 0 ? (
          <div className="reports-state">Nenhum relatório foi gerado ainda.</div>
        ) : (
          <div className="reports-list">
            {reports.map((report) => {
              const operation = operations.find((item) => item.id === report.operation_id)
              return (
                <article className="report-card" key={report.id}>
                  <div className="report-card__format">{report.format}</div>
                  <div className="report-card__body">
                    <div>
                      <strong>{operation?.operation_code ?? 'Operação'}</strong>
                      <span>{report.filename ?? 'Arquivo indisponível'}</span>
                    </div>
                    <small>
                      {dateTime(report.created_at)} · snapshot do run{' '}
                      {report.optimization_run_id.slice(0, 8)}
                    </small>
                    {report.error_message ? (
                      <p className="form-error">{report.error_message}</p>
                    ) : null}
                  </div>
                  <span className={`report-status report-status--${report.status.toLowerCase()}`}>
                    {statusLabel(report.status)}
                  </span>
                  {report.status === 'FAILED' ? (
                    <button
                      className="button button--ghost"
                      type="button"
                      disabled={retryingId === report.id}
                      onClick={() => void retry(report)}
                    >
                      {retryingId === report.id ? 'Tentando…' : 'Tentar novamente'}
                    </button>
                  ) : (
                    <button
                      className="button button--ghost"
                      type="button"
                      disabled={report.status !== 'COMPLETED' || downloadingId === report.id}
                      onClick={() => void download(report)}
                    >
                      {downloadingId === report.id ? 'Baixando…' : 'Baixar'}
                    </button>
                  )}
                </article>
              )
            })}
          </div>
        )}
      </section>
    </div>
  )
}
