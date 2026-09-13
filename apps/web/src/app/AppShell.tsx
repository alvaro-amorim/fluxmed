import { NavLink, Outlet } from 'react-router-dom'

import { useAuth } from '../features/auth/auth-context'
import type { UserRole } from '../types/auth'

interface NavigationItem {
  label: string
  path: string
  short: string
  allowedRoles?: UserRole[]
}

const navigation: NavigationItem[] = [
  { label: 'Operações', path: '/operations', short: 'OP' },
  { label: 'Entregas', path: '/deliveries', short: 'EN' },
  { label: 'Frota', path: '/fleet', short: 'FR' },
  { label: 'Equipe', path: '/workforce', short: 'EQ' },
  { label: 'Relatórios', path: '/reports', short: 'RE' },
  { label: 'Assistente IA', path: '/assistant', short: 'IA' },
  { label: 'Configurações', path: '/settings', short: 'CO', allowedRoles: ['ADMIN'] },
]

function roleLabel(role: UserRole): string {
  return role === 'ADMIN' ? 'Administrador' : 'Planejador'
}

export function AppShell() {
  const { user, logout } = useAuth()
  if (user === null) return null

  const visibleNavigation = navigation.filter(
    (item) => item.allowedRoles === undefined || item.allowedRoles.includes(user.role),
  )

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="brand-mark brand-mark--small">FM</div>
          <div>
            <strong>FluxMed</strong>
            <span>Controle logístico</span>
          </div>
        </div>

        <nav className="sidebar-nav" aria-label="Navegação principal">
          {visibleNavigation.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) => `nav-item${isActive ? ' nav-item--active' : ''}`}
            >
              <span className="nav-item-short" aria-hidden="true">{item.short}</span>
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-footer">
          <span className="sidebar-environment">Ambiente demo</span>
          <span>FluxMed V1 · desenvolvimento</span>
        </div>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <span className="topbar-context">Santa Aurora · planejamento diário</span>
          </div>
          <div className="user-area">
            <span className="session-status"><span aria-hidden="true" />Sessão ativa</span>
            <div className="user-copy">
              <strong>{user.display_name}</strong>
              <span>{roleLabel(user.role)}</span>
            </div>
            <button className="button button--ghost" type="button" onClick={() => void logout()}>
              Sair
            </button>
          </div>
        </header>

        <div className="workspace-content">
          <Outlet />
        </div>
      </section>
    </div>
  )
}
