import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import App from './App'
import type { AuthUser } from './types/auth'

const planner: AuthUser = {
  id: 'planner-id',
  email: 'planner@fluxmed.demo',
  display_name: 'Planejador Demo',
  role: 'PLANNER',
}

const admin: AuthUser = {
  ...planner,
  id: 'admin-id',
  email: 'admin@fluxmed.demo',
  display_name: 'Admin Demo',
  role: 'ADMIN',
}

function response(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response
}

function mockFetch(handler: (path: string, method: string) => Response): void {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = typeof input === 'string' ? input : input.toString()
      return handler(path, init?.method ?? 'GET')
    }),
  )
}

beforeEach(() => {
  window.history.pushState({}, '', '/login')
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('authentication shell', () => {
  it('logs in with the demo account and opens operations', async () => {
    mockFetch((path, method) => {
      if (path.endsWith('/auth/me')) return response({ error: {} }, 401)
      if (path.endsWith('/auth/login') && method === 'POST') return response({ user: planner })
      return response({}, 404)
    })

    render(<App />)
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: 'Usar acesso demo' }))
    await user.click(screen.getByRole('button', { name: 'Entrar' }))

    expect(await screen.findByRole('heading', { name: 'Operações' })).toBeInTheDocument()
    expect(screen.getByText('Planejador Demo')).toBeInTheDocument()
  })

  it('redirects an anonymous user away from a protected route', async () => {
    window.history.pushState({}, '', '/operations')
    mockFetch((path) =>
      path.endsWith('/auth/me') ? response({ error: {} }, 401) : response({}, 404),
    )

    render(<App />)

    expect(await screen.findByRole('heading', { name: 'Acesse o FluxMed' })).toBeInTheDocument()
  })

  it('only shows Configurações to an administrator', async () => {
    window.history.pushState({}, '', '/operations')
    mockFetch((path) => (path.endsWith('/auth/me') ? response(admin) : response({}, 404)))

    render(<App />)

    expect(await screen.findByRole('link', { name: /Configurações/ })).toBeInTheDocument()
  })

  it('hides Configurações from a planner', async () => {
    window.history.pushState({}, '', '/operations')
    mockFetch((path) => (path.endsWith('/auth/me') ? response(planner) : response({}, 404)))

    render(<App />)

    await screen.findByRole('heading', { name: 'Operações' })
    expect(screen.queryByRole('link', { name: /Configurações/ })).not.toBeInTheDocument()
  })

  it('logs out and returns to login', async () => {
    window.history.pushState({}, '', '/operations')
    mockFetch((path, method) => {
      if (path.endsWith('/auth/me')) return response(planner)
      if (path.endsWith('/auth/logout') && method === 'POST') return response(undefined, 204)
      return response({}, 404)
    })

    render(<App />)
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: 'Sair' }))

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Acesse o FluxMed' })).toBeInTheDocument()
    })
  })
})
