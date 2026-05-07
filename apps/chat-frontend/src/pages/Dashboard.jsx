import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { BookOpen, BarChart3, ChevronRight, CheckCircle, Trophy } from 'lucide-react'
import clsx from 'clsx'
import { getCourseBlocks } from '../api/appCourse.js'
import { getAllStats } from '../api/appStats.js'
import useAuthStore from '../store/authStore.js'

function ProgressBar({ value }) {
  return (
    <div className="h-2 w-full rounded-full bg-slate-200">
      <div
        className="h-full rounded-full bg-blue-500 transition-all"
        style={{ width: `${Math.round(value * 100)}%` }}
      />
    </div>
  )
}

export default function Dashboard() {
  const user = useAuthStore((s) => s.user)

  const courseData = useQuery({
    queryKey: ['course-blocks'],
    queryFn: getCourseBlocks,
  })

  const statsData = useQuery({
    queryKey: ['app-stats-all'],
    queryFn: getAllStats,
  })

  const blocks = courseData.data?.blocks ?? []
  const courseProgress = courseData.data?.course_progress ?? { status: 'not_started' }
  const totalBlocks = blocks.length
  const passedBlocks = blocks.filter((b) => b.user_status === 'passed').length
  const totalTopics = blocks.reduce((s, b) => s + (b.topics_total ?? 0), 0)
  const passedTopics = blocks.reduce((s, b) => s + (b.topics_passed ?? 0), 0)
  const courseOverallProgress = totalTopics > 0 ? passedTopics / totalTopics : 0

  // Find current block (first unlocked and not passed)
  const currentBlock = blocks.find((b) => b.is_unlocked && b.user_status !== 'passed')

  const accuracy = Math.round((statsData.data?.accuracy ?? 0) * 100)

  return (
    <div className="space-y-5">
      {/* Greeting */}
      <div>
        <h1 className="text-xl font-semibold text-slate-900 sm:text-2xl">
          Добро пожаловать{user?.username ? `, ${user.username}` : ''}!
        </h1>
        <p className="mt-1 text-sm text-slate-600">Продолжайте обучение с того места, где остановились.</p>
      </div>

      {/* Course completed banner */}
      {courseProgress.status === 'passed' && (
        <div className="card flex items-center gap-3 bg-green-50 p-4">
          <Trophy size={24} className="text-green-500 shrink-0" />
          <div>
            <p className="font-medium text-green-800">Курс успешно пройден!</p>
            <p className="text-sm text-green-700">
              Финальный результат: {Math.round(courseProgress.best_score * 100)}%
            </p>
          </div>
        </div>
      )}

      {/* Course progress */}
      {!courseData.isLoading && totalBlocks > 0 && (
        <div className="card p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-medium text-slate-800">Прогресс курса</h2>
            <span className="text-sm text-slate-500">
              {passedTopics}/{totalTopics} тем · {passedBlocks}/{totalBlocks} блоков
            </span>
          </div>
          <ProgressBar value={courseOverallProgress} />
          {currentBlock && (
            <Link
              to={`/app/course/blocks/${currentBlock.id}`}
              className="flex items-center justify-between rounded-lg bg-blue-50 px-3 py-2.5 text-sm hover:bg-blue-100 transition-colors"
            >
              <div className="flex items-center gap-2">
                <BookOpen size={16} className="text-blue-600 shrink-0" />
                <span className="text-blue-700 font-medium">
                  Продолжить: {currentBlock.title}
                </span>
              </div>
              <ChevronRight size={16} className="text-blue-500" />
            </Link>
          )}
        </div>
      )}

      {/* Stats cards */}
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="card p-4">
          <p className="text-sm font-medium text-slate-700">Всего ответов</p>
          <p className="mt-1 text-2xl font-semibold text-slate-900">
            {statsData.data?.total_answers ?? '—'}
          </p>
        </div>
        <div className="card p-4">
          <p className="text-sm font-medium text-slate-700">Верных</p>
          <p className="mt-1 text-2xl font-semibold text-green-600">
            {statsData.data?.correct_answers ?? '—'}
          </p>
        </div>
        <div className="card p-4">
          <p className="text-sm font-medium text-slate-700">Точность</p>
          <p className={clsx(
            'mt-1 text-2xl font-semibold',
            accuracy >= 70 ? 'text-green-600' : accuracy > 0 ? 'text-amber-500' : 'text-slate-900'
          )}>
            {statsData.isLoading ? '—' : `${accuracy}%`}
          </p>
        </div>
      </div>

      {/* Quick actions */}
      <div className="flex flex-wrap gap-2">
        <Link to="/app/course" className="btn-primary flex items-center gap-2">
          <BookOpen size={16} />
          Перейти к курсу
        </Link>
        <Link to="/app/stats" className="btn-secondary flex items-center gap-2">
          <BarChart3 size={16} />
          Статистика
        </Link>
      </div>
    </div>
  )
}
