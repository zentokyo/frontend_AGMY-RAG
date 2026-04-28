import { useQuery } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { getThemeDownloadInfo, getThemes } from '../api/appThemes.js'

export default function TheoryPage() {
  const themes = useQuery({
    queryKey: ['themes-list'],
    queryFn: getThemes,
  })

  async function handleDownload(themeId) {
    try {
      const data = await getThemeDownloadInfo(themeId)
      toast.success(`Файлов в теме: ${data.files?.length ?? 0}`)
    } catch (err) {
      toast.error(err.response?.data?.error || 'Не удалось получить данные для скачивания')
    }
  }

  return (
    <div>
      <h1 className="text-xl font-semibold text-slate-900 sm:text-2xl">Теория</h1>
      <p className="mt-2 text-sm text-slate-600">Темы и материалы для обучения.</p>
      <div className="mt-4 grid gap-3">
        {(themes.data || []).map((theme) => (
          <div key={theme.theme_id} className="card p-4 flex items-center justify-between">
            <div>
              <p className="font-medium text-slate-900">{theme.title}</p>
              <p className="text-xs text-slate-500">Файлов: {theme.file_count}</p>
            </div>
            <button className="btn-secondary" onClick={() => handleDownload(theme.theme_id)}>
              Получить ZIP
            </button>
          </div>
        ))}
        {themes.isLoading && <p className="text-sm text-slate-500">Загрузка тем...</p>}
      </div>
    </div>
  )
}
