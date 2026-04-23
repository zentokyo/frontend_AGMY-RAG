import { useState, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Upload, Trash2, FileText, RefreshCw, UploadCloud,
  ChevronDown, ChevronRight, FolderOpen, FilePlus,
} from 'lucide-react'
import toast from 'react-hot-toast'
import clsx from 'clsx'
import { getDocuments, uploadDocument, deleteDocument, addFilesToTheme } from '../api/documents.js'
import ConfirmDialog from '../components/Modal/ConfirmDialog.jsx'
import Modal from '../components/Modal/Modal.jsx'

// ─── Mini file-picker used in two places ────────────────────────────────────
function FilePicker({ files, onChange, label = 'Файлы (PDF, TXT, DOCX)', multiple = true }) {
  const ref = useRef(null)
  return (
    <div>
      {label && <label className="label">{label}</label>}
      <div
        onClick={() => ref.current?.click()}
        className="cursor-pointer rounded-xl border-2 border-dashed border-slate-300 bg-slate-50 px-4 py-5 text-center hover:border-blue-400 hover:bg-blue-50 transition-colors"
      >
        <input
          ref={ref}
          type="file"
          accept=".pdf,.txt,.docx"
          multiple={multiple}
          className="hidden"
          onChange={(e) => onChange(Array.from(e.target.files))}
        />
        <UploadCloud size={24} className="mx-auto mb-2 text-slate-400" />
        {files.length > 0 ? (
          <div className="space-y-0.5">
            {files.map((f, i) => (
              <p key={i} className="text-sm text-slate-700">
                <FileText size={12} className="inline mr-1 text-slate-400" />
                {f.name}
              </p>
            ))}
            <p className="text-xs text-slate-400 mt-1">Нажми снова, чтобы изменить</p>
          </div>
        ) : (
          <>
            <p className="text-sm font-medium text-slate-600">Выбрать файлы</p>
            <p className="text-xs text-slate-400">до 50 МБ каждый</p>
          </>
        )}
      </div>
    </div>
  )
}

// ─── Create-theme modal ──────────────────────────────────────────────────────
function CreateThemeModal({ open, onClose }) {
  const qc = useQueryClient()
  const [title,     setTitle]     = useState('')
  const [files,     setFiles]     = useState([])
  const [uploading, setUploading] = useState(false)
  const [pct,       setPct]       = useState(0)

  function reset() { setTitle(''); setFiles([]); setPct(0) }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!title.trim()) return toast.error('Укажи название темы')
    if (!files.length) return toast.error('Добавь хотя бы один файл')

    setUploading(true)
    try {
      await uploadDocument(title, files, (evt) => {
        if (evt.total) setPct(Math.round((evt.loaded / evt.total) * 100))
      })
      toast.success(`Тема «${title}» создана`)
      qc.invalidateQueries({ queryKey: ['documents'] })
      qc.invalidateQueries({ queryKey: ['document-stats'] })
      reset(); onClose()
    } catch (err) {
      toast.error(err.response?.data?.error || 'Ошибка загрузки')
    } finally {
      setUploading(false)
    }
  }

  return (
    <Modal open={open} onClose={() => { reset(); onClose() }} title="Добавить тему в базу знаний" size="md">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="label">Название темы *</label>
          <input
            type="text" className="input"
            placeholder="Например: Гражданское право"
            value={title} onChange={(e) => setTitle(e.target.value)} required
          />
        </div>

        <FilePicker files={files} onChange={setFiles} label="Файлы темы * (PDF, TXT, DOCX)" />

        {uploading && (
          <div className="space-y-1">
            <div className="flex justify-between text-xs text-slate-500">
              <span>Загрузка…</span><span>{pct}%</span>
            </div>
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-200">
              <div className="h-full rounded-full bg-blue-600 transition-all" style={{ width: `${pct}%` }} />
            </div>
          </div>
        )}

        <div className="flex justify-end gap-3 border-t border-slate-200 pt-4">
          <button type="button" className="btn-secondary" onClick={() => { reset(); onClose() }}>Отмена</button>
          <button type="submit" className="btn-primary" disabled={uploading}>
            {uploading
              ? <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
              : <Upload size={15} />}
            {uploading ? 'Загружаем...' : 'Создать тему'}
          </button>
        </div>
      </form>
    </Modal>
  )
}

// ─── Add-files-to-theme modal ────────────────────────────────────────────────
function AddFilesModal({ theme, onClose }) {
  const qc = useQueryClient()
  const [files,     setFiles]     = useState([])
  const [uploading, setUploading] = useState(false)
  const [pct,       setPct]       = useState(0)

  const mutation = useMutation({
    mutationFn: ({ id, files, onProgress }) => addFilesToTheme(id, files, onProgress),
    onSuccess: () => {
      toast.success('Файлы добавлены')
      qc.invalidateQueries({ queryKey: ['documents'] })
      onClose()
    },
    onError: (err) => toast.error(err.response?.data?.error || 'Ошибка загрузки'),
  })

  async function handleSubmit(e) {
    e.preventDefault()
    if (!files.length) return toast.error('Выбери файлы')
    setUploading(true)
    try {
      await addFilesToTheme(theme.id, files, (evt) => {
        if (evt.total) setPct(Math.round((evt.loaded / evt.total) * 100))
      })
      toast.success('Файлы добавлены в тему')
      qc.invalidateQueries({ queryKey: ['documents'] })
      qc.invalidateQueries({ queryKey: ['document-stats'] })
      onClose()
    } catch (err) {
      toast.error(err.response?.data?.error || 'Ошибка загрузки')
    } finally {
      setUploading(false)
    }
  }

  return (
    <Modal open={!!theme} onClose={onClose} title={`Добавить файлы в «${theme?.title}»`} size="md">
      <form onSubmit={handleSubmit} className="space-y-4">
        <FilePicker files={files} onChange={setFiles} label="Новые файлы (PDF, TXT, DOCX)" />

        {uploading && (
          <div className="space-y-1">
            <div className="flex justify-between text-xs text-slate-500">
              <span>Загрузка…</span><span>{pct}%</span>
            </div>
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-200">
              <div className="h-full rounded-full bg-blue-600 transition-all" style={{ width: `${pct}%` }} />
            </div>
          </div>
        )}

        <div className="flex justify-end gap-3 border-t border-slate-200 pt-4">
          <button type="button" className="btn-secondary" onClick={onClose}>Отмена</button>
          <button type="submit" className="btn-primary" disabled={uploading}>
            {uploading
              ? <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
              : <FilePlus size={15} />}
            {uploading ? 'Загружаем...' : 'Добавить файлы'}
          </button>
        </div>
      </form>
    </Modal>
  )
}

// ─── Theme Row ────────────────────────────────────────────────────────────────
function ThemeRow({ theme, onDelete, onAddFiles }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="border border-slate-200 rounded-xl bg-white overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-3">
        <button
          onClick={() => setExpanded((v) => !v)}
          className="text-slate-400 hover:text-slate-600 transition-colors shrink-0"
        >
          {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        </button>

        <FolderOpen size={18} className="text-blue-500 shrink-0" />

        <div className="flex-1 min-w-0">
          <p className="font-semibold text-slate-800 truncate">{theme.title}</p>
          <p className="text-xs text-slate-400">
            {theme.file_count} {pluralFiles(Number(theme.file_count))} · Тема #{theme.theme_order}
          </p>
        </div>

        <div className="flex items-center gap-1 shrink-0">
          <button
            onClick={() => onAddFiles(theme)}
            className="inline-flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs text-blue-600 hover:bg-blue-50 transition-colors"
            title="Добавить файлы в тему"
          >
            <FilePlus size={13} />
            Добавить файлы
          </button>
          <button
            onClick={() => onDelete(theme)}
            className="inline-flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs text-red-600 hover:bg-red-50 transition-colors"
          >
            <Trash2 size={13} />
            Удалить
          </button>
        </div>
      </div>

      {/* Files list */}
      {expanded && (
        <div className="border-t border-slate-100 bg-slate-50 px-4 py-2">
          {theme.files?.length > 0 ? (
            <div className="space-y-1">
              {theme.files.map((f) => (
                <div key={f.file_id} className="flex items-center gap-2 text-sm text-slate-600">
                  <FileText size={13} className="text-slate-400 shrink-0" />
                  <span className="truncate">{f.filename}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-400 py-1">Нет файлов</p>
          )}
        </div>
      )}
    </div>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────
export default function KnowledgeBasePage() {
  const qc = useQueryClient()
  const [createOpen,   setCreateOpen]   = useState(false)
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [addFilesTo,   setAddFilesTo]   = useState(null)

  const { data: themes = [], isLoading, refetch } = useQuery({
    queryKey: ['documents'],
    queryFn: getDocuments,
  })

  const deleteMutation = useMutation({
    mutationFn: (id) => deleteDocument(id),
    onSuccess: () => {
      toast.success('Тема удалена')
      qc.invalidateQueries({ queryKey: ['documents'] })
      qc.invalidateQueries({ queryKey: ['document-stats'] })
      setDeleteTarget(null)
    },
    onError: (err) => toast.error(err.response?.data?.error || 'Ошибка удаления'),
  })

  const totalFiles = themes.reduce((acc, t) => acc + Number(t.file_count), 0)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">База знаний</h1>
          <p className="mt-1 text-sm text-slate-500">
            {themes.length} {pluralThemes(themes.length)} · {totalFiles} {pluralFiles(totalFiles)}
          </p>
        </div>
        <div className="flex gap-2">
          <button className="btn-secondary" onClick={() => refetch()}>
            <RefreshCw size={15} />Обновить
          </button>
          <button className="btn-primary" onClick={() => setCreateOpen(true)}>
            <Upload size={15} />Добавить тему
          </button>
        </div>
      </div>

      {/* Themes list */}
      {isLoading ? (
        <div className="flex items-center justify-center py-16 text-slate-400">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-blue-600 border-t-transparent mr-3" />
          Загрузка…
        </div>
      ) : themes.length === 0 ? (
        <div className="card flex flex-col items-center justify-center py-16 text-center">
          <FolderOpen size={40} className="mb-3 text-slate-300" />
          <p className="font-medium text-slate-500">База знаний пуста</p>
          <p className="text-sm text-slate-400 mt-1">Добавьте первую тему с документами</p>
          <button className="btn-primary mt-4" onClick={() => setCreateOpen(true)}>
            <Upload size={15} />Добавить тему
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {themes.map((theme) => (
            <ThemeRow
              key={theme.id}
              theme={theme}
              onDelete={setDeleteTarget}
              onAddFiles={setAddFilesTo}
            />
          ))}
        </div>
      )}

      <CreateThemeModal open={createOpen} onClose={() => setCreateOpen(false)} />

      {addFilesTo && (
        <AddFilesModal theme={addFilesTo} onClose={() => setAddFilesTo(null)} />
      )}

      <ConfirmDialog
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={() => deleteMutation.mutate(deleteTarget.id)}
        loading={deleteMutation.isPending}
        title="Удалить тему"
        message={`Удалить тему «${deleteTarget?.title}» и все ${deleteTarget?.file_count} файлов? Файлы будут удалены из хранилища.`}
      />
    </div>
  )
}

function pluralThemes(n) {
  if (n % 10 === 1 && n % 100 !== 11) return 'тема'
  if ([2, 3, 4].includes(n % 10) && ![12, 13, 14].includes(n % 100)) return 'темы'
  return 'тем'
}
function pluralFiles(n) {
  if (n % 10 === 1 && n % 100 !== 11) return 'файл'
  if ([2, 3, 4].includes(n % 10) && ![12, 13, 14].includes(n % 100)) return 'файла'
  return 'файлов'
}
