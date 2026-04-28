import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { createExam, getExamThemes, getInProgressExam } from '../api/appExam.js'

export default function ExamsPage() {
  const navigate = useNavigate()
  const qc = useQueryClient()

  const themes = useQuery({
    queryKey: ['app-exam-themes'],
    queryFn: getExamThemes,
  })

  const inProgress = useQuery({
    queryKey: ['app-exam-in-progress'],
    queryFn: getInProgressExam,
    retry: false,
  })

  const createMutation = useMutation({
    mutationFn: createExam,
    onSuccess: (exam) => {
      qc.invalidateQueries({ queryKey: ['app-exam-in-progress'] })
      navigate(`/app/exams/${exam.exam_id}`)
    },
    onError: (err) => {
      const exam = err?.response?.data?.exam
      if (exam?.exam_id) {
        toast('У вас уже есть активный экзамен, открываю его')
        navigate(`/app/exams/${exam.exam_id}`)
        return
      }
      toast.error(err.response?.data?.error || 'Не удалось создать экзамен')
    },
  })

  function startExam(themeId) {
    createMutation.mutate({ question_count: 10, exam_theme_id: themeId })
  }

  return (
    <div>
      <h1 className="text-xl font-semibold text-slate-900 sm:text-2xl">Экзамены</h1>
      {inProgress.data?.exam_id && (
        <div className="card mt-4 p-4">
          <p className="text-sm text-slate-700">У вас есть активный экзамен.</p>
          <button
            className="btn-primary mt-3"
            onClick={() => navigate(`/app/exams/${inProgress.data.exam_id}`)}
          >
            Продолжить
          </button>
        </div>
      )}
      <div className="mt-4 grid gap-3">
        {(themes.data || []).map((theme) => (
          <div key={theme.exam_theme_id} className="card p-4 flex items-center justify-between">
            <div>
              <p className="font-medium text-slate-900">{theme.title}</p>
              <p className="text-xs text-slate-500">Порядок: {theme.exam_theme_order}</p>
            </div>
            <button
              className="btn-primary"
              onClick={() => startExam(theme.exam_theme_id)}
              disabled={createMutation.isPending}
            >
              Начать
            </button>
          </div>
        ))}
        {themes.isLoading && <p className="text-sm text-slate-500">Загрузка тем...</p>}
      </div>
    </div>
  )
}
