import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { LogOut, User, Sun, Moon } from 'lucide-react'
import toast from 'react-hot-toast'
import useAuthStore from '../../store/authStore.js'
import { logout } from '../../api/auth.js'

export default function Header() {
  const navigate   = useNavigate()
  const user       = useAuthStore((s) => s.user)
  const clearAuth  = useAuthStore((s) => s.clearAuth)

  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('theme') || 'light'
  })

  useEffect(() => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
    localStorage.setItem('theme', theme)
  }, [theme])

  async function handleLogout() {
    try {
      await logout()
    } catch {
      // Ignore — clear client state regardless
    }
    clearAuth()
    navigate('/login', { replace: true })
    toast.success('Вы вышли из системы')
  }

  return (
    <header className="flex h-16 items-center justify-between border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 px-6 transition-colors">
      <div /> {/* placeholder for breadcrumb if needed */}

      <div className="flex items-center gap-4">
        <button
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800 transition-colors"
          title={theme === 'dark' ? 'Светлая тема' : 'Темная тема'}
        >
          {theme === 'dark' ? <Sun size={18} className="text-amber-500" /> : <Moon size={18} />}
        </button>

        <div className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-100 dark:bg-slate-800">
            <User size={15} className="text-slate-500 dark:text-slate-400" />
          </div>
          <span>{user?.email}</span>
          <span className="rounded bg-blue-100 dark:bg-blue-950/40 px-1.5 py-0.5 text-xs font-medium text-blue-700 dark:text-blue-400">
            {user?.role}
          </span>
        </div>

        <button
          onClick={handleLogout}
          className="btn-secondary gap-1.5 text-xs dark:bg-slate-800 dark:text-slate-200 dark:border-slate-700 dark:hover:bg-slate-750"
        >
          <LogOut size={14} />
          Выйти
        </button>
      </div>
    </header>
  )
}
