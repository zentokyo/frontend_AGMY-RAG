import { useState, useEffect } from 'react'
import useAuthStore from '../store/authStore.js'
import { User, Mail, Shield, Moon, Sun, Settings } from 'lucide-react'

export default function ProfilePage() {
  const user = useAuthStore((s) => s.user)
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

  const initials = user?.username
    ? user.username.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase()
    : (user?.email ? user.email.substring(0, 2).toUpperCase() : 'US')

  return (
    <div className="space-y-6 text-slate-800 dark:text-slate-200">
      {/* Page Header */}
      <div>
        <h1 className="text-xl font-bold text-slate-900 dark:text-white sm:text-2xl">Профиль</h1>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          Управление настройками вашей учетной записи и внешним видом приложения.
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        {/* Banner with avatar */}
        <div className="card bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 p-6 col-span-1 flex flex-col items-center text-center space-y-4">
          <div className="relative flex h-24 w-24 items-center justify-center rounded-full bg-gradient-to-tr from-blue-500 to-indigo-600 text-white font-bold text-3xl shadow-md">
            {initials}
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-900 dark:text-white">
              {user?.username || 'Студент'}
            </h2>
            <p className="text-xs text-slate-400 font-medium mt-0.5">Личный кабинет ASMU RAG</p>
          </div>
        </div>

        {/* Account Details */}
        <div className="card bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 p-6 col-span-1 md:col-span-2 space-y-6">
          <div className="space-y-4">
            <h3 className="font-bold text-slate-900 dark:text-white flex items-center gap-2 border-b border-slate-100 dark:border-slate-850 pb-3">
              <User size={18} className="text-blue-500" />
              Данные аккаунта
            </h3>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="flex items-center gap-3 bg-slate-50 dark:bg-slate-800/40 p-3 rounded-lg border border-slate-100 dark:border-slate-850">
                <Mail size={16} className="text-slate-400 shrink-0" />
                <div className="min-w-0">
                  <span className="text-xxs font-semibold text-slate-400 uppercase tracking-wider block">Email</span>
                  <span className="text-sm font-semibold text-slate-800 dark:text-slate-200 block truncate">
                    {user?.email || '—'}
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-3 bg-slate-50 dark:bg-slate-800/40 p-3 rounded-lg border border-slate-100 dark:border-slate-850">
                <Shield size={16} className="text-slate-400 shrink-0" />
                <div className="min-w-0">
                  <span className="text-xxs font-semibold text-slate-400 uppercase tracking-wider block">Имя / Никнейм</span>
                  <span className="text-sm font-semibold text-slate-800 dark:text-slate-200 block truncate">
                    {user?.username || '—'}
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-3 bg-slate-50 dark:bg-slate-800/40 p-3 rounded-lg border border-slate-100 dark:border-slate-850 sm:col-span-2">
                <div className="min-w-0">
                  <span className="text-xxs font-semibold text-slate-400 uppercase tracking-wider block">ID Пользователя</span>
                  <code className="text-xs font-mono text-slate-600 dark:text-slate-400 block break-all">
                    {user?.id || '—'}
                  </code>
                </div>
              </div>
            </div>
          </div>

          {/* Settings / Theme Toggler */}
          <div className="space-y-4">
            <h3 className="font-bold text-slate-900 dark:text-white flex items-center gap-2 border-b border-slate-100 dark:border-slate-850 pb-3">
              <Settings size={18} className="text-indigo-500" />
              Внешний вид
            </h3>

            <div className="flex items-center justify-between bg-slate-50 dark:bg-slate-800/40 p-4 rounded-xl border border-slate-100 dark:border-slate-850">
              <div className="space-y-0.5">
                <span className="text-sm font-semibold text-slate-800 dark:text-slate-200 block">Темная тема оформления</span>
                <span className="text-xs text-slate-400 block">Переключение темы личного кабинета и панели администратора</span>
              </div>
              <button
                onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-sm font-semibold text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800/80 transition-colors shadow-xs"
              >
                {theme === 'dark' ? (
                  <>
                    <Sun size={16} className="text-amber-500" />
                    <span>Светлая тема</span>
                  </>
                ) : (
                  <>
                    <Moon size={16} className="text-indigo-500" />
                    <span>Темная тема</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
