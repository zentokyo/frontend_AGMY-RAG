import { useNavigate } from 'react-router-dom'
import { LogOut, User } from 'lucide-react'
import toast from 'react-hot-toast'
import useAuthStore from '../../store/authStore.js'
import { logout } from '../../api/auth.js'

export default function Header() {
  const navigate   = useNavigate()
  const user       = useAuthStore((s) => s.user)
  const clearAuth  = useAuthStore((s) => s.clearAuth)

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
    <header className="flex h-16 items-center justify-between border-b border-slate-200 bg-white px-6">
      <div /> {/* placeholder for breadcrumb if needed */}

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 text-sm text-slate-600">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-100">
            <User size={15} className="text-slate-500" />
          </div>
          <span>{user?.email}</span>
          <span className="rounded bg-blue-100 px-1.5 py-0.5 text-xs font-medium text-blue-700">
            {user?.role}
          </span>
        </div>

        <button
          onClick={handleLogout}
          className="btn-secondary gap-1.5 text-xs"
        >
          <LogOut size={14} />
          Выйти
        </button>
      </div>
    </header>
  )
}
