import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getAllStats, getLastStats } from '../api/appStats.js'
import {
  BarChart3,
  CheckCircle2,
  XCircle,
  Award,
  Target,
  ChevronDown,
  ChevronUp,
  HelpCircle,
  BookOpen
} from 'lucide-react'
import clsx from 'clsx'

function AccuracyGauge({ accuracy }) {
  const radius = 42
  const strokeWidth = 8
  const circumference = 2 * Math.PI * radius
  const percentage = Math.round(accuracy * 100)
  const strokeDashoffset = circumference - (percentage / 100) * circumference

  return (
    <div className="flex flex-col items-center justify-center space-y-2">
      <div className="relative flex items-center justify-center">
        <svg className="w-28 h-28 transform -rotate-90">
          <defs>
            <linearGradient id="accGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#3b82f6" />
              <stop offset="100%" stopColor="#10b981" />
            </linearGradient>
          </defs>
          <circle
            cx="56"
            cy="56"
            r={radius}
            strokeWidth={strokeWidth}
            className="stroke-slate-100 fill-none"
          />
          <circle
            cx="56"
            cy="56"
            r={radius}
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            stroke="url(#accGrad)"
            className="fill-none transition-all duration-1000 ease-out"
          />
        </svg>
        <div className="absolute text-center">
          <span className="text-2xl font-bold text-slate-800">
            {percentage}%
          </span>
        </div>
      </div>
      <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Точность</span>
    </div>
  )
}

export default function StatsPage() {
  const [expandedQuestion, setExpandedQuestion] = useState(null)

  const allStats = useQuery({
    queryKey: ['stats-all'],
    queryFn: getAllStats,
  })

  const lastStats = useQuery({
    queryKey: ['stats-last'],
    queryFn: getLastStats,
    retry: false,
  })

  const globalAccuracy = allStats.data?.accuracy ?? 0
  const themeStats = allStats.data?.stat_by_theme ?? []
  const hasLastExam = !!lastStats.data

  return (
    <div className="space-y-6 text-slate-900">
      {/* Page Header */}
      <div>
        <h1 className="text-xl font-bold text-slate-900 sm:text-2xl flex items-center gap-2">
          <BarChart3 className="text-blue-500" size={24} />
          Статистика обучения
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Следите за своим прогрессом по всем темам курса и анализируйте результаты.
        </p>
      </div>

      {allStats.isLoading ? (
        <div className="flex justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
        </div>
      ) : (
        <>
          {/* Main Grid */}
          <div className="grid gap-6 md:grid-cols-3">
            {/* Circle Progress + Quick Overview */}
            <div className="card bg-white border-slate-200 p-6 flex flex-col justify-between items-center sm:flex-row md:flex-col sm:justify-around md:justify-between col-span-1">
              <AccuracyGauge accuracy={globalAccuracy} />
              <div className="w-full mt-4 sm:mt-0 md:mt-4 space-y-3">
                <div className="flex justify-between items-center bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                  <div className="flex items-center gap-2">
                    <HelpCircle size={16} className="text-blue-500" />
                    <span className="text-sm text-slate-600">Всего ответов</span>
                  </div>
                  <span className="font-bold text-slate-800">
                    {allStats.data?.total_answers ?? 0}
                  </span>
                </div>
                <div className="flex justify-between items-center bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 size={16} className="text-emerald-500" />
                    <span className="text-sm text-slate-600">Верно отвечено</span>
                  </div>
                  <span className="font-bold text-slate-800">
                    {allStats.data?.correct_answers ?? 0}
                  </span>
                </div>
              </div>
            </div>

            {/* Performance by Theme */}
            <div className="card bg-white border-slate-200 p-6 col-span-1 md:col-span-2 space-y-4">
              <h2 className="font-bold text-slate-900 flex items-center gap-2 border-b border-slate-100 pb-3">
                <Award className="text-amber-500" size={18} />
                Успеваемость по темам
              </h2>

              {themeStats.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <p className="text-sm text-slate-500">Пока нет статистики по отдельным темам.</p>
                </div>
              ) : (
                <div className="space-y-4 max-h-60 overflow-y-auto pr-1">
                  {themeStats.map((theme, i) => {
                    const pct = Math.round((theme.accuracy || 0) * 100)
                    return (
                      <div key={i} className="space-y-1.5">
                        <div className="flex justify-between text-xs font-semibold">
                          <span className="text-slate-700 truncate max-w-[75%]">
                            {theme.theme_title}
                          </span>
                          <span className="text-slate-500">
                            {theme.correct_answers}/{theme.total_answers} ({pct}%)
                          </span>
                        </div>
                        <div className="w-full bg-slate-100 h-3 rounded-full overflow-hidden">
                          <div
                            className={clsx(
                              "h-full rounded-full transition-all duration-500",
                              pct >= 80 ? "bg-gradient-to-r from-emerald-400 to-teal-500" :
                              pct >= 60 ? "bg-gradient-to-r from-amber-400 to-orange-500" :
                              "bg-gradient-to-r from-rose-500 to-red-600"
                            )}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          </div>

          {/* Last Exam Details */}
          <div className="card bg-white border-slate-200 p-6">
            <h2 className="font-bold text-slate-900 flex items-center gap-2 border-b border-slate-100 pb-3">
              <Target className="text-rose-500" size={18} />
              Детали последнего тестирования
            </h2>

            {lastStats.isLoading ? (
              <p className="text-sm text-slate-500 py-6">Загрузка последних результатов...</p>
            ) : !hasLastExam ? (
              <div className="flex flex-col items-center justify-center py-8 text-center space-y-2">
                <p className="text-sm text-slate-500">У вас пока нет завершенных экзаменов или тестов.</p>
              </div>
            ) : (
              <div className="mt-4 space-y-4">
                {/* Last Exam Score Card */}
                <div className="flex flex-col sm:flex-row justify-between sm:items-center bg-slate-50 p-4 rounded-xl border border-slate-100 gap-4">
                  <div className="space-y-1">
                    <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Тема теста</span>
                    <h3 className="font-bold text-slate-800">
                      {lastStats.data.theme_title || 'Смешанный тест'}
                    </h3>
                  </div>
                  <div className="flex gap-4">
                    <div className="bg-white border border-slate-100 py-2 px-4 rounded-lg text-center shadow-xs">
                      <p className="text-lg font-bold text-slate-800">
                        {lastStats.data.correct_answers} / {lastStats.data.total_answers}
                      </p>
                      <p className="text-xxs font-medium text-slate-500">Верных ответов</p>
                    </div>
                    <div className="bg-white border border-slate-100 py-2 px-4 rounded-lg text-center shadow-xs">
                      <p className={clsx(
                        "text-lg font-bold",
                        lastStats.data.accuracy >= 0.7 ? "text-emerald-500" : "text-rose-500"
                      )}>
                        {Math.round(lastStats.data.accuracy * 100)}%
                      </p>
                      <p className="text-xxs font-medium text-slate-500">Результат</p>
                    </div>
                  </div>
                </div>

                {/* Question Breakdown Accordion */}
                <div className="space-y-2">
                  <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Разбор вопросов</h4>
                  {lastStats.data.answer_list?.length === 0 ? (
                    <p className="text-sm text-slate-500">Разбор ответов недоступен.</p>
                  ) : (
                    <div className="space-y-2">
                      {lastStats.data.answer_list.map((a, i) => {
                        const isExpanded = expandedQuestion === i
                        return (
                          <div
                            key={i}
                            className="border border-slate-100 rounded-xl overflow-hidden transition-all duration-300"
                          >
                            <button
                              onClick={() => setExpandedQuestion(isExpanded ? null : i)}
                              className="w-full flex items-center justify-between p-3.5 bg-slate-50 hover:bg-slate-100 transition-colors text-left"
                            >
                              <div className="flex items-center gap-3 min-w-0">
                                {a.is_correct ? (
                                  <CheckCircle2 size={16} className="text-emerald-500 shrink-0" />
                                ) : (
                                  <XCircle size={16} className="text-rose-500 shrink-0" />
                                )}
                                <span className="font-semibold text-slate-800 text-sm truncate">
                                  {i + 1}. {a.question_text}
                                </span>
                              </div>
                              {isExpanded ? (
                                <ChevronUp size={16} className="text-slate-400" />
                              ) : (
                                <ChevronDown size={16} className="text-slate-400" />
                              )}
                            </button>

                            {isExpanded && (
                              <div className="p-4 bg-white border-t border-slate-100 space-y-3 text-sm">
                                <div>
                                  <span className="text-xs font-semibold text-slate-500 block mb-1">
                                    Ваш ответ:
                                  </span>
                                  <p className="bg-slate-50 border border-slate-100 rounded-lg p-3 text-slate-800 font-medium">
                                    {a.user_answer || '—'}
                                  </p>
                                </div>
                                <div className="flex items-center gap-2 pt-1">
                                  <span className="text-xs text-slate-500">Вердикт системы:</span>
                                  <span className={clsx(
                                    "badge",
                                    a.is_correct
                                      ? "bg-green-100 text-green-700"
                                      : "bg-red-100 text-red-700"
                                  )}>
                                    {a.is_correct ? 'Зачтено' : 'Не зачтено'}
                                  </span>
                                </div>
                              </div>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
