import { Routes, Route, Navigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import useAuthStore from './store/authStore.js'
import { refreshToken, getMe } from './api/auth.js'

import LoginPage        from './pages/LoginPage.jsx'
import DashboardPage    from './pages/DashboardPage.jsx'
import KnowledgeBasePage from './pages/KnowledgeBasePage.jsx'
import QuestionsPage    from './pages/QuestionsPage.jsx'
import Layout           from './components/Layout/Layout.jsx'

function RequireAuth({ children }) {
  const accessToken = useAuthStore((s) => s.accessToken)
  if (!accessToken) return <Navigate to="/login" replace />
  return children
}

export default function App() {
  const [bootstrapping, setBootstrapping] = useState(true)
  const setAuth = useAuthStore((s) => s.setAuth)

  // On first load, try to restore session via httpOnly cookie
  useEffect(() => {
    refreshToken()
      .then(({ accessToken }) =>
        getMe().then((user) => setAuth(accessToken, user))
      )
      .catch(() => {}) // no session — user stays logged out
      .finally(() => setBootstrapping(false))
  }, [setAuth])

  if (bootstrapping) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
      </div>
    )
  }

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route
        path="/"
        element={
          <RequireAuth>
            <Layout />
          </RequireAuth>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard"      element={<DashboardPage />} />
        <Route path="knowledge-base" element={<KnowledgeBasePage />} />
        <Route path="questions"      element={<QuestionsPage />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
