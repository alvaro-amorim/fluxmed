import { Navigate, Route, Routes } from 'react-router-dom'

import { LoginPage } from '../features/auth/LoginPage'
import { ProtectedRoute } from '../features/auth/ProtectedRoute'
import { DeliveriesPage } from '../features/deliveries/DeliveriesPage'
import '../features/deliveries/deliveries.css'
import { FleetPage } from '../features/fleet/FleetPage'
import { NewOperationPage } from '../features/operations/NewOperationPage'
import { OperationDetailPage } from '../features/operations/OperationDetailPage'
import { OperationsPage } from '../features/operations/OperationsPage'
import '../features/operations/operation-sections.css'
import '../features/operations/operation-wizard.css'
import '../features/operations/operations.css'
import '../features/resources/resources.css'
import { WorkforcePage } from '../features/workforce/WorkforcePage'
import { PlaceholderPage } from '../pages/PlaceholderPage'
import { AppShell } from './AppShell'

export function AppRouter() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<AppShell />}>
          <Route index element={<Navigate to="/operations" replace />} />
          <Route path="/operations" element={<OperationsPage />} />
          <Route path="/operations/new" element={<NewOperationPage />} />
          <Route path="/operations/:operationId" element={<OperationDetailPage />} />
          <Route path="/deliveries" element={<DeliveriesPage />} />
          <Route path="/fleet" element={<FleetPage />} />
          <Route path="/workforce" element={<WorkforcePage />} />
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
