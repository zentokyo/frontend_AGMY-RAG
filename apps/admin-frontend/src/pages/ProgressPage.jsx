import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Activity,
  AlertTriangle,
  BarChart3,
  BookOpen,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Clock3,
  Eye,
  ListChecks,
  Search,
  Trophy,
  Users,
} from 'lucide-react'
import clsx from 'clsx'
import {
  getProgressBlocks,
  getProgressExams,
  getProgressOverview,
  getProgressUserDetail,
  getProgressUsers,
} from '../api/progress.js'
import DataTable from '../components/Table/DataTable.jsx'
import { formatDate, formatPercent } from '../utils/format.js'

const LIMIT = 20

export default function ProgressPage() {
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [selectedUserId, setSelectedUserId] = useState(null)

  const overviewQuery = useQuery({
    queryKey: ['progress-overview'],
    queryFn: getProgressOverview,
  })

  const blocksQuery = useQuery({
    queryKey: ['progress-blocks'],
    queryFn: getProgressBlocks,
  })

  const usersQuery = useQuery({
    queryKey: ['progress-users', { page, search }],
    queryFn: () => getProgressUsers({ page, limit: LIMIT, search }),
    placeholderData: (prev) => prev,
  })

  const detailQuery = useQuery({
    queryKey: ['progress-user-detail', selectedUserId],
    queryFn: () => getProgressUserDetail(selectedUserId),
    enabled: Boolean(selectedUserId),
  })

  const examsQuery = useQuery({
    queryKey: ['progress-exams', selectedUserId],
    queryFn: () => getProgressExams({ user_id: selectedUserId, limit: 20 }),
    placeholderData: (prev) => prev,
  })

  const users = usersQuery.data?.items ?? []
  const pagination = usersQuery.data ?? { total: 0, page: 1, limit: LIMIT }
  const selectedUser = detailQuery.data
  const exams = examsQuery.data ?? []

  useEffect(() => {
    if (!selectedUserId && users.length > 0) {
      setSelectedUserId(users[0].id)
    }
  }, [selectedUserId, users])

  function handleSearchSubmit(event) {
    event.preventDefault()
    setPage(1)
  }

  const summary = overviewQuery.data?.summary ?? {}

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Прохождение курса</h1>
          <p className="mt-1 text-sm text-slate-500">
            Статистика студентов, экзаменов, прогресса по блокам и качества ответов.
          </p>
        </div>
        <form onSubmit={handleSearchSubmit} className="flex w-full gap-2 sm:max-w-md">
          <div className="relative flex-1">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              className="input pl-9"
              placeholder="Поиск по студенту или email…"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </div>
          <button type="submit" className="btn-secondary">
            Найти
          </button>
        </form>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          icon={Users}
          label="Студентов"
          value={overviewQuery.isLoading ? '…' : summary.total_users}
          sub={`${summary.users_with_exams ?? 0} с попытками`}
          color="blue"
        />
        <MetricCard
          icon={Trophy}
          label="Завершили курс"
          value={overviewQuery.isLoading ? '…' : summary.course_passed_users}
          sub={formatPercent(safeRatio(summary.course_passed_users, summary.total_users))}
          color="green"
        />
        <MetricCard
          icon={ListChecks}
          label="Экзаменов"
          value={overviewQuery.isLoading ? '…' : summary.total_exams}
          sub={`${summary.completed_exams ?? 0} завершено · ${summary.in_progress_exams ?? 0} в работе`}
          color="amber"
        />
        <MetricCard
          icon={BarChart3}
          label="Точность ответов"
          value={overviewQuery.isLoading ? '…' : formatPercent(summary.accuracy)}
          sub={`${summary.correct_answers ?? 0}/${summary.total_answers ?? 0} верных`}
          color="blue"
        />
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.25fr)_minmax(360px,0.75fr)]">
        <section className="card">
          <SectionHeader
            title="Прогресс по блокам"
            subtitle={`${summary.total_blocks ?? 0} блоков · ${summary.total_topics ?? 0} тем`}
          />
          <div className="divide-y divide-slate-100">
            {blocksQuery.isLoading ? (
              <LoadingRow />
            ) : (blocksQuery.data ?? []).length === 0 ? (
              <EmptyRow text="Блоки ещё не созданы" />
            ) : (
              blocksQuery.data.map((block) => (
                <BlockProgress key={block.id} block={block} totalUsers={summary.total_users ?? 0} />
              ))
            )}
          </div>
        </section>

        <section className="card">
          <SectionHeader title="Активность за 14 дней" subtitle="По дате старта или завершения экзамена" />
          <div className="space-y-3 p-5">
            {(overviewQuery.data?.activity ?? []).length === 0 ? (
              <p className="py-8 text-center text-sm text-slate-400">За последние 14 дней активности нет</p>
            ) : (
              overviewQuery.data.activity.map((item) => (
                <ActivityRow key={item.day} item={item} max={maxActivity(overviewQuery.data.activity)} />
              ))
            )}
          </div>
          <div className="border-t border-slate-100 p-5">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Типы экзаменов</h3>
            <div className="mt-3 space-y-2">
              {(overviewQuery.data?.by_scope ?? []).map((item) => (
                <div key={item.exam_scope} className="flex items-center justify-between gap-3 text-sm">
                  <span className="text-slate-600">{scopeLabel(item.exam_scope)}</span>
                  <span className="font-medium text-slate-900">
                    {item.total_exams} · {formatPercent(item.average_score)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </section>
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.05fr)_minmax(420px,0.95fr)]">
        <section className="card overflow-hidden">
          <SectionHeader
            title="Студенты"
            subtitle={`${pagination.total ?? 0} зарегистрировано`}
          />
          <DataTable
            loading={usersQuery.isLoading}
            data={users}
            emptyMessage="Студенты не найдены"
            columns={[
              {
                key: 'email',
                header: 'Студент',
                render: (_, row) => (
                  <div className="min-w-0">
                    <p className="truncate font-medium text-slate-800">{row.username || 'Без имени'}</p>
                    <p className="truncate text-xs text-slate-400">{row.email}</p>
                  </div>
                ),
              },
              {
                key: 'topic_progress',
                header: 'Темы',
                render: (value, row) => (
                  <ProgressCell
                    value={value}
                    label={`${row.passed_topics}/${row.total_topics}`}
                  />
                ),
              },
              {
                key: 'accuracy',
                header: 'Точность',
                render: (value, row) => (
                  <div>
                    <p className="font-medium text-slate-800">{formatPercent(value)}</p>
                    <p className="text-xs text-slate-400">{row.correct_answers}/{row.total_answers}</p>
                  </div>
                ),
              },
              {
                key: 'total_exams',
                header: 'Экзамены',
                render: (value, row) => (
                  <div>
                    <p className="font-medium text-slate-800">{value}</p>
                    <p className="text-xs text-slate-400">{row.completed_exams} завершено</p>
                  </div>
                ),
              },
              {
                key: 'course_status',
                header: 'Курс',
                render: (value) => <StatusBadge status={value} />,
              },
              {
                key: 'last_activity_at',
                header: 'Активность',
                render: (value) => <span className="whitespace-nowrap text-xs">{formatDate(value)}</span>,
              },
              {
                key: 'actions',
                header: '',
                cellClassName: 'text-right',
                render: (_, row) => (
                  <button
                    className={clsx(
                      'btn-secondary px-3 py-1.5 text-xs',
                      selectedUserId === row.id && 'border-blue-300 bg-blue-50 text-blue-700'
                    )}
                    onClick={() => setSelectedUserId(row.id)}
                  >
                    <Eye size={13} />
                    Открыть
                  </button>
                ),
              },
            ]}
          />
          <Pagination
            page={page}
            total={pagination.total ?? 0}
            limit={LIMIT}
            onPrev={() => setPage((value) => Math.max(value - 1, 1))}
            onNext={() => setPage((value) => value + 1)}
          />
        </section>

        <section className="card overflow-hidden">
          <SectionHeader
            title="Карточка студента"
            subtitle={selectedUser?.user?.email || 'Выберите студента в таблице'}
          />
          {!selectedUserId ? (
            <EmptyRow text="Нет выбранного студента" />
          ) : detailQuery.isLoading ? (
            <LoadingRow />
          ) : selectedUser ? (
            <UserDetail data={selectedUser} />
          ) : (
            <EmptyRow text="Не удалось загрузить карточку студента" />
          )}
        </section>
      </div>

      <section className="card overflow-hidden">
        <SectionHeader
          title={selectedUserId ? 'Последние экзамены выбранного студента' : 'Последние экзамены'}
          subtitle="Ответы, статус проверки и контекст экзамена"
        />
        <DataTable
          loading={examsQuery.isLoading}
          data={exams}
          emptyMessage="Экзаменов пока нет"
          columns={[
            {
              key: 'email',
              header: 'Студент',
              render: (_, row) => (
                <div className="min-w-0">
                  <p className="truncate font-medium text-slate-800">{row.username || 'Без имени'}</p>
                  <p className="truncate text-xs text-slate-400">{row.email}</p>
                </div>
              ),
            },
            {
              key: 'context_title',
              header: 'Контекст',
              render: (value, row) => (
                <div className="min-w-0">
                  <p className="truncate text-sm text-slate-700">{value || 'Без темы'}</p>
                  <p className="text-xs text-slate-400">{scopeLabel(row.exam_scope)}</p>
                </div>
              ),
            },
            {
              key: 'status',
              header: 'Статус',
              render: (value) => <ExamStatusBadge status={value} />,
            },
            {
              key: 'accuracy',
              header: 'Результат',
              render: (value, row) => (
                <div>
                  <p className="font-medium text-slate-800">{formatPercent(value)}</p>
                  <p className="text-xs text-slate-400">{row.correct_answers}/{row.total_answers}</p>
                </div>
              ),
            },
            {
              key: 'pending_evaluations',
              header: 'Проверка',
              render: (value, row) => (
                <EvaluationBadge pending={value} failed={row.failed_evaluations} />
              ),
            },
            {
              key: 'start_exam',
              header: 'Дата',
              render: (_, row) => (
                <span className="whitespace-nowrap text-xs">{formatDate(row.end_exam || row.start_exam)}</span>
              ),
            },
          ]}
        />
      </section>
    </div>
  )
}

function MetricCard({ icon: Icon, label, value, sub, color }) {
  const colors = {
    blue: 'bg-blue-50 text-blue-600 ring-blue-200',
    green: 'bg-green-50 text-green-600 ring-green-200',
    amber: 'bg-amber-50 text-amber-600 ring-amber-200',
  }

  return (
    <div className="card p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-medium text-slate-500">{label}</p>
          <p className="mt-1 text-3xl font-bold text-slate-900">{value ?? '—'}</p>
          {sub && <p className="mt-1 truncate text-xs text-slate-400">{sub}</p>}
        </div>
        <div className={clsx('rounded-lg p-3 ring-1', colors[color] || colors.blue)}>
          <Icon size={20} />
        </div>
      </div>
    </div>
  )
}

function SectionHeader({ title, subtitle }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-slate-200 px-5 py-4">
      <div className="min-w-0">
        <h2 className="truncate text-sm font-semibold text-slate-800">{title}</h2>
        {subtitle && <p className="mt-0.5 truncate text-xs text-slate-400">{subtitle}</p>}
      </div>
    </div>
  )
}

function BlockProgress({ block, totalUsers }) {
  const passedRatio = safeRatio(block.users_passed_block, totalUsers)

  return (
    <div className="px-5 py-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <BookOpen size={16} className="text-blue-500" />
            <h3 className="truncate text-sm font-semibold text-slate-800">{block.title}</h3>
          </div>
          <p className="mt-1 text-xs text-slate-400">
            {block.total_topics} тем · {block.block_attempts} попыток блока · средний балл {formatPercent(block.average_block_score)}
          </p>
        </div>
        <div className="w-full lg:w-56">
          <div className="flex justify-between text-xs text-slate-500">
            <span>Прошли блок</span>
            <span>{block.users_passed_block}/{totalUsers || 0}</span>
          </div>
          <ProgressBar value={passedRatio} className="mt-2" />
        </div>
      </div>

      {block.topics.length > 0 && (
        <div className="mt-4 grid gap-2 lg:grid-cols-2">
          {block.topics.map((topic) => (
            <div key={topic.id} className="rounded-lg border border-slate-100 bg-slate-50 px-3 py-2">
              <div className="flex items-start justify-between gap-2">
                <p className="min-w-0 truncate text-xs font-medium text-slate-700">{topic.title}</p>
                <span className="shrink-0 text-xs text-slate-400">{formatPercent(topic.average_score)}</span>
              </div>
              <div className="mt-2 flex items-center gap-2">
                <ProgressBar value={safeRatio(topic.users_passed, totalUsers)} />
                <span className="w-14 shrink-0 text-right text-xs text-slate-500">
                  {topic.users_passed}/{totalUsers || 0}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function ActivityRow({ item, max }) {
  const width = safeRatio(item.total_exams, max)
  return (
    <div>
      <div className="flex items-center justify-between gap-3 text-xs">
        <span className="text-slate-500">{formatShortDate(item.day)}</span>
        <span className="font-medium text-slate-800">
          {item.total_exams} экзам. · {formatPercent(item.average_score)}
        </span>
      </div>
      <ProgressBar value={width} className="mt-1.5" />
    </div>
  )
}

function UserDetail({ data }) {
  const { summary, course_progress: courseProgress } = data

  return (
    <div className="divide-y divide-slate-100">
      <div className="grid grid-cols-2 gap-3 p-5">
        <MiniMetric label="Экзаменов" value={summary.total_exams} sub={`${summary.completed_exams} завершено`} />
        <MiniMetric label="Точность" value={formatPercent(summary.accuracy)} sub={`${summary.correct_answers}/${summary.total_answers}`} />
        <MiniMetric label="Курс" value={<StatusBadge status={courseProgress.status} />} sub={`${courseProgress.attempts} попыток`} />
        <MiniMetric label="Последняя активность" value={formatDate(summary.last_activity_at)} />
      </div>
      <div className="p-5">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Блоки и темы</h3>
        <div className="mt-3 space-y-3">
          {data.blocks.map((block) => (
            <div key={block.id} className="rounded-lg border border-slate-100">
              <div className="flex items-center justify-between gap-3 bg-slate-50 px-3 py-2">
                <p className="truncate text-sm font-medium text-slate-800">{block.title}</p>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-500">{formatPercent(block.best_score)}</span>
                  <StatusBadge status={block.status} />
                </div>
              </div>
              <div className="divide-y divide-slate-100">
                {block.topics.map((topic) => (
                  <div key={topic.id} className="flex items-center justify-between gap-3 px-3 py-2">
                    <p className="min-w-0 truncate text-xs text-slate-600">{topic.title}</p>
                    <div className="flex shrink-0 items-center gap-2">
                      <span className="text-xs text-slate-500">{formatPercent(topic.best_score)}</span>
                      <StatusBadge status={topic.status} compact />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function MiniMetric({ label, value, sub }) {
  return (
    <div className="rounded-lg border border-slate-100 bg-slate-50 p-3">
      <p className="text-xs text-slate-400">{label}</p>
      <div className="mt-1 text-sm font-semibold text-slate-900">{value ?? '—'}</div>
      {sub && <p className="mt-1 text-xs text-slate-400">{sub}</p>}
    </div>
  )
}

function ProgressCell({ value, label }) {
  return (
    <div className="w-32">
      <div className="flex items-center justify-between text-xs">
        <span className="text-slate-500">{label}</span>
        <span className="font-medium text-slate-800">{formatPercent(value)}</span>
      </div>
      <ProgressBar value={value} className="mt-1.5" />
    </div>
  )
}

function ProgressBar({ value, className = '' }) {
  const width = `${Math.max(0, Math.min(Number(value) || 0, 1)) * 100}%`
  return (
    <div className={clsx('h-2 flex-1 overflow-hidden rounded-full bg-slate-200', className)}>
      <div className="h-full rounded-full bg-blue-600" style={{ width }} />
    </div>
  )
}

function StatusBadge({ status, compact = false }) {
  const meta = statusMeta(status)
  return (
    <span className={clsx('badge whitespace-nowrap', meta.className, compact && 'px-2 py-0 text-[11px]')}>
      {compact ? meta.shortLabel : meta.label}
    </span>
  )
}

function ExamStatusBadge({ status }) {
  if (status === 'Выполнен') {
    return (
      <span className="badge bg-green-50 text-green-700">
        <CheckCircle2 size={12} className="mr-1" />
        Выполнен
      </span>
    )
  }
  if (status === 'В работе') {
    return (
      <span className="badge bg-amber-50 text-amber-700">
        <Clock3 size={12} className="mr-1" />
        В работе
      </span>
    )
  }
  return <span className="badge bg-slate-100 text-slate-600">{status || '—'}</span>
}

function EvaluationBadge({ pending, failed }) {
  if (failed > 0) {
    return (
      <span className="badge bg-red-50 text-red-700">
        <AlertTriangle size={12} className="mr-1" />
        {failed} ошибок
      </span>
    )
  }
  if (pending > 0) {
    return (
      <span className="badge bg-amber-50 text-amber-700">
        <Activity size={12} className="mr-1" />
        {pending} в проверке
      </span>
    )
  }
  return <span className="badge bg-green-50 text-green-700">Готово</span>
}

function Pagination({ page, total, limit, onPrev, onNext }) {
  const pages = Math.max(Math.ceil(total / limit), 1)
  return (
    <div className="flex items-center justify-between border-t border-slate-100 px-5 py-3">
      <p className="text-xs text-slate-400">
        Страница {page} из {pages}
      </p>
      <div className="flex gap-2">
        <button className="btn-secondary px-3 py-1.5 text-xs" onClick={onPrev} disabled={page <= 1}>
          <ChevronLeft size={14} />Назад
        </button>
        <button className="btn-secondary px-3 py-1.5 text-xs" onClick={onNext} disabled={page >= pages}>
          Вперёд<ChevronRight size={14} />
        </button>
      </div>
    </div>
  )
}

function LoadingRow() {
  return (
    <div className="flex items-center justify-center gap-2 py-12 text-sm text-slate-400">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
      Загрузка...
    </div>
  )
}

function EmptyRow({ text }) {
  return <p className="py-12 text-center text-sm text-slate-400">{text}</p>
}

function statusMeta(status) {
  if (status === 'passed') {
    return { label: 'Пройдено', shortLabel: 'OK', className: 'bg-green-50 text-green-700' }
  }
  if (status === 'failed') {
    return { label: 'Не сдано', shortLabel: 'Fail', className: 'bg-red-50 text-red-700' }
  }
  if (status === 'in_progress') {
    return { label: 'В процессе', shortLabel: 'Run', className: 'bg-amber-50 text-amber-700' }
  }
  return { label: 'Не начато', shortLabel: '—', className: 'bg-slate-100 text-slate-600' }
}

function scopeLabel(scope) {
  if (scope === 'topic') return 'Тема'
  if (scope === 'block') return 'Блок'
  if (scope === 'final') return 'Итоговый экзамен'
  return 'Отдельный экзамен'
}

function formatShortDate(value) {
  if (!value) return '—'
  return new Intl.DateTimeFormat('ru-RU', { day: '2-digit', month: '2-digit' }).format(new Date(value))
}

function maxActivity(items = []) {
  return Math.max(...items.map((item) => Number(item.total_exams || 0)), 1)
}

function safeRatio(part, total) {
  const totalValue = Number(total || 0)
  if (totalValue <= 0) return 0
  return Number(part || 0) / totalValue
}
