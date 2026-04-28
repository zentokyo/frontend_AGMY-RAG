import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getLastStats } from '../api/appStats.js'

export default function ExamResultsPage() {
  const { examId } = useParams()
  const stats = useQuery({
    queryKey: ['app-stats-last', examId],
    queryFn: getLastStats,
    retry: false,
  })

  return (
    <div>
      <h1 className="text-xl font-semibold text-slate-900 sm:text-2xl">Результаты</h1>
      <p className="mt-2 text-sm text-slate-600">
        Экзамен: <code className="rounded bg-slate-100 px-1.5 py-0.5 text-xs">{examId}</code>
      </p>
      <div className="card mt-4 p-4">
        {stats.isLoading && <p className="text-sm text-slate-500">Загрузка...</p>}
        {stats.isError && <p className="text-sm text-slate-500">Нет данных по завершённому экзамену.</p>}
        {stats.data && (
          <>
            <p className="text-sm text-slate-700">Тема: {stats.data.theme_title || '—'}</p>
            <p className="text-sm text-slate-700">Верных: {stats.data.correct_answers} из {stats.data.total_answers}</p>
            <p className="text-sm text-slate-700">Точность: {Math.round((stats.data.accuracy || 0) * 100)}%</p>
          </>
        )}
      </div>
    </div>
  )
}
