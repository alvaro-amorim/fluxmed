import { type ReactNode, useEffect, useMemo, useState } from 'react'

import * as authService from '../../services/auth'
import { ApiClientError } from '../../services/api'
import type { AuthUser } from '../../types/auth'
import { AuthContext, type AuthContextValue, type AuthStatus } from './auth-context'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [status, setStatus] = useState<AuthStatus>('loading')

  useEffect(() => {
    let active = true

    async function restoreSession() {
      try {
        const currentUser = await authService.getCurrentUser()
        if (!active) return
        setUser(currentUser)
        setStatus('authenticated')
      } catch (error) {
        if (!active) return
        if (!(error instanceof ApiClientError) || error.status !== 401) {
          console.warn('Unable to restore FluxMed session', error)
        }
        setUser(null)
        setStatus('anonymous')
      }
    }

    void restoreSession()
    return () => {
      active = false
    }
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      status,
      async login(email: string, password: string) {
        const result = await authService.login(email, password)
        setUser(result.user)
        setStatus('authenticated')
      },
      async logout() {
        try {
          await authService.logout()
        } finally {
          setUser(null)
          setStatus('anonymous')
        }
      },
    }),
    [status, user],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
