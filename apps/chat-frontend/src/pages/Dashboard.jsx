import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { getAllStats } from '../api/appStats.js'

export default function Dashboard() {
  const stats = useQuery({
    queryKey: ['app-stats-all'],
    queryFn: getAllStats,
  })

  const total = stats.data?.total_answers ?? 0
  const correct = stats.data?.correct_answers ?? 0
  const accuracy = Math.round((stats.data?.accuracy ?? 0) * 100)

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold text-slate-900 sm:text-2xl">Главная</h1>
      <p className="max-w-2xl text-sm text-slate-600 sm:text-base">
        Здесь появятся виджеты: быстрый старт экзамена, краткая статистика, продолжение сессии (после
        реализации API).
      </p>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <div className="card p-4 sm:p-5">
          <p className="text-sm font-medium text-slate-800">Всего ответов</p>
          <p className="mt-1 text-2xl font-semibold text-slate-900">{total}</p>
        </div>
        <div className="card p-4 sm:p-5">
          <p className="text-sm font-medium text-slate-800">Верных ответов</p>
          <p className="mt-1 text-2xl font-semibold text-slate-900">{correct}</p>
        </div>
        <div className="card p-4 sm:p-5 sm:col-span-2 lg:col-span-1">
          <p className="text-sm font-medium text-slate-800">Точность</p>
          <p className="mt-1 text-2xl font-semibold text-slate-900">{accuracy}%</p>
        </div>
      </div>
      <div className="flex gap-2">
        <Link to="/app/exams" className="btn-primary">Перейти к экзаменам</Link>
        <Link to="/app/theory" className="btn-secondary">Открыть теорию</Link>
      </div>
    </div>
  )
}
