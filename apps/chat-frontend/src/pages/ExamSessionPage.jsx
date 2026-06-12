import { useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import toast from 'react-hot-toast'
import { answerQuestion, askQuestion } from '../api/appExam.js'

export default function ExamSessionPage() {
  const { examId } = useParams()
  const navigate = useNavigate()
  const [answer, setAnswer] = useState('')
  const [isAdvancing, setIsAdvancing] = useState(false)

  const question = useQuery({
    queryKey: ['app-ask-question', examId],
    queryFn: () => askQuestion(examId),
    retry: false,
  })

  const submit = useMutation({
    mutationFn: ({ examQuestionId, answerText }) => answerQuestion(examQuestionId, answerText),
    onSuccess: async (data) => {
      setAnswer('')
      toast.success('Ответ записан')
      if (data.completed) {
        navigate(`/app/exams/${examId}/result`, { replace: true })
      } else {
        setIsAdvancing(true)
        try {
          await question.refetch()
        } finally {
          setIsAdvancing(false)
        }
      }
    },
    onError: (err) => {
      setIsAdvancing(false)
      toast.error(err.response?.data?.error || 'Не удалось отправить ответ')
    },
  })

  const q = question.data?.question
  const showQuestion = q && !isAdvancing

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <h1 className="text-xl font-semibold text-slate-900 sm:text-2xl">Экзамен</h1>
      <p className="text-sm text-slate-500">
        Сессия: <code className="rounded bg-slate-100 px-1.5 py-0.5 text-xs">{examId}</code>
      </p>

      <div className="card p-5">
        {(question.isLoading || isAdvancing) && (
          <p className="text-sm text-slate-500">
            {isAdvancing ? 'Готовим следующий вопрос...' : 'Загрузка вопроса...'}
          </p>
        )}

        {question.isError && !isAdvancing && (
          <div className="space-y-3">
            <p className="text-sm text-slate-600">
              {question.error?.response?.data?.error || 'Вопросы закончились или экзамен завершён.'}
            </p>
            <button
              className="btn-secondary"
              onClick={() => navigate(`/app/exams/${examId}/result`)}
            >
              Посмотреть результаты
            </button>
          </div>
        )}

        {showQuestion && (
          <div className="space-y-4">
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Вопрос</p>
              <p className="mt-1 text-base font-medium text-slate-900">{q.text}</p>
            </div>

            <div className="space-y-1.5">
              <label className="label" htmlFor="answer">Ваш ответ</label>
              <textarea
                id="answer"
                className="input min-h-24"
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                placeholder="Введите ответ"
                disabled={submit.isPending || isAdvancing}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && e.ctrlKey && answer.trim() && !submit.isPending && !isAdvancing) {
                    submit.mutate({ examQuestionId: q.exam_question_id, answerText: answer })
                  }
                }}
              />
              <p className="text-xs text-slate-400">Ctrl+Enter для отправки</p>
            </div>

            <button
              className="btn-primary"
              onClick={() => submit.mutate({ examQuestionId: q.exam_question_id, answerText: answer })}
              disabled={!answer.trim() || submit.isPending || isAdvancing}
            >
              {submit.isPending ? 'Записываем...' : 'Отправить ответ'}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
