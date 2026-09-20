import { BrowserRouter } from 'react-router-dom'

import { AppRouter } from './app/AppRouter'
import { AuthProvider } from './features/auth/AuthContext'

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRouter />
      </AuthProvider>
    </BrowserRouter>
  )
}
