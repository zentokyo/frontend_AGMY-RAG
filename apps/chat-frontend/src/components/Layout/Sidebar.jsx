import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  ClipboardList,
  BookOpen,
  BarChart3,
  User,
} from 'lucide-react'
import clsx from 'clsx'

const navItems = [
  { to: '/app', end: true, label: 'Главная', icon: LayoutDashboard },
  { to: '/app/exams', label: 'Экзамены', icon: ClipboardList },
  { to: '/app/theory', label: 'Теория', icon: BookOpen },
  { to: '/app/stats', label: 'Статистика', icon: BarChart3 },
  { to: '/app/profile', label: 'Профиль', icon: User },
]

export default function Sidebar() {
  return (
    <aside className="flex w-56 shrink-0 flex-col bg-slate-900 text-slate-100 sm:w-60">
      <div className="flex h-16 items-center gap-3 border-b border-slate-700/50 px-5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600">
          <span className="text-sm font-bold text-white">A</span>
        </div>
        <div>
          <p className="text-sm font-semibold leading-none">AGMY RAG</p>
          <p className="mt-0.5 text-xs text-slate-400">Личный кабинет</p>
        </div>
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
        {navItems.map(({ to, end, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
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

      <div className="border-t border-slate-700/50 px-5 py-3">
        <p className="text-xs text-slate-500">Портал обучения v1.0</p>
      </div>
    </aside>
  )
}
