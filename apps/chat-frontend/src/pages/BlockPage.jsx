import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams, Link } from 'react-router-dom'
import toast from 'react-hot-toast'
import { Lock, CheckCircle, XCircle, ChevronRight, ChevronLeft, ClipboardCheck } from 'lucide-react'
import clsx from 'clsx'
import { getBlock, startBlockExam } from '../api/appCourse.js'

function TopicStatusIcon({ status, isUnlocked }) {
  if (!isUnlocked) return <Lock size={16} className="text-slate-400 shrink-0" />
  if (status === 'passed') return <CheckCircle size={16} className="text-green-500 shrink-0" />
  if (status === 'failed') return <XCircle size={16} className="text-red-400 shrink-0" />
  return <ChevronRight size={16} className="text-blue-500 shrink-0" />
}

function StatusBadge({ status }) {
  const map = {
    passed: ['bg-green-100 text-green-700', 'Пройдено'],
    failed: ['bg-red-100 text-red-700', 'Не сдано'],
    not_started: ['bg-slate-100 text-slate-600', 'Не начато'],
  }
  const [cls, label] = map[status] ?? map.not_started
  return <span className={clsx('rounded-full px-2 py-0.5 text-xs font-medium', cls)}>{label}</span>
}

export default function BlockPage() {
  const { blockId } = useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['block', blockId],
    queryFn: () => getBlock(blockId),
  })

  const blockExamMutation = useMutation({
    mutationFn: () => startBlockExam(blockId),
    onSuccess: ({ exam_id }) => {
      qc.invalidateQueries({ queryKey: ['block', blockId] })
      navigate(`/app/exams/${exam_id}`)
    },
    onError: (err) => {
      const d = err?.response?.data
      if (d?.exam_id) { navigate(`/app/exams/${d.exam_id}`); return }
      toast.error(d?.error || 'Не удалось запустить тест блока')
    },
  })

  if (isLoading) return <p className="text-sm text-slate-500">Загрузка...</p>
  if (!data) return null

  const { block, topics, block_test_unlocked } = data

  return (
    <div className="space-y-5">
      {/* Breadcrumb */}
      <Link to="/app/course" className="inline-flex items-center gap-1 text-sm text-blue-600 hover:underline">
        <ChevronLeft size={16} />
        Курс
      </Link>

      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-slate-900 sm:text-2xl">{block.title}</h1>
          {block.description && (
            <p className="mt-1 text-sm text-slate-600">{block.description}</p>
          )}
        </div>
        <StatusBadge status={block.user_status} />
      </div>

      {/* Topics list */}
      <div className="space-y-2">
        <h2 className="text-sm font-medium text-slate-700 uppercase tracking-wide">Темы блока</h2>
        {topics.length === 0 && (
          <p className="text-sm text-slate-500">В этом блоке пока нет тем.</p>
        )}
        {topics.map((topic) => (
          <button
            key={topic.id}
            disabled={!topic.is_unlocked}
            onClick={() => topic.is_unlocked && navigate(`/app/course/blocks/${blockId}/topics/${topic.id}`)}
            className={clsx(
              'card w-full p-4 text-left transition-shadow flex items-center gap-3',
              topic.is_unlocked ? 'hover:shadow-md cursor-pointer' : 'cursor-not-allowed opacity-60'
            )}
          >
            <TopicStatusIcon status={topic.user_status} isUnlocked={topic.is_unlocked} />
            <div className="flex-1 min-w-0">
              <p className="font-medium text-slate-900 truncate">{topic.topic_order}. {topic.title}</p>
              {topic.attempts > 0 && (
                <p className="text-xs text-slate-500 mt-0.5">
                  Попыток: {topic.attempts} · Лучший результат: {Math.round(topic.best_score * 100)}%
                </p>
              )}
            </div>
            <StatusBadge status={topic.user_status} />
          </button>
        ))}
      </div>

      {/* Block test */}
      <div className={clsx('card p-4', !block_test_unlocked && 'opacity-60')}>
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            {block_test_unlocked
              ? <ClipboardCheck size={20} className="text-blue-500" />
              : <Lock size={20} className="text-slate-400" />
            }
            <div>
              <p className="font-medium text-slate-900">Тест по блоку</p>
              <p className="text-xs text-slate-500">
                {block_test_unlocked
                  ? 'Все темы пройдены — тест доступен'
                  : 'Пройдите все темы блока для разблокировки'}
              </p>
            </div>
          </div>
          <button
            className="btn-primary shrink-0"
            disabled={!block_test_unlocked || blockExamMutation.isPending}
            onClick={() => blockExamMutation.mutate()}
          >
            {blockExamMutation.isPending ? 'Запуск...' : block.user_status === 'passed' ? 'Пересдать' : 'Начать тест'}
          </button>
        </div>
        {block.attempts > 0 && (
          <p className="mt-2 text-xs text-slate-500">
            Попыток: {block.attempts} · Лучший результат: {Math.round(block.best_score * 100)}%
          </p>
        )}
      </div>
    </div>
  )
}
