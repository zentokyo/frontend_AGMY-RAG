import { useQuery } from '@tanstack/react-query'
import { FileText, HelpCircle, FolderOpen, BookOpen } from 'lucide-react'
import { getDocumentStats, getDocuments } from '../api/documents.js'
import { getQuestionStats } from '../api/questions.js'
import { formatDate } from '../utils/format.js'

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

  const recentDocs = [...documents].slice(0, 5)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Дашборд</h1>
        <p className="mt-1 text-sm text-slate-500">Обзор состояния системы RAG</p>
      </div>

      {/* Stats grid */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          icon={FolderOpen}
          label="Тем в базе знаний"
          value={docLoading ? '…' : docStats?.total_themes}
          sub={docStats?.total_blocks ? `${docStats.total_blocks} ${pluralBlocks(docStats.total_blocks)}` : undefined}
          color="blue"
        />
        <StatCard
          icon={FileText}
          label="Файлов всего"
          value={docLoading ? '…' : docStats?.total_files}
          color="green"
        />
        <StatCard
          icon={HelpCircle}
          label="Вопросов Q&A"
          value={qLoading ? '…' : qStats?.total}
          color="blue"
        />
        <StatCard
          icon={BookOpen}
          label="Категорий вопросов"
          value={qLoading ? '…' : qStats?.by_theme?.length ?? 0}
          color="amber"
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
                  <FolderOpen size={16} className="shrink-0 text-blue-400" />
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-slate-700">{doc.title}</p>
                    <p className="text-xs text-slate-400">{doc.file_count} файлов</p>
                  </div>
                </div>
                <span className="badge bg-blue-50 text-blue-700">{doc.block_title || `Тема #${doc.theme_order}`}</span>
              </li>
            ))
          )}
        </ul>
      </div>

      {/* Q&A by category */}
      {qStats?.by_theme?.length > 0 && (
        <div className="card">
          <div className="border-b border-slate-200 px-6 py-4">
            <h2 className="text-sm font-semibold text-slate-700">Q&A по темам</h2>
          </div>
          <ul className="divide-y divide-slate-100">
            {qStats.by_theme.map((t) => (
              <li key={t.theme} className="flex items-center justify-between px-6 py-3">
                <span className="text-sm text-slate-700">{t.theme}</span>
                <span className="badge bg-blue-50 text-blue-700">{t.count}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

function pluralBlocks(n) {
  if (n % 10 === 1 && n % 100 !== 11) return 'блок'
  if ([2, 3, 4].includes(n % 10) && ![12, 13, 14].includes(n % 100)) return 'блока'
  return 'блоков'
}
