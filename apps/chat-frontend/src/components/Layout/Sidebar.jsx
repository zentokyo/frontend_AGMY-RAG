import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  GraduationCap,
  BarChart3,
  User,
  X,
} from 'lucide-react'
import clsx from 'clsx'
import useAuthStore from '../../store/authStore.js'

const navItems = [
  { to: '/app', end: true, label: 'Главная', icon: LayoutDashboard },
  { to: '/app/course', label: 'Курс', icon: GraduationCap },
  { to: '/app/stats', label: 'Статистика', icon: BarChart3 },
  { to: '/app/profile', label: 'Профиль', icon: User },
]

export default function Sidebar({ isOpen, onClose }) {
  const logout = useAuthStore((s) => s.logout)

  const renderContent = (isMobile = false) => (
    <div className="flex h-full flex-col bg-slate-900 text-slate-100">
      <div className="flex h-16 items-center justify-between border-b border-slate-700/50 px-5">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600">
            <span className="text-sm font-bold text-white">A</span>
          </div>
          <div>
            <p className="text-sm font-semibold leading-none">ASMU RAG</p>
            <p className="mt-0.5 text-xs text-slate-400">Портал обучения</p>
          </div>
        </div>
        {isMobile && (
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white md:hidden focus:outline-none"
            title="Закрыть меню"
          >
            <X size={18} />
          </button>
        )}
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
        {navItems.map(({ to, end, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            onClick={isMobile ? onClose : undefined}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-400 hover:bg-slate-800 hover:text-slate-100'
              )
            }
          >
            <Icon size={18} className="shrink-0" />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-slate-700/50 px-3 py-3">
        <button
          onClick={() => {
            if (isMobile) onClose()
            logout()
          }}
          className="w-full rounded-lg px-3 py-2 text-left text-sm font-medium text-slate-400 hover:bg-slate-800 hover:text-slate-100 transition-colors"
        >
          Выйти
        </button>
      </div>
    </div>
  )

  return (
    <>
      {/* Desktop static sidebar */}
      <aside className="hidden md:flex md:w-60 md:shrink-0 md:flex-col bg-slate-900 text-slate-100 border-r border-slate-800">
        {renderContent(false)}
      </aside>

      {/* Mobile animated drawer sidebar */}
      <div
        className={clsx(
          'fixed inset-0 z-50 md:hidden transition-opacity duration-300',
          isOpen ? 'pointer-events-auto opacity-100' : 'pointer-events-none opacity-0'
        )}
      >
        {/* Backdrop overlay */}
        <div
          className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm"
          onClick={onClose}
        />
        {/* Sliding drawer panel */}
        <aside
          className={clsx(
            'absolute inset-y-0 left-0 flex w-56 sm:w-60 transform flex-col bg-slate-900 shadow-xl transition-transform duration-300 ease-in-out',
            isOpen ? 'translate-x-0' : '-translate-x-full'
          )}
        >
          {renderContent(true)}
        </aside>
      </div>
    </>
  )
}
