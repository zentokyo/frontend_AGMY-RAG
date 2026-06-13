import { NavLink } from 'react-router-dom'
import { LayoutDashboard, BookOpen, HelpCircle } from 'lucide-react'
import clsx from 'clsx'

const navItems = [
  { to: '/dashboard',       label: 'Дашборд',       icon: LayoutDashboard },
  { to: '/knowledge-base',  label: 'База знаний',   icon: BookOpen        },
  { to: '/questions',       label: 'База вопросов', icon: HelpCircle      },
]

export default function Sidebar() {
  return (
    <aside className="flex w-60 flex-col bg-slate-900 text-slate-100">
      {/* Brand */}
      <div className="flex h-16 items-center gap-3 border-b border-slate-700/50 px-5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600">
          <span className="text-sm font-bold text-white">A</span>
        </div>
        <div>
          <p className="text-sm font-semibold leading-none">ASMU RAG</p>
          <p className="text-xs text-slate-400 mt-0.5">Admin Panel</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 px-3 py-4">
        {navItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-400 hover:bg-slate-800 hover:text-slate-100'
              )
            }
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="border-t border-slate-700/50 px-5 py-3">
        <p className="text-xs text-slate-500">RAG Assistant v1.0</p>
      </div>
    </aside>
  )
}
