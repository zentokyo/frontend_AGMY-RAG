import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { Lock, CheckCircle, XCircle, ChevronRight, Trophy } from 'lucide-react'
import clsx from 'clsx'
import { getCourseBlocks, startFinalExam } from '../api/appCourse.js'

function statusIcon(status, isUnlocked) {
  if (!isUnlocked) return <Lock size={18} className="text-slate-400" />
  if (status === 'passed') return <CheckCircle size={18} className="text-green-500" />
  if (status === 'failed') return <XCircle size={18} className="text-red-400" />
  return <ChevronRight size={18} className="text-blue-500" />
}

function ProgressBar({ value, className }) {
  return (
    <div className={clsx('h-1.5 w-full rounded-full bg-slate-200', className)}>
      <div
        className="h-full rounded-full bg-blue-500 transition-all"
        style={{ width: `${Math.round(value * 100)}%` }}
      />
    </div>
  )
}

export default function CoursePage() {
  const navigate = useNavigate()
  const qc = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['course-blocks'],
    queryFn: getCourseBlocks,
  })

  const finalExamMutation = useMutation({
    mutationFn: startFinalExam,
    onSuccess: ({ exam_id }) => {
      qc.invalidateQueries({ queryKey: ['course-blocks'] })
      navigate(`/app/exams/${exam_id}`)
    },
    onError: (err) => {
      const msg = err?.response?.data?.error
      if (err?.response?.data?.exam_id) {
        navigate(`/app/exams/${err.response.data.exam_id}`)
        return
      }
      toast.error(msg || 'Не удалось запустить итоговый тест')
    },
  })

  const blocks = data?.blocks ?? []
  const courseProgress = data?.course_progress ?? { status: 'not_started' }
  const finalUnlocked = data?.final_exam_unlocked ?? false

  if (isLoading) {
    return <p className="text-sm text-slate-500">Загрузка курса...</p>
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-semibold text-slate-900 sm:text-2xl">Курс</h1>
        <p className="mt-1 text-sm text-slate-600">
          Изучите каждый блок, сдайте тест — переходите к следующему.
        </p>
      </div>

      {/* Course completed banner */}
      {courseProgress.status === 'passed' && (
        <div className="card flex items-center gap-3 bg-green-50 p-4">
          <Trophy size={24} className="text-green-500 shrink-0" />
          <div>
            <p className="font-medium text-green-800">Курс пройден!</p>
            <p className="text-sm text-green-700">
              Лучший результат: {Math.round(courseProgress.best_score * 100)}%
            </p>
          </div>
        </div>
      )}

      {/* Blocks grid */}
      <div className="space-y-3">
        {blocks.map((block) => {
          const progress = block.topics_total > 0 ? block.topics_passed / block.topics_total : 0
          return (
            <button
              key={block.id}
              disabled={!block.is_unlocked}
              onClick={() => block.is_unlocked && navigate(`/app/course/blocks/${block.id}`)}
              className={clsx(
                'card w-full p-4 text-left transition-shadow',
                block.is_unlocked
                  ? 'hover:shadow-md cursor-pointer'
                  : 'cursor-not-allowed opacity-60'
              )}
            >
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-3 min-w-0">
                  {statusIcon(block.user_status, block.is_unlocked)}
                  <div className="min-w-0">
                    <p className="font-medium text-slate-900 truncate">{block.title}</p>
                    {block.description && (
                      <p className="text-xs text-slate-500 mt-0.5 truncate">{block.description}</p>
                    )}
                  </div>
                </div>
                <div className="shrink-0 text-right">
                  <p className="text-xs text-slate-500">
                    {block.topics_passed}/{block.topics_total} тем
                  </p>
                  {block.user_status === 'passed' && (
                    <p className="text-xs text-green-600 font-medium">
                      {Math.round(block.best_score * 100)}%
                    </p>
                  )}
                </div>
              </div>
              {block.is_unlocked && block.topics_total > 0 && (
                <ProgressBar value={progress} className="mt-3" />
              )}
            </button>
          )
        })}
      </div>

      {/* Final exam section */}
      {blocks.length > 0 && (
        <div className={clsx('card p-4', !finalUnlocked && courseProgress.status !== 'passed' && 'opacity-60')}>
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              {courseProgress.status === 'passed'
                ? <CheckCircle size={20} className="text-green-500" />
                : finalUnlocked
                  ? <Trophy size={20} className="text-amber-500" />
                  : <Lock size={20} className="text-slate-400" />
              }
              <div>
                <p className="font-medium text-slate-900">Итоговый тест курса</p>
                <p className="text-xs text-slate-500">
                  {finalUnlocked || courseProgress.status === 'passed'
                    ? 'Доступен после прохождения всех блоков'
                    : 'Пройдите все блоки для разблокировки'}
                </p>
              </div>
            </div>
            <button
              className="btn-primary shrink-0"
              disabled={!finalUnlocked || finalExamMutation.isPending}
              onClick={() => finalExamMutation.mutate()}
            >
              {finalExamMutation.isPending ? 'Запуск...' : courseProgress.status === 'passed' ? 'Пересдать' : 'Начать'}
            </button>
          </div>
          {courseProgress.status !== 'not_started' && (
            <p className="mt-2 text-xs text-slate-500">
              Попыток: {courseProgress.attempts} · Лучший результат: {Math.round(courseProgress.best_score * 100)}%
            </p>
          )}
        </div>
      )}
    </div>
  )
}
