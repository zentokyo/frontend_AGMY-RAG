import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams, Link } from 'react-router-dom'
import toast from 'react-hot-toast'
import { CheckCircle, XCircle, BookOpen, RefreshCw, ChevronRight, Trophy, Loader2 } from 'lucide-react'
import clsx from 'clsx'
import { getExamResult, startTopicExam, startBlockExam, startFinalExam } from '../api/appCourse.js'
import { createExam } from '../api/appExam.js'

function ScoreRing({ score }) {
  const pct = Math.round(score * 100)
  const passed = score >= 0.7
  return (
    <div className={clsx(
      'flex h-24 w-24 flex-col items-center justify-center rounded-full border-4',
      passed ? 'border-green-400 bg-green-50' : 'border-red-300 bg-red-50'
    )}>
      <span className={clsx('text-2xl font-bold', passed ? 'text-green-700' : 'text-red-600')}>
        {pct}%
      </span>
      <span className={clsx('text-xs font-medium', passed ? 'text-green-600' : 'text-red-500')}>
        {passed ? 'Сдано' : 'Не сдано'}
      </span>
    </div>
  )
}

function RetryDialog({ result, onReviewMaterials, onRetry, retryPending }) {
  return (
    <div className="card border-amber-200 bg-amber-50 p-5 space-y-3">
      <div className="flex items-center gap-2">
        <XCircle size={20} className="text-amber-600 shrink-0" />
        <p className="font-medium text-amber-900">Тест не пройден</p>
      </div>
      <p className="text-sm text-amber-800">
        Для прохождения нужно набрать минимум {Math.round(result.pass_threshold * 100)}%. Вы набрали {Math.round(result.score * 100)}%.
      </p>
      <p className="text-sm font-medium text-amber-900">Повторить материалы?</p>
      <div className="flex flex-wrap gap-2">
        <button
          className="btn-primary flex items-center gap-2"
          onClick={onReviewMaterials}
        >
          <BookOpen size={16} />
          Да, повторить материалы
        </button>
        <button
          className="btn-secondary flex items-center gap-2"
          disabled={retryPending}
          onClick={onRetry}
        >
          <RefreshCw size={16} className={clsx(retryPending && 'animate-spin')} />
          {retryPending ? 'Запуск...' : 'Нет, попробовать снова'}
        </button>
      </div>
    </div>
  )
}

export default function ExamResultsPage() {
  const { examId } = useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()

  const { data: result, isLoading, isError } = useQuery({
    queryKey: ['exam-result', examId],
    queryFn: () => getExamResult(examId),
    retry: false,
    refetchInterval: (query) => {
      const data = query.state.data
      return data && !data.result_ready ? 2000 : false
    },
  })

  const retryMutation = useMutation({
    mutationFn: async () => {
      const scope = result?.exam_scope
      const ctx = result?.context ?? {}
      if (scope === 'topic' && ctx.topic_id) return startTopicExam(ctx.topic_id)
      if (scope === 'block' && ctx.block_id) return startBlockExam(ctx.block_id)
      if (scope === 'final') return startFinalExam()
      return createExam({ question_count: 10 })
    },
    onSuccess: ({ exam_id }) => {
      qc.invalidateQueries({ queryKey: ['course-blocks'] })
      navigate(`/app/exams/${exam_id}`, { replace: true })
    },
    onError: (err) => {
      toast.error(err?.response?.data?.error || 'Не удалось запустить повторный тест')
    },
  })

  function goReviewMaterials() {
    const scope = result?.exam_scope
    const ctx = result?.context ?? {}
    if (scope === 'topic' && ctx.block_id && ctx.topic_id) {
      navigate(`/app/course/blocks/${ctx.block_id}/topics/${ctx.topic_id}`)
    } else if ((scope === 'block' || scope === 'final') && ctx.block_id) {
      navigate(`/app/course/blocks/${ctx.block_id}`)
    } else {
      navigate('/app/course')
    }
  }

  function goNext() {
    const scope = result?.exam_scope
    const ctx = result?.context ?? {}
    if (scope === 'topic' && ctx.block_id) {
      navigate(`/app/course/blocks/${ctx.block_id}`)
    } else if (scope === 'block') {
      navigate('/app/course')
    } else if (scope === 'final') {
      navigate('/app/course')
    } else {
      navigate('/app/exams')
    }
  }

  if (isLoading) return <p className="text-sm text-slate-500">Загрузка результатов...</p>

  if (isError) {
    return (
      <div className="space-y-3">
        <p className="text-sm text-slate-600">Не удалось загрузить результаты.</p>
        <Link to="/app/course" className="btn-secondary inline-flex">На главную курса</Link>
      </div>
    )
  }

  const isReady = result.result_ready !== false
  const isPassed = result.is_passed

  const scopeLabel = {
    topic: 'Тест по теме',
    block: 'Тест по блоку',
    final: 'Итоговый тест курса',
    standalone: 'Экзамен',
  }[result.exam_scope] ?? 'Экзамен'

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-slate-900 sm:text-2xl">Результаты</h1>
          <p className="mt-0.5 text-sm text-slate-500">{scopeLabel} · {result.theme_title}</p>
        </div>
        {isReady ? (
          <ScoreRing score={result.score} />
        ) : (
          <div className="flex h-24 w-24 flex-col items-center justify-center rounded-full border-4 border-blue-200 bg-blue-50">
            <Loader2 size={24} className="animate-spin text-blue-600" />
            <span className="mt-1 text-xs font-medium text-blue-700">Проверка</span>
          </div>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-3">
        <div className="card p-3 text-center">
          <p className="text-lg font-semibold text-slate-900">{result.total_answers}</p>
          <p className="text-xs text-slate-500">Вопросов</p>
        </div>
        <div className="card p-3 text-center">
          <p className="text-lg font-semibold text-green-600">{isReady ? result.correct_answers : '...'}</p>
          <p className="text-xs text-slate-500">Верных</p>
        </div>
        <div className="card p-3 text-center">
          <p className="text-lg font-semibold text-red-500">{isReady ? result.total_answers - result.correct_answers : '...'}</p>
          <p className="text-xs text-slate-500">Ошибок</p>
        </div>
      </div>

      {/* Passed banner / Retry dialog */}
      {!isReady ? (
        <div className="card flex items-center gap-3 bg-blue-50 p-4">
          <Loader2 size={20} className="animate-spin text-blue-500 shrink-0" />
          <div>
            <p className="font-medium text-blue-800">Ответы записаны, идет проверка</p>
            <p className="text-sm text-blue-700">
              Осталось проверить: {result.pending_evaluations ?? 0}. Результат обновится автоматически.
            </p>
          </div>
        </div>
      ) : isPassed && result.exam_scope === 'final' ? (
        <div className="card flex items-center gap-3 bg-green-50 p-4">
          <Trophy size={24} className="text-green-500 shrink-0" />
          <div>
            <p className="font-medium text-green-800">Поздравляем! Курс успешно пройден!</p>
            <p className="text-sm text-green-700">Результат {Math.round(result.score * 100)}% зафиксирован.</p>
          </div>
        </div>
      ) : isPassed ? (
        <div className="card flex items-center gap-3 bg-green-50 p-4">
          <CheckCircle size={20} className="text-green-500 shrink-0" />
          <p className="text-sm font-medium text-green-800">Тест пройден! Переходите к следующему шагу.</p>
        </div>
      ) : (
        <RetryDialog
          result={result}
          onReviewMaterials={goReviewMaterials}
          onRetry={() => retryMutation.mutate()}
          retryPending={retryMutation.isPending}
        />
      )}

      {/* Navigation after pass */}
      {isReady && isPassed && (
        <button className="btn-primary flex items-center gap-2" onClick={goNext}>
          {result.exam_scope === 'final' ? 'На страницу курса' : 'Продолжить'}
          <ChevronRight size={16} />
        </button>
      )}

      {/* Answer review */}
      {result.answer_list?.length > 0 && (
        <div className="space-y-2">
          <h2 className="text-sm font-medium text-slate-700 uppercase tracking-wide">Разбор ответов</h2>
          <div className="space-y-2">
            {result.answer_list.map((a, i) => (
              <div
                key={i}
                className={clsx(
                  'card p-3 text-sm',
                  a.evaluation_status === 'pending' || a.evaluation_status === 'evaluating'
                    ? 'border-blue-200'
                    : a.is_correct
                      ? 'border-green-200'
                      : 'border-red-200'
                )}
              >
                <p className="font-medium text-slate-800">{i + 1}. {a.question_text}</p>
                <div className="mt-1.5 grid grid-cols-1 gap-1 sm:grid-cols-2">
                  <div className="flex items-start gap-1.5">
                    {a.evaluation_status === 'pending' || a.evaluation_status === 'evaluating'
                      ? <Loader2 size={14} className="animate-spin text-blue-500 mt-0.5 shrink-0" />
                      : a.is_correct
                      ? <CheckCircle size={14} className="text-green-500 mt-0.5 shrink-0" />
                      : <XCircle size={14} className="text-red-400 mt-0.5 shrink-0" />
                    }
                    <p className="text-slate-700">Ваш: <span className="font-medium">{a.user_answer}</span></p>
                  </div>
                  {a.evaluation_status !== 'pending' && a.evaluation_status !== 'evaluating' && !a.is_correct && (
                    <p className="text-slate-500">Верный: <span className="font-medium text-green-700">{a.model_answer}</span></p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
