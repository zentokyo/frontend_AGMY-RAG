import { useParams } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import toast from 'react-hot-toast'
import { answerQuestion, askQuestion } from '../api/appExam.js'

export default function ExamSessionPage() {
  const { examId } = useParams()
  const [answer, setAnswer] = useState('')

  const question = useQuery({
    queryKey: ['app-ask-question', examId],
    queryFn: () => askQuestion(examId),
    retry: false,
  })

  const submit = useMutation({
    mutationFn: ({ examQuestionId, answerText }) => answerQuestion(examQuestionId, answerText),
    onSuccess: (data) => {
      setAnswer('')
      if (data.completed) {
        toast.success('Экзамен завершён')
      } else {
        toast.success(data.is_correct ? 'Верно!' : 'Ответ принят')
      }
      question.refetch()
    },
    onError: (err) => {
      toast.error(err.response?.data?.error || 'Не удалось отправить ответ')
    },
  })

  const q = question.data?.question

  return (
    <div>
      <h1 className="text-xl font-semibold text-slate-900 sm:text-2xl">Экзамен</h1>
      <p className="mt-2 text-sm text-slate-600">
        Сессия: <code className="rounded bg-slate-100 px-1.5 py-0.5 text-xs">{examId}</code>
      </p>
      <div className="card mt-4 p-4">
        {question.isLoading && <p className="text-sm text-slate-500">Загрузка вопроса...</p>}
        {question.isError && (
          <p className="text-sm text-slate-600">
            {question.error?.response?.data?.error || 'Вопросы закончились или экзамен завершён.'}
          </p>
        )}
        {q && (
          <>
            <p className="text-sm text-slate-500">Вопрос</p>
            <p className="mt-1 font-medium text-slate-900">{q.text}</p>
            <div className="mt-4 space-y-2">
              <label className="label" htmlFor="answer">Ваш ответ</label>
              <textarea
                id="answer"
                className="input min-h-24"
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                placeholder="Введите ответ"
              />
            </div>
            <button
              className="btn-primary mt-3"
              onClick={() => submit.mutate({ examQuestionId: q.exam_question_id, answerText: answer })}
              disabled={!answer.trim() || submit.isPending}
            >
              {submit.isPending ? 'Отправка...' : 'Отправить ответ'}
            </button>
          </>
        )}
      </div>
    </div>
  )
}
