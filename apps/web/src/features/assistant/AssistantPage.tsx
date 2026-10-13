import { FormEvent, useEffect, useMemo, useState } from 'react'

import { getAssistantStatus, sendAssistantMessage } from '../../services/assistant'
import { listOperations } from '../../services/operations'
import type {
  AssistantHistoryMessageInput,
  AssistantStatus,
  AssistantToolCall,
} from '../../types/assistant'
import type { Operation } from '../../types/operations'
import './assistant.css'

interface ChatMessage {
  id: string
  role: 'assistant' | 'user'
  content: string
  toolCalls?: AssistantToolCall[]
  providerLabel?: string
}

type CopyState = 'idle' | 'copied' | 'error'

const suggestedQuestions = [
  'Qual o custo total da operação?',
  'Por que o veículo foi escolhido para a primeira rota?',
  'Gere instruções para o motorista da primeira rota.',
  'Gere um relatório diário da operação.',
  'Simule remover o ajudante da primeira rota.',
]

function operationEligible(operation: Operation): boolean {
  return ['OPTIMIZED', 'APPROVED', 'DISPATCHED'].includes(operation.status)
}

function statusLabel(status: AssistantStatus | null): string {
  if (status === null) return 'Verificando…'
  return status.status === 'HEALTHY' ? 'Configurado' : 'Temporariamente indisponível'
}

function formatHistory(operation: Operation | null, messages: ChatMessage[]): string {
  const conversation = messages.filter((message) => message.id !== 'welcome')
  const lines = ['# FluxMed — Histórico do Assistente IA', '']

  if (operation) {
    lines.push(
      `**Operação:** ${operation.operation_code}`,
      `**Data:** ${operation.operation_date}`,
      `**Status:** ${operation.status}`,
      `**Revisão:** ${operation.current_revision_number}`,
      `**Cidade:** ${operation.city_name}`,
      '',
    )
  }

  if (conversation.length === 0) {
    lines.push('_Nenhuma interação registrada nesta conversa._')
    return lines.join('\n')
  }

  for (const message of conversation) {
    lines.push(`## ${message.role === 'assistant' ? 'FluxMed IA' : 'Você'}`, '')
    if (message.providerLabel) {
      lines.push(`_Provider: ${message.providerLabel}_`, '')
    }
    lines.push(message.content.trim())
    if (message.toolCalls && message.toolCalls.length > 0) {
      lines.push(
        '',
        `**Fontes estruturadas:** ${message.toolCalls
          .map((tool) => `${tool.name} (${tool.status})`)
          .join(', ')}`,
      )
    }
    lines.push('')
  }

  return lines.join('\n').trim()
}

function compactConversationContent(content: string): string {
  const clean = content.trim()
  if (clean.length <= 2000) return clean
  return `${clean.slice(0, 1000).trimEnd()} … ${clean.slice(-1000).trimStart()}`
}

function conversationHistory(messages: ChatMessage[]): AssistantHistoryMessageInput[] {
  return messages
    .filter((message) => message.id !== 'welcome')
    .slice(-8)
    .map((message) => ({
      role: message.role,
      content: compactConversationContent(message.content),
    }))
}

export function AssistantPage() {
  const [operations, setOperations] = useState<Operation[]>([])
  const [operationId, setOperationId] = useState('')
  const [assistantStatus, setAssistantStatus] = useState<AssistantStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [input, setInput] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [copyState, setCopyState] = useState<CopyState>('idle')
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content:
        'Selecione uma operação otimizada e faça uma pergunta. Eu consulto dados estruturados do FluxMed antes de afirmar métricas operacionais.',
    },
  ])

  useEffect(() => {
    let active = true
    Promise.all([listOperations(), getAssistantStatus()])
      .then(([operationPage, status]) => {
        if (!active) return
        const eligible = operationPage.items.filter(operationEligible)
        setOperations(eligible)
        setOperationId(eligible[0]?.id ?? '')
        setAssistantStatus(status)
      })
      .catch((requestError: unknown) => {
        if (!active) return
        setError(
          requestError instanceof Error
            ? requestError.message
            : 'Não foi possível iniciar o Assistente IA.',
        )
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

  async function ask(message: string) {
    const cleanMessage = message.trim()
    if (!cleanMessage || !operationId || sending) return

    const history = conversationHistory(messages)
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: cleanMessage,
    }
    setMessages((current) => [...current, userMessage])
    setInput('')
    setSending(true)
    setError(null)
    setCopyState('idle')

    try {
      const response = await sendAssistantMessage({
        message: cleanMessage,
        context: { operation_id: operationId },
        history,
      })
      setMessages((current) => [
        ...current,
        {
          id: response.request_id,
          role: 'assistant',
          content: response.message,
          toolCalls: response.tool_calls,
          providerLabel: `${response.provider} · ${response.model}`,
        },
      ])
    } catch (requestError: unknown) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Não foi possível obter uma resposta do Assistente IA.',
      )
    } finally {
      setSending(false)
    }
  }

  async function copyHistory() {
    const clipboard = navigator.clipboard
    if (!clipboard?.writeText) {
      setCopyState('error')
      return
    }

    try {
      await clipboard.writeText(formatHistory(selectedOperation, messages))
      setCopyState('copied')
    } catch {
      setCopyState('error')
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    void ask(input)
  }

  if (loading) return <section className="assistant-state">Carregando Assistente IA…</section>

  return (
    <div className="assistant-page">
      <header className="assistant-heading">
        <div>
          <p className="eyebrow eyebrow--dark">Assistente IA</p>
          <h1>Explique o plano com dados validados</h1>
          <p>
            O assistente interpreta dados estruturados do FluxMed. Ele não recalcula custos, não
            substitui o otimizador e não aplica alterações automaticamente.
          </p>
        </div>
        <div
          className={
            assistantStatus?.status === 'HEALTHY'
              ? 'assistant-status assistant-status--healthy'
              : 'assistant-status assistant-status--degraded'
          }
        >
          <span aria-hidden="true" />
          <div>
            <strong>Assistente IA · {statusLabel(assistantStatus)}</strong>
            {assistantStatus ? (
              <small>
                {assistantStatus.provider} · {assistantStatus.model}
              </small>
            ) : null}
          </div>
        </div>
      </header>

      <section className="assistant-context" aria-label="Contexto do assistente">
        <label htmlFor="assistant-operation">Operação em contexto</label>
        <select
          id="assistant-operation"
          value={operationId}
          onChange={(event) => {
            setOperationId(event.target.value)
            setMessages((current) => current.slice(0, 1))
            setCopyState('idle')
          }}
        >
          {operations.length === 0 ? <option value="">Nenhuma operação otimizada</option> : null}
          {operations.map((operation) => (
            <option key={operation.id} value={operation.id}>
              {operation.operation_code} · {operation.operation_date} · {operation.status}
            </option>
          ))}
        </select>
        {selectedOperation ? (
          <span>
            Revisão {selectedOperation.current_revision_number} · {selectedOperation.city_name}
          </span>
        ) : (
          <span>Otimize uma operação para habilitar perguntas operacionais.</span>
        )}
      </section>

      <div className="assistant-layout">
        <aside className="assistant-suggestions" aria-label="Perguntas sugeridas">
          <p className="eyebrow eyebrow--dark">Comece por aqui</p>
          <h2>Demonstração da Fase 16</h2>
          <p>
            As sugestões exercitam pergunta factual, explicação, instruções, relatório e simulação
            sem aplicar mudanças ao plano.
          </p>
          <div className="assistant-suggestion-list">
            {suggestedQuestions.map((question) => (
              <button
                key={question}
                type="button"
                disabled={!operationId || sending || assistantStatus?.status === 'DEGRADED'}
                onClick={() => void ask(question)}
              >
                {question}
              </button>
            ))}
          </div>
          <div className="assistant-guardrail">
            <strong>Dados antes da narrativa</strong>
            <span>
              Métricas vêm das tools do backend. O modelo apenas interpreta e redige a resposta.
            </span>
          </div>
        </aside>

        <section className="assistant-chat" aria-label="Conversa com Assistente IA">
          <div className="assistant-chat__toolbar">
            <button
              type="button"
              className="assistant-copy-button"
              disabled={messages.length <= 1}
              onClick={() => void copyHistory()}
              title="Copiar conversa em Markdown para análise ou compartilhamento"
            >
              {copyState === 'copied' ? 'Copiado' : 'Copiar histórico'}
            </button>
            <span className="assistant-copy-status" aria-live="polite">
              {copyState === 'error' ? 'Não foi possível copiar.' : ''}
            </span>
          </div>

          <div className="assistant-messages" aria-live="polite">
            {messages.map((message) => (
              <article
                key={message.id}
                className={`assistant-message assistant-message--${message.role}`}
              >
                <div className="assistant-message__label">
                  <strong>{message.role === 'assistant' ? 'FluxMed IA' : 'Você'}</strong>
                  {message.providerLabel ? <span>{message.providerLabel}</span> : null}
                </div>
                <p>{message.content}</p>
                {message.toolCalls && message.toolCalls.length > 0 ? (
                  <div className="assistant-tool-source">
                    Fonte estruturada:{' '}
                    {message.toolCalls.map((tool) => `${tool.name} (${tool.status})`).join(', ')}
                  </div>
                ) : null}
              </article>
            ))}
            {sending ? (
              <article className="assistant-message assistant-message--assistant">
                <div className="assistant-message__label">
                  <strong>FluxMed IA</strong>
                </div>
                <p>Consultando dados estruturados…</p>
              </article>
            ) : null}
          </div>

          {error ? <p className="form-error assistant-error">{error}</p> : null}

          <form className="assistant-composer" onSubmit={submit}>
            <label htmlFor="assistant-input">Pergunte sobre a operação selecionada</label>
            <div className="assistant-composer__row">
              <textarea
                id="assistant-input"
                rows={3}
                maxLength={4000}
                placeholder="Ex.: Qual o custo total da operação?"
                value={input}
                onChange={(event) => setInput(event.target.value)}
                disabled={!operationId || sending || assistantStatus?.status === 'DEGRADED'}
              />
              <button
                className="button button--primary"
                type="submit"
                disabled={
                  !operationId ||
                  !input.trim() ||
                  sending ||
                  assistantStatus?.status === 'DEGRADED'
                }
              >
                {sending ? 'Consultando…' : 'Enviar'}
              </button>
            </div>
          </form>
        </section>
      </div>
    </div>
  )
}
