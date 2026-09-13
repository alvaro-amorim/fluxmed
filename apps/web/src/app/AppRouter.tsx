import { Navigate, Route, Routes } from 'react-router-dom'

import { LoginPage } from '../features/auth/LoginPage'
import { ProtectedRoute } from '../features/auth/ProtectedRoute'
import { PlaceholderPage } from '../pages/PlaceholderPage'
import { AppShell } from './AppShell'

export function AppRouter() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<AppShell />}>
          <Route index element={<Navigate to="/operations" replace />} />
          <Route
            path="/operations"
            element={
              <PlaceholderPage
                title="Operações"
                description="Criação, planejamento e histórico das operações diárias do FluxMed."
                phase="Próxima fase"
              />
            }
          />
          <Route
            path="/deliveries"
            element={
              <PlaceholderPage
                title="Entregas"
                description="Cadastro, importação e acompanhamento das entregas médicas."
                phase="Planejado"
              />
            }
          />
          <Route
            path="/fleet"
            element={
              <PlaceholderPage
                title="Frota"
                description="Veículos, capacidades, autonomia, refrigeração e custos."
                phase="Planejado"
              />
            }
          />
          <Route
            path="/workforce"
            element={
              <PlaceholderPage
                title="Equipe"
                description="Motoristas, ajudantes, disponibilidade e custos de equipe."
                phase="Planejado"
              />
            }
          />
          <Route
            path="/reports"
            element={
              <PlaceholderPage
                title="Relatórios"
                description="Relatórios operacionais, custos e exportações da operação."
                phase="Planejado"
              />
            }
          />
          <Route
            path="/assistant"
            element={
              <PlaceholderPage
                title="Assistente IA"
                description="Explicações e análises em linguagem natural com dados validados."
                phase="Planejado"
              />
            }
          />
          <Route
            path="/settings"
            element={
              <PlaceholderPage
                title="Configurações"
                description="Parâmetros administrativos do ambiente FluxMed."
                phase="ADMIN"
              />
            }
          />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/operations" replace />} />
    </Routes>
  )
}
