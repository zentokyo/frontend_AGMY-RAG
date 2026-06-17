import { Link, useNavigate } from 'react-router-dom'
import { LogOut, User, Menu } from 'lucide-react'
import useAuthStore from '../../store/authStore.js'

export default function Header({ onMenuClick }) {
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)

  async function handleLogout() {
    await logout()
    navigate('/login', { replace: true })
  }

  const display = user?.username || user?.email || 'Пользователь'

  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b border-slate-200 bg-white px-4 sm:px-6">
      <div className="flex items-center gap-3 min-w-0">
        <button
          type="button"
          onClick={onMenuClick}
          className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-700 md:hidden focus:outline-none shrink-0"
          title="Открыть меню"
        >
          <Menu size={20} />
        </button>
        <div className="min-w-0 text-sm text-slate-500 sm:text-base truncate">
          Добро пожаловать в личный кабинет
        </div>
      </div>

      <div className="flex items-center gap-2 sm:gap-4">
        <div className="flex min-w-0 items-center gap-2 text-sm text-slate-600">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-100">
            <User size={15} className="text-slate-500" />
          </div>
          <span className="max-w-[140px] truncate sm:max-w-[220px]" title={display}>
            {display}
          </span>
        </div>

        <Link
          to="/login"
          className="text-xs text-blue-600 hover:text-blue-800 sm:hidden"
        >
          Вход
        </Link>

        <button
          type="button"
          onClick={handleLogout}
          className="btn-secondary gap-1.5 text-xs"
        >
          <LogOut size={14} />
          <span className="hidden sm:inline">Выйти</span>
        </button>
      </div>
    </header>
  )
}
