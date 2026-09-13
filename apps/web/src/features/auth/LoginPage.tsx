import { type FormEvent, useState } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'

import { ApiClientError } from '../../services/api'
import { useAuth } from './AuthContext'

const DEMO_EMAIL = import.meta.env.VITE_DEMO_EMAIL ?? 'planner@fluxmed.demo'
const DEMO_PASSWORD = import.meta.env.VITE_DEMO_PASSWORD ?? 'FluxMedDemo2026!'

interface LocationState {
  from?: { pathname?: string }
}

export function LoginPage() {
  const { login, status } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  if (status === 'authenticated') return <Navigate to="/operations" replace />

  const from = (location.state as LocationState | null)?.from?.pathname ?? '/operations'

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await login(email, password)
      navigate(from, { replace: true })
    } catch (caught) {
      if (caught instanceof ApiClientError) setError(caught.message)
      else setError('Não foi possível conectar ao FluxMed. Tente novamente.')
    } finally {
      setSubmitting(false)
    }
  }

  function useDemoAccess() {
    setEmail(DEMO_EMAIL)
    setPassword(DEMO_PASSWORD)
    setError(null)
  }

  return (
    <main className="login-page">
      <section className="login-brand-panel" aria-label="FluxMed">
        <div className="brand-mark">FM</div>
        <div>
          <p className="eyebrow">Planejamento logístico médico</p>
          <h1>FluxMed</h1>
          <p className="login-brand-copy">
            Planeje operações médicas com rotas otimizadas, restrições reais e decisões
            operacionais explicáveis.
          </p>
        </div>
        <div className="login-brand-note">
          <span className="status-pulse" aria-hidden="true" />
          Ambiente acadêmico de demonstração
        </div>
      </section>

      <section className="login-form-panel">
        <div className="login-card">
          <div className="login-heading">
            <p className="eyebrow eyebrow--dark">Acesso operacional</p>
            <h2>Acesse o FluxMed</h2>
            <p>Entre com uma conta autorizada para iniciar o planejamento.</p>
          </div>

          <form onSubmit={handleSubmit} className="login-form">
            <label>
              <span>E-mail</span>
              <input
                type="email"
                name="email"
                autoComplete="username"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
              />
            </label>
            <label>
              <span>Senha</span>
              <input
                type="password"
                name="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
              />
            </label>

            {error ? <div className="form-error" role="alert">{error}</div> : null}

            <button
              type="submit"
              className="button button--primary button--full"
              disabled={submitting || status === 'loading'}
            >
              {submitting ? 'Entrando…' : 'Entrar'}
            </button>
          </form>

          <div className="demo-access">
            <div>
              <strong>Acesso de demonstração</strong>
              <span>{DEMO_EMAIL}</span>
              <span>{DEMO_PASSWORD}</span>
            </div>
            <button type="button" className="button button--secondary" onClick={useDemoAccess}>
              Usar acesso demo
            </button>
          </div>
        </div>
      </section>
    </main>
  )
}
