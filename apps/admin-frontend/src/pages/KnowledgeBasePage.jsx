import { useState, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Upload, Trash2, FileText, RefreshCw, UploadCloud,
  ChevronDown, ChevronRight, FolderOpen, FilePlus,
  CheckCircle2, AlertTriangle, Loader2, Clock, Info,
  Pause, Play, XCircle, Activity,
} from 'lucide-react'
import toast from 'react-hot-toast'
import clsx from 'clsx'
import {
  getDocuments,
  uploadDocument,
  deleteDocument,
  addFilesToTheme,
  reindexFile,
  reindexTheme,
  reindexFailedFiles,
  getFileJobs,
  getIngestMetrics,
  pauseFileIngest,
  resumeFileIngest,
  cancelFileIngest,
} from '../api/documents.js'
import ConfirmDialog from '../components/Modal/ConfirmDialog.jsx'
import Modal from '../components/Modal/Modal.jsx'

const ACTIVE_INGEST_STATUSES = new Set(['queued', 'indexing', 'pausing', 'cancelling'])
const ACTIVE_JOB_STATUSES = new Set(['queued', 'running', 'pausing', 'cancelling'])
const PAUSED_JOB_STATUSES = new Set(['paused'])

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
      toast.success(`Тема «${title}» создана, файлы поставлены в очередь`)
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
              <span>Загрузка файлов…</span><span>{pct}%</span>
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

  async function handleSubmit(e) {
    e.preventDefault()
    if (!files.length) return toast.error('Выбери файлы')
    setUploading(true)
    try {
      await addFilesToTheme(theme.id, files, (evt) => {
        if (evt.total) setPct(Math.round((evt.loaded / evt.total) * 100))
      })
      toast.success('Файлы добавлены и поставлены в очередь')
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
              <span>Загрузка файлов…</span><span>{pct}%</span>
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
function ThemeRow({
  theme,
  onDelete,
  onAddFiles,
  onReindexFile,
  onReindexTheme,
  onShowFileJobs,
  onPauseFile,
  onResumeFile,
  onCancelFile,
  reindexingFileId,
  reindexingThemeId,
  ingestActionFileId,
}) {
  const [expanded, setExpanded] = useState(false)
  const hasActiveFiles = theme.files?.some(isIngestBlockedFile)

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
            onClick={() => onReindexTheme(theme)}
            disabled={reindexingThemeId === theme.id || hasActiveFiles}
            className="inline-flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs text-slate-600 hover:bg-slate-50 transition-colors disabled:cursor-not-allowed disabled:opacity-60"
            title="Переиндексировать все файлы темы"
          >
            {reindexingThemeId === theme.id
              ? <Loader2 size={13} className="animate-spin" />
              : <RefreshCw size={13} />}
            Переиндексировать
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
                  <span className="min-w-0 flex-1 truncate">{f.filename}</span>
                  <IngestStatusBadge file={f} />
                  <button
                    onClick={() => onShowFileJobs(theme, f)}
                    className="inline-flex shrink-0 items-center gap-1 rounded-lg px-2 py-1 text-xs text-slate-500 transition-colors hover:bg-white hover:text-slate-700"
                    title="История индексации"
                  >
                    <Info size={12} />
                    Детали
                  </button>
                  {canPauseFile(f) && (
                    <button
                      onClick={() => onPauseFile(theme, f)}
                      disabled={ingestActionFileId === f.file_id}
                      className="inline-flex shrink-0 items-center gap-1 rounded-lg px-2 py-1 text-xs text-slate-500 transition-colors hover:bg-white hover:text-amber-600 disabled:cursor-not-allowed disabled:opacity-60"
                      title="Поставить индексацию на паузу"
                    >
                      {ingestActionFileId === f.file_id ? <Loader2 size={12} className="animate-spin" /> : <Pause size={12} />}
                      Пауза
                    </button>
                  )}
                  {canResumeFile(f) && (
                    <button
                      onClick={() => onResumeFile(theme, f)}
                      disabled={ingestActionFileId === f.file_id}
                      className="inline-flex shrink-0 items-center gap-1 rounded-lg px-2 py-1 text-xs text-slate-500 transition-colors hover:bg-white hover:text-emerald-600 disabled:cursor-not-allowed disabled:opacity-60"
                      title="Возобновить индексацию"
                    >
                      {ingestActionFileId === f.file_id ? <Loader2 size={12} className="animate-spin" /> : <Play size={12} />}
                      Продолжить
                    </button>
                  )}
                  {canCancelFile(f) && (
                    <button
                      onClick={() => onCancelFile(theme, f)}
                      disabled={ingestActionFileId === f.file_id}
                      className="inline-flex shrink-0 items-center gap-1 rounded-lg px-2 py-1 text-xs text-slate-500 transition-colors hover:bg-white hover:text-red-600 disabled:cursor-not-allowed disabled:opacity-60"
                      title="Отменить индексацию"
                    >
                      {ingestActionFileId === f.file_id ? <Loader2 size={12} className="animate-spin" /> : <XCircle size={12} />}
                      Отмена
                    </button>
                  )}
                  <button
                    onClick={() => onReindexFile(theme, f)}
                    disabled={reindexingFileId === f.file_id || isIngestBlockedFile(f)}
                    className="inline-flex shrink-0 items-center gap-1 rounded-lg px-2 py-1 text-xs text-slate-500 transition-colors hover:bg-white hover:text-blue-600 disabled:cursor-not-allowed disabled:opacity-60"
                    title="Переиндексировать файл"
                  >
                    {reindexingFileId === f.file_id
                      ? <Loader2 size={12} className="animate-spin" />
                      : <RefreshCw size={12} />}
                    Переиндексировать
                  </button>
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
  const [jobHistoryTarget, setJobHistoryTarget] = useState(null)
  const [reindexingFileId, setReindexingFileId] = useState(null)
  const [reindexingThemeId, setReindexingThemeId] = useState(null)
  const [ingestActionFileId, setIngestActionFileId] = useState(null)

  const { data: themes = [], isLoading, refetch } = useQuery({
    queryKey: ['documents'],
    queryFn: getDocuments,
    refetchInterval: (query) => hasActiveIngest(query.state.data) ? 3000 : false,
  })

  const hasActiveFiles = hasActiveIngest(themes)
  const { data: ingestMetrics } = useQuery({
    queryKey: ['document-ingest-metrics'],
    queryFn: getIngestMetrics,
    refetchInterval: hasActiveFiles ? 3000 : 10000,
  })

  const { data: fileJobs = [], isLoading: isLoadingFileJobs } = useQuery({
    queryKey: ['document-file-jobs', jobHistoryTarget?.theme.id, jobHistoryTarget?.file.file_id],
    queryFn: () => getFileJobs(jobHistoryTarget.theme.id, jobHistoryTarget.file.file_id),
    enabled: !!jobHistoryTarget,
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

  const reindexMutation = useMutation({
    mutationFn: ({ themeId, fileId }) => reindexFile(themeId, fileId),
    onMutate: ({ fileId }) => setReindexingFileId(fileId),
    onSuccess: () => {
      toast.success('Переиндексация запущена')
      qc.invalidateQueries({ queryKey: ['documents'] })
    },
    onError: (err) => toast.error(err.response?.data?.error || 'Ошибка переиндексации'),
    onSettled: () => setReindexingFileId(null),
  })

  const reindexThemeMutation = useMutation({
    mutationFn: (themeId) => reindexTheme(themeId),
    onMutate: (themeId) => setReindexingThemeId(themeId),
    onSuccess: (data) => {
      toast.success(queueToast('Поставлено в очередь', data))
      qc.invalidateQueries({ queryKey: ['documents'] })
    },
    onError: (err) => toast.error(err.response?.data?.error || 'Ошибка переиндексации темы'),
    onSettled: () => setReindexingThemeId(null),
  })

  const reindexFailedMutation = useMutation({
    mutationFn: reindexFailedFiles,
    onSuccess: (data) => {
      toast.success(queueToast('Ошибочные файлы поставлены в очередь', data))
      qc.invalidateQueries({ queryKey: ['documents'] })
    },
    onError: (err) => toast.error(err.response?.data?.error || 'Ошибка повторной индексации'),
  })

  const pauseMutation = useMutation({
    mutationFn: ({ themeId, fileId }) => pauseFileIngest(themeId, fileId),
    onMutate: ({ fileId }) => setIngestActionFileId(fileId),
    onSuccess: () => {
      toast.success('Индексация поставлена на паузу')
      qc.invalidateQueries({ queryKey: ['documents'] })
      qc.invalidateQueries({ queryKey: ['document-ingest-metrics'] })
    },
    onError: (err) => toast.error(err.response?.data?.error || 'Не удалось поставить на паузу'),
    onSettled: () => setIngestActionFileId(null),
  })

  const resumeMutation = useMutation({
    mutationFn: ({ themeId, fileId }) => resumeFileIngest(themeId, fileId),
    onMutate: ({ fileId }) => setIngestActionFileId(fileId),
    onSuccess: () => {
      toast.success('Индексация возобновлена')
      qc.invalidateQueries({ queryKey: ['documents'] })
      qc.invalidateQueries({ queryKey: ['document-ingest-metrics'] })
    },
    onError: (err) => toast.error(err.response?.data?.error || 'Не удалось возобновить индексацию'),
    onSettled: () => setIngestActionFileId(null),
  })

  const cancelMutation = useMutation({
    mutationFn: ({ themeId, fileId }) => cancelFileIngest(themeId, fileId),
    onMutate: ({ fileId }) => setIngestActionFileId(fileId),
    onSuccess: () => {
      toast.success('Индексация отменена')
      qc.invalidateQueries({ queryKey: ['documents'] })
      qc.invalidateQueries({ queryKey: ['document-ingest-metrics'] })
    },
    onError: (err) => toast.error(err.response?.data?.error || 'Не удалось отменить индексацию'),
    onSettled: () => setIngestActionFileId(null),
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
          <button
            className="btn-secondary"
            onClick={() => reindexFailedMutation.mutate()}
            disabled={reindexFailedMutation.isPending}
          >
            {reindexFailedMutation.isPending
              ? <Loader2 size={15} className="animate-spin" />
              : <AlertTriangle size={15} />}
            Повторить ошибки
          </button>
          <button className="btn-primary" onClick={() => setCreateOpen(true)}>
            <Upload size={15} />Добавить тему
          </button>
        </div>
      </div>

      <IngestMetricsPanel metrics={ingestMetrics} />

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
              onReindexFile={(theme, file) => {
                reindexMutation.mutate({ themeId: theme.id, fileId: file.file_id })
              }}
              onReindexTheme={(theme) => reindexThemeMutation.mutate(theme.id)}
              onShowFileJobs={(theme, file) => setJobHistoryTarget({ theme, file })}
              onPauseFile={(theme, file) => pauseMutation.mutate({ themeId: theme.id, fileId: file.file_id })}
              onResumeFile={(theme, file) => resumeMutation.mutate({ themeId: theme.id, fileId: file.file_id })}
              onCancelFile={(theme, file) => cancelMutation.mutate({ themeId: theme.id, fileId: file.file_id })}
              reindexingFileId={reindexingFileId}
              reindexingThemeId={reindexingThemeId}
              ingestActionFileId={ingestActionFileId}
            />
          ))}
        </div>
      )}

      <CreateThemeModal open={createOpen} onClose={() => setCreateOpen(false)} />

      {addFilesTo && (
        <AddFilesModal theme={addFilesTo} onClose={() => setAddFilesTo(null)} />
      )}

      <JobHistoryModal
        target={jobHistoryTarget}
        jobs={fileJobs}
        loading={isLoadingFileJobs}
        onClose={() => setJobHistoryTarget(null)}
      />

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

function IngestMetricsPanel({ metrics }) {
  const stageTimings = metrics?.performance?.avg_stage_seconds || {}
  return (
    <div className="rounded-xl border border-slate-200 bg-white px-4 py-3">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-800">
          <Activity size={16} className="text-blue-500" />
          Ingest worker
        </div>
        <div className="text-xs text-slate-400">
          concurrency {metrics?.worker?.index_concurrency || '—'} · max attempts {metrics?.worker?.max_attempts || '—'}
        </div>
      </div>
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
        <MetricTile label="Очередь" value={metrics?.queue?.depth ?? '—'} hint={formatSeconds(metrics?.queue?.oldest_queued_age_seconds)} />
        <MetricTile label="В работе" value={metrics?.queue?.running ?? '—'} hint={`pause ${metrics?.queue?.pausing || 0} · cancel ${metrics?.queue?.cancelling || 0}`} />
        <MetricTile label="Пауза" value={metrics?.queue?.paused ?? '—'} hint="ожидает resume" />
        <MetricTile label="Ошибки" value={metrics?.failures?.failed ?? '—'} hint={`dead ${metrics?.failures?.dead_letter || 0}`} />
        <MetricTile label="Среднее" value={formatSeconds(metrics?.performance?.avg_total_seconds)} hint="полный job" />
      </div>
      {Object.keys(stageTimings).length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-500">
          <StageTiming label="read" value={stageTimings.reading_seconds} />
          <StageTiming label="extract" value={stageTimings.extracting_seconds} />
          <StageTiming label="chunk" value={stageTimings.chunking_seconds} />
          <StageTiming label="delete" value={stageTimings.qdrant_delete_seconds} />
          <StageTiming label="embed+upsert" value={stageTimings.embedding_qdrant_upsert_seconds} />
        </div>
      )}
    </div>
  )
}

function MetricTile({ label, value, hint }) {
  return (
    <div className="rounded-lg bg-slate-50 px-3 py-2">
      <div className="text-[11px] uppercase tracking-wide text-slate-400">{label}</div>
      <div className="mt-0.5 text-lg font-semibold text-slate-800">{value}</div>
      <div className="truncate text-xs text-slate-400">{hint || '—'}</div>
    </div>
  )
}

function StageTiming({ label, value }) {
  return (
    <span className="rounded-full bg-slate-100 px-2 py-0.5">
      {label}: {formatSeconds(value)}
    </span>
  )
}

function JobHistoryModal({ target, jobs, loading, onClose }) {
  return (
    <Modal
      open={!!target}
      onClose={onClose}
      title={target ? `Индексация: ${target.file.filename}` : 'История индексации'}
      size="xl"
    >
      {loading ? (
        <div className="flex items-center justify-center py-10 text-sm text-slate-400">
          <Loader2 size={18} className="mr-2 animate-spin" />
          Загружаем историю…
        </div>
      ) : jobs.length === 0 ? (
        <p className="text-sm text-slate-500">Для этого файла ещё нет job-истории.</p>
      ) : (
        <div className="max-h-[70vh] space-y-3 overflow-y-auto pr-1">
          {jobs.map((job) => (
            <div key={job.job_id} className="rounded-lg border border-slate-200 bg-white p-3">
              <div className="flex flex-wrap items-center gap-2">
                <span className={clsx(
                  'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium',
                  jobStatusClass(job.status),
                )}>
                  {jobStatusLabel(job.status)}
                </span>
                <span className="text-xs text-slate-500">{ingestStageLabel(job.stage)}</span>
                <span className="text-xs text-slate-400">Попытка #{job.attempt || 1}</span>
                <span className="ml-auto text-xs text-slate-400">{formatDateTime(job.created_at)}</span>
              </div>

              {job.error && (
                <p className="mt-2 rounded-md bg-red-50 px-2 py-1.5 text-xs text-red-700">
                  {job.error}
                </p>
              )}

              <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-slate-500 sm:grid-cols-4">
                <JobMetric label="Прогресс" value={`${Number(job.progress_percent || 0)}%`} />
                <JobMetric label="Старт" value={formatDateTime(job.started_at)} />
                <JobMetric label="Финиш" value={formatDateTime(job.finished_at)} />
                <JobMetric label="Обновлено" value={formatDateTime(job.updated_at)} />
              </div>

              {job.result && (
                <>
                  <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-slate-500 sm:grid-cols-4">
                    <JobMetric label="Страниц" value={job.result.pages || '—'} />
                    <JobMetric label="Чанков" value={job.result.chunks_written || job.result.chunks || '—'} />
                    <JobMetric label="Секций" value={job.result.sections || '—'} />
                    <JobMetric label="OCR" value={job.result.ocr_pages || 0} />
                  </div>
                  {job.result.timings && (
                    <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-slate-500 sm:grid-cols-5">
                      <JobMetric label="Reading" value={formatSeconds(job.result.timings.reading_seconds)} />
                      <JobMetric label="Extract" value={formatSeconds(job.result.timings.extracting_seconds)} />
                      <JobMetric label="Chunking" value={formatSeconds(job.result.timings.chunking_seconds)} />
                      <JobMetric label="Delete" value={formatSeconds(job.result.timings.qdrant_delete_seconds)} />
                      <JobMetric label="Embed+upsert" value={formatSeconds(job.result.timings.embedding_qdrant_upsert_seconds)} />
                    </div>
                  )}
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </Modal>
  )
}

function JobMetric({ label, value }) {
  return (
    <div className="rounded-md bg-slate-50 px-2 py-1.5">
      <div className="text-[11px] uppercase tracking-wide text-slate-400">{label}</div>
      <div className="mt-0.5 truncate text-slate-700">{value || '—'}</div>
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

function hasActiveIngest(themes = []) {
  return themes.some((theme) =>
    theme.files?.some(isActiveIngestFile)
  )
}

function isActiveIngestFile(file) {
  return ACTIVE_INGEST_STATUSES.has(file.ingest_status) || ACTIVE_JOB_STATUSES.has(file.latest_job?.status)
}

function isPausedIngestFile(file) {
  return file.ingest_status === 'paused' || PAUSED_JOB_STATUSES.has(file.latest_job?.status)
}

function isIngestBlockedFile(file) {
  return isActiveIngestFile(file) || isPausedIngestFile(file)
}

function canPauseFile(file) {
  return ['queued', 'running'].includes(file.latest_job?.status) || ['queued', 'indexing'].includes(file.ingest_status)
}

function canResumeFile(file) {
  return isPausedIngestFile(file)
}

function canCancelFile(file) {
  return ['queued', 'running', 'pausing', 'paused'].includes(file.latest_job?.status)
    || ['queued', 'indexing', 'pausing', 'paused'].includes(file.ingest_status)
}

function queueToast(prefix, data) {
  const deadLettered = Number(data.dead_lettered || 0)
  return deadLettered > 0
    ? `${prefix}: ${data.queued}; в dead letter: ${deadLettered}`
    : `${prefix}: ${data.queued}`
}

function IngestStatusBadge({ file }) {
  const status = file.ingest_status || 'uploaded'
  const job = file.latest_job
  const chunks = Number(file.indexed_chunks || 0)
  const progress = Number(job?.progress_percent || 0)
  const stage = job?.stage ? ingestStageLabel(job.stage) : null
  const config = {
    indexed: {
      icon: CheckCircle2,
      label: chunks > 0 ? `Индекс: ${chunks}` : 'Индексировано',
      className: 'bg-emerald-50 text-emerald-700',
    },
    indexing: {
      icon: Loader2,
      label: stage ? `${stage} ${progress}%` : 'Индексация',
      className: 'bg-blue-50 text-blue-700',
      spin: true,
    },
    queued: {
      icon: Clock,
      label: stage && stage !== 'queued' ? `${stage} ${progress}%` : 'В очереди',
      className: 'bg-amber-50 text-amber-700',
    },
    failed: {
      icon: AlertTriangle,
      label: 'Ошибка индекса',
      className: 'bg-red-50 text-red-700',
    },
    pausing: {
      icon: Loader2,
      label: 'Ставим на паузу',
      className: 'bg-amber-50 text-amber-700',
      spin: true,
    },
    paused: {
      icon: Pause,
      label: 'Пауза',
      className: 'bg-amber-50 text-amber-700',
    },
    cancelling: {
      icon: Loader2,
      label: 'Отмена',
      className: 'bg-red-50 text-red-700',
      spin: true,
    },
    cancelled: {
      icon: XCircle,
      label: 'Отменено',
      className: 'bg-slate-100 text-slate-600',
    },
    dead_letter: {
      icon: AlertTriangle,
      label: 'Dead letter',
      className: 'bg-red-100 text-red-800',
    },
    uploaded: {
      icon: Clock,
      label: 'Ожидает индекса',
      className: 'bg-slate-100 text-slate-600',
    },
  }[status] || {
    icon: Clock,
    label: status,
    className: 'bg-slate-100 text-slate-600',
  }
  const Icon = config.icon

  return (
    <span
      className={clsx(
        'ml-auto inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-0.5 text-xs',
        config.className,
      )}
      title={file.ingest_error || job?.error || ingestJobTitle(job) || config.label}
    >
      <Icon size={12} className={config.spin ? 'animate-spin' : undefined} />
      {config.label}
    </span>
  )
}

function ingestStageLabel(stage) {
  return {
    queued: 'В очереди',
    starting: 'Старт',
    reading: 'Чтение',
    extracting: 'Извлечение',
    chunking: 'Чанкинг',
    embedding: 'Эмбеддинги',
    qdrant_upsert: 'Qdrant',
    done: 'Готово',
    failed: 'Ошибка',
    claimed: 'В работе',
    pausing: 'Пауза…',
    paused: 'Пауза',
    cancelling: 'Отмена…',
    cancelled: 'Отменено',
    dead_letter: 'Dead letter',
  }[stage] || stage
}

function ingestJobTitle(job) {
  if (!job) return ''
  const result = job.result || {}
  const chunks = result.chunks_written || result.chunks
  const pages = result.pages ? `${result.pages} стр.` : null
  const ocr = result.ocr_pages ? `OCR: ${result.ocr_pages}` : null
  return [ingestStageLabel(job.stage), chunks ? `${chunks} чанков` : null, pages, ocr]
    .filter(Boolean)
    .join(' · ')
}

function jobStatusLabel(status) {
  return {
    queued: 'В очереди',
    running: 'В работе',
    succeeded: 'Успешно',
    failed: 'Ошибка',
    pausing: 'Пауза…',
    paused: 'Пауза',
    cancelling: 'Отмена…',
    cancelled: 'Отменено',
    dead_letter: 'Dead letter',
  }[status] || status
}

function jobStatusClass(status) {
  return {
    queued: 'bg-amber-50 text-amber-700',
    running: 'bg-blue-50 text-blue-700',
    succeeded: 'bg-emerald-50 text-emerald-700',
    failed: 'bg-red-50 text-red-700',
    pausing: 'bg-amber-50 text-amber-700',
    paused: 'bg-amber-50 text-amber-700',
    cancelling: 'bg-red-50 text-red-700',
    cancelled: 'bg-slate-100 text-slate-600',
    dead_letter: 'bg-red-100 text-red-800',
  }[status] || 'bg-slate-100 text-slate-600'
}

function formatSeconds(value) {
  if (value === null || value === undefined || value === '—') return '—'
  const seconds = Number(value)
  if (!Number.isFinite(seconds)) return '—'
  if (seconds < 60) return `${seconds.toFixed(seconds < 10 ? 1 : 0)}s`
  return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`
}

function formatDateTime(value) {
  if (!value) return '—'
  return new Date(value).toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}
