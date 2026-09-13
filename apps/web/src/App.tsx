import { useEffect, useState } from 'react'

type ApiStatus = 'checking' | 'online' | 'offline'

function apiUrl(path: string): string {
  const baseUrl = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '') ?? ''
  return `${baseUrl}${path}`
}

export default function App() {
  const [apiStatus, setApiStatus] = useState<ApiStatus>('checking')

  useEffect(() => {
    const controller = new AbortController()

    async function checkApi() {
      try {
        const response = await fetch(apiUrl('/health/live'), {
          signal: controller.signal,
        })
        setApiStatus(response.ok ? 'online' : 'offline')
      } catch (error) {
        if (error instanceof DOMException && error.name === 'AbortError') return
        setApiStatus('offline')
      }
    }

    void checkApi()
    return () => controller.abort()
  }, [])

  const statusLabel = {
    checking: 'Verificando API…',
    online: 'API online',
    offline: 'API indisponível',
  }[apiStatus]

  return (
    <main className="page-shell">
      <section className="foundation-card" aria-labelledby="fluxmed-title">
        <p className="eyebrow">Planejamento inteligente de rotas médicas</p>
        <h1 id="fluxmed-title">FluxMed</h1>
        <p className="intro">
          Fundação técnica ativa. O produto será construído em fatias verticais,
          mantendo frontend e backend integrados desde o início.
        </p>
        <div className={`api-status api-status--${apiStatus}`} role="status">
          <span className="status-dot" aria-hidden="true" />
          {statusLabel}
        </div>
      </section>
    </main>
  )
}
