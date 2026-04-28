import { useQuery } from '@tanstack/react-query'
import { getAllStats, getLastStats } from '../api/appStats.js'

export default function StatsPage() {
  const allStats = useQuery({
    queryKey: ['stats-all'],
    queryFn: getAllStats,
  })
  const lastStats = useQuery({
    queryKey: ['stats-last'],
    queryFn: getLastStats,
    retry: false,
  })

  return (
    <div>
      <h1 className="text-xl font-semibold text-slate-900 sm:text-2xl">Статистика</h1>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <div className="card p-4">
          <h2 className="font-medium text-slate-900">Общая</h2>
          {allStats.isLoading && <p className="text-sm text-slate-500 mt-2">Загрузка...</p>}
          {allStats.data && (
            <div className="mt-2 text-sm text-slate-700 space-y-1">
              <p>Всего ответов: {allStats.data.total_answers}</p>
              <p>Верных ответов: {allStats.data.correct_answers}</p>
              <p>Точность: {Math.round((allStats.data.accuracy || 0) * 100)}%</p>
            </div>
          )}
        </div>
        <div className="card p-4">
          <h2 className="font-medium text-slate-900">Последний экзамен</h2>
          {lastStats.isLoading && <p className="text-sm text-slate-500 mt-2">Загрузка...</p>}
          {lastStats.isError && <p className="text-sm text-slate-500 mt-2">Пока нет завершённых экзаменов.</p>}
          {lastStats.data && (
            <div className="mt-2 text-sm text-slate-700 space-y-1">
              <p>Тема: {lastStats.data.theme_title || '—'}</p>
              <p>Верных: {lastStats.data.correct_answers} / {lastStats.data.total_answers}</p>
              <p>Точность: {Math.round((lastStats.data.accuracy || 0) * 100)}%</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
