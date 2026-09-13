import { Navigate, Outlet, useLocation } from 'react-router-dom'

import { useAuth } from './auth-context'

export function ProtectedRoute() {
  const { status } = useAuth()
  const location = useLocation()

  if (status === 'loading') {
    return (
      <main className="auth-loading" role="status">
        <div className="brand-mark brand-mark--standalone">FM</div>
        <p>Verificando sessão segura…</p>
      </main>
    )
  }

  if (status === 'anonymous') {
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  return <Outlet />
}
