import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams, Link } from 'react-router-dom'
import toast from 'react-hot-toast'
import { ChevronLeft, FileText, CheckCircle, XCircle, PlayCircle, Eye, Download } from 'lucide-react'
import clsx from 'clsx'
import { getTopic, startTopicExam } from '../api/appCourse.js'
import api from '../api/client.js'

function StatusBanner({ status, bestScore, attempts }) {
  if (status === 'not_started') return null
  const passed = status === 'passed'
  return (
    <div className={clsx(
      'flex items-center gap-3 rounded-xl px-4 py-3',
      passed ? 'bg-green-50' : 'bg-amber-50'
    )}>
      {passed
        ? <CheckCircle size={20} className="text-green-500 shrink-0" />
        : <XCircle size={20} className="text-amber-500 shrink-0" />
      }
      <div>
        <p className={clsx('text-sm font-medium', passed ? 'text-green-800' : 'text-amber-800')}>
          {passed ? 'Тема пройдена' : 'Тест не сдан'}
        </p>
        <p className={clsx('text-xs', passed ? 'text-green-700' : 'text-amber-700')}>
          Лучший результат: {Math.round(bestScore * 100)}% · Попыток: {attempts}
        </p>
      </div>
    </div>
  )
}

export default function TopicPage() {
  const { blockId, topicId } = useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['topic', blockId, topicId],
    queryFn: () => getTopic(blockId, topicId),
  })

  const handleFileAction = async (filename, action) => {
    try {
      const response = await api.get(`/app/files/${encodeURIComponent(filename)}`, {
        responseType: 'blob',
      })
      const contentType = response.headers['content-type'] || 'application/pdf'
      const blob = new Blob([response.data], { type: contentType })
      const blobUrl = window.URL.createObjectURL(blob)

      if (action === 'view') {
        window.open(blobUrl, '_blank')
      } else if (action === 'download') {
        const link = document.createElement('a')
        link.href = blobUrl
        link.setAttribute('download', filename)
        document.body.appendChild(link)
        link.click()
        link.parentNode.removeChild(link)
      }
    } catch (err) {
      toast.error('Не удалось загрузить файл')
    }
  }

  const startExamMutation = useMutation({
    mutationFn: () => startTopicExam(topicId),
    onSuccess: ({ exam_id }) => {
      qc.invalidateQueries({ queryKey: ['topic', blockId, topicId] })
      navigate(`/app/exams/${exam_id}`)
    },
    onError: (err) => {
      const d = err?.response?.data
      if (d?.exam_id) { navigate(`/app/exams/${d.exam_id}`); return }
      toast.error(d?.error || 'Не удалось запустить тест')
    },
  })

  if (isLoading) return <p className="text-sm text-slate-500">Загрузка темы...</p>
  if (!data) return null

  const { topic, materials, question_count } = data

  return (
    <div className="space-y-5">
      {/* Breadcrumb */}
      <Link to={`/app/course/blocks/${blockId}`} className="inline-flex items-center gap-1 text-sm text-blue-600 hover:underline">
        <ChevronLeft size={16} />
        Назад к блоку
      </Link>

      {/* Header */}
      <div>
        <h1 className="text-xl font-semibold text-slate-900 sm:text-2xl">{topic.title}</h1>
        <p className="mt-1 text-sm text-slate-500">Тема {topic.topic_order}</p>
      </div>

      {/* Progress status */}
      <StatusBanner
        status={topic.user_status}
        bestScore={topic.best_score}
        attempts={topic.attempts}
      />

      {!topic.is_unlocked ? (
        <div className="card p-6 text-center space-y-4 bg-white border-slate-200">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-amber-50 text-amber-500">
            <XCircle size={24} />
          </div>
          <div className="space-y-1">
            <h2 className="font-semibold text-slate-900">Тема заблокирована</h2>
            <p className="text-sm text-slate-500">
              Пройдите предыдущую тему для разблокировки доступа к материалам и тестированию.
            </p>
          </div>
        </div>
      ) : (
        <>
          <div className="card p-4 space-y-3 bg-white border-slate-200">
            <h2 className="font-medium text-slate-900">Учебные материалы</h2>
            {materials.length === 0 ? (
              <p className="text-sm text-slate-500">Материалы для этой темы не добавлены.</p>
            ) : (
              <ul className="divide-y divide-slate-100">
                {materials.map((f) => (
                  <li key={f.file_id} className="flex items-center gap-3 py-2.5 hover:bg-slate-50 rounded-lg px-2 transition-colors">
                    <FileText size={16} className="text-slate-400 shrink-0" />
                    <span className="flex-1 text-sm text-slate-700 truncate">{f.filename}</span>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleFileAction(f.filename, 'view')}
                        className="p-1 rounded-md text-slate-400 hover:text-blue-600 hover:bg-blue-50 transition-colors"
                        title="Просмотреть"
                      >
                        <Eye size={16} />
                      </button>
                      <button
                        onClick={() => handleFileAction(f.filename, 'download')}
                        className="p-1 rounded-md text-slate-400 hover:text-blue-600 hover:bg-blue-50 transition-colors"
                        title="Скачать"
                      >
                        <Download size={16} />
                      </button>
                      <span className="text-xs text-slate-400 font-medium select-none bg-slate-100 px-1.5 py-0.5 rounded">PDF</span>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* Start exam */}
          <div className="card p-4">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="font-medium text-slate-900">Тест по теме</h2>
                <p className="mt-1 text-sm text-slate-600">
                  {question_count > 0
                    ? `${Math.min(3, question_count)} вопроса · порог прохождения 70%`
                    : 'Вопросы к этой теме ещё не добавлены'}
                </p>
              </div>
              <button
                className="btn-primary shrink-0"
                disabled={!topic.is_unlocked || question_count === 0 || startExamMutation.isPending}
                onClick={() => startExamMutation.mutate()}
              >
                <PlayCircle size={16} className="mr-1.5 -ml-0.5" />
                {startExamMutation.isPending
                  ? 'Запуск...'
                  : topic.user_status === 'passed'
                    ? 'Пересдать'
                    : 'Начать тест'}
              </button>
            </div>
            {!topic.is_unlocked && (
              <p className="mt-2 text-xs text-amber-600">
                Пройдите предыдущую тему для разблокировки.
              </p>
            )}
          </div>
        </>
      )}
    </div>
  )
}
