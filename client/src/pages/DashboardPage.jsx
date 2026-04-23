import { useQuery } from '@tanstack/react-query'
import { FileText, HelpCircle, CheckCircle, AlertCircle } from 'lucide-react'
import { getDocumentStats } from '../api/documents.js'
import { getQuestionStats } from '../api/questions.js'
import { getDocuments } from '../api/documents.js'
import { formatBytes, formatDate } from '../utils/format.js'

function StatCard({ icon: Icon, label, value, sub, color }) {
  const colors = {
    blue:  { bg: 'bg-blue-50',   icon: 'text-blue-600',  ring: 'ring-blue-200' },
    green: { bg: 'bg-green-50',  icon: 'text-green-600', ring: 'ring-green-200' },
    amber: { bg: 'bg-amber-50',  icon: 'text-amber-600', ring: 'ring-amber-200' },
    red:   { bg: 'bg-red-50',    icon: 'text-red-600',   ring: 'ring-red-200'   },
  }
  const c = colors[color] || colors.blue

  return (
    <div className="card p-6">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-slate-500">{label}</p>
          <p className="mt-1 text-3xl font-bold text-slate-900">{value ?? '—'}</p>
          {sub && <p className="mt-1 text-xs text-slate-400">{sub}</p>}
        </div>
        <div className={`rounded-xl p-3 ring-1 ${c.bg} ${c.ring}`}>
          <Icon size={20} className={c.icon} />
        </div>
      </div>
    </div>
  )
}

function StatusBadge({ status }) {
  const styles = {
    processing: 'bg-amber-100 text-amber-700',
    indexed:    'bg-green-100 text-green-700',
    error:      'bg-red-100 text-red-600',
  }
  const labels = { processing: 'Обработка', indexed: 'Проиндексирован', error: 'Ошибка' }
  return (
    <span className={`badge ${styles[status] || 'bg-slate-100 text-slate-600'}`}>
      {labels[status] || status}
    </span>
  )
}

export default function DashboardPage() {
  const { data: docStats, isLoading: docLoading } = useQuery({
    queryKey: ['document-stats'],
    queryFn: getDocumentStats,
  })

  const { data: qStats, isLoading: qLoading } = useQuery({
    queryKey: ['question-stats'],
    queryFn: getQuestionStats,
  })

  const { data: documents = [] } = useQuery({
    queryKey: ['documents'],
    queryFn: getDocuments,
  })

  const recentDocs = [...documents]
    .sort((a, b) => new Date(b.uploaded_at) - new Date(a.uploaded_at))
    .slice(0, 5)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Дашборд</h1>
        <p className="mt-1 text-sm text-slate-500">Обзор состояния системы RAG</p>
      </div>

      {/* Stats grid */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          icon={FileText}
          label="Документов"
          value={docLoading ? '…' : docStats?.total}
          sub={docStats ? `${formatBytes(Number(docStats.total_size))} всего` : undefined}
          color="blue"
        />
        <StatCard
          icon={CheckCircle}
          label="Проиндексировано"
          value={docLoading ? '…' : docStats?.indexed}
          color="green"
        />
        <StatCard
          icon={HelpCircle}
          label="Вопросов Q&A"
          value={qLoading ? '…' : qStats?.total}
          sub={qStats ? `${qStats.active} активных` : undefined}
          color="blue"
        />
        <StatCard
          icon={AlertCircle}
          label="Ошибок загрузки"
          value={docLoading ? '…' : docStats?.error}
          color="red"
        />
      </div>

      {/* Recent uploads */}
      <div className="card">
        <div className="border-b border-slate-200 px-6 py-4">
          <h2 className="text-sm font-semibold text-slate-700">Последние загрузки</h2>
        </div>
        <ul className="divide-y divide-slate-100">
          {recentDocs.length === 0 ? (
            <li className="py-8 text-center text-sm text-slate-400">
              Документы ещё не загружены
            </li>
          ) : (
            recentDocs.map((doc) => (
              <li key={doc.id} className="flex items-center justify-between px-6 py-3">
                <div className="flex items-center gap-3 min-w-0">
                  <FileText size={16} className="shrink-0 text-slate-400" />
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-slate-700">
                      {doc.original_name}
                    </p>
                    <p className="text-xs text-slate-400">
                      {formatBytes(doc.file_size)} · {formatDate(doc.uploaded_at)}
                    </p>
                  </div>
                </div>
                <StatusBadge status={doc.status} />
              </li>
            ))
          )}
        </ul>
      </div>

      {/* Q&A by category */}
      {qStats?.by_category?.length > 0 && (
        <div className="card">
          <div className="border-b border-slate-200 px-6 py-4">
            <h2 className="text-sm font-semibold text-slate-700">Q&A по категориям</h2>
          </div>
          <ul className="divide-y divide-slate-100">
            {qStats.by_category.map((cat) => (
              <li key={cat.category} className="flex items-center justify-between px-6 py-3">
                <span className="text-sm text-slate-700">{cat.category}</span>
                <span className="badge bg-blue-50 text-blue-700">{cat.count}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
