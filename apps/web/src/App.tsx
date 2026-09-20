import { BrowserRouter } from 'react-router-dom'

import { AppRouter } from './app/AppRouter'
import { AuthProvider } from './features/auth/AuthContext'

export default function App() {
  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <AuthProvider>
        <AppRouter />
      </AuthProvider>
    </BrowserRouter>
  )
}
