import { useState, useRef, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Upload, Trash2, FileText, RefreshCw, UploadCloud } from 'lucide-react'
import toast from 'react-hot-toast'
import clsx from 'clsx'
import { getDocuments, uploadDocument, deleteDocument } from '../api/documents.js'
import DataTable from '../components/Table/DataTable.jsx'
import ConfirmDialog from '../components/Modal/ConfirmDialog.jsx'
import { formatBytes, formatDate } from '../utils/format.js'

function StatusBadge({ status }) {
  const map = {
    processing: { cls: 'bg-amber-100 text-amber-700', label: 'Обработка' },
    indexed:    { cls: 'bg-green-100 text-green-700',  label: 'Проиндексирован' },
    error:      { cls: 'bg-red-100  text-red-700',     label: 'Ошибка' },
  }
  const { cls, label } = map[status] || { cls: 'bg-slate-100 text-slate-600', label: status }
  return <span className={`badge ${cls}`}>{label}</span>
}

export default function KnowledgeBasePage() {
  const qc = useQueryClient()
  const fileRef = useRef(null)

  const [deleteTarget, setDeleteTarget] = useState(null)
  const [dragging,     setDragging]     = useState(false)
  const [uploading,    setUploading]    = useState(false)
  const [uploadPct,    setUploadPct]    = useState(0)

  const { data: documents = [], isLoading, refetch } = useQuery({
    queryKey: ['documents'],
    queryFn: getDocuments,
    refetchInterval: (data) =>
      (data ?? []).some((d) => d.status === 'processing') ? 5000 : false,
  })

  const deleteMutation = useMutation({
    mutationFn: (id) => deleteDocument(id),
    onSuccess: () => {
      toast.success('Документ удалён')
      qc.invalidateQueries({ queryKey: ['documents'] })
      qc.invalidateQueries({ queryKey: ['document-stats'] })
      setDeleteTarget(null)
    },
    onError: (err) => toast.error(err.response?.data?.error || 'Ошибка удаления'),
  })

  async function handleUpload(files) {
    if (!files?.length) return
    const file = files[0]

    setUploading(true)
    setUploadPct(0)
    try {
      await uploadDocument(file, (evt) => {
        if (evt.total) setUploadPct(Math.round((evt.loaded / evt.total) * 100))
      })
      toast.success(`«${file.name}» загружен. Идёт индексация…`)
      qc.invalidateQueries({ queryKey: ['documents'] })
      qc.invalidateQueries({ queryKey: ['document-stats'] })
    } catch (err) {
      toast.error(err.response?.data?.error || 'Ошибка загрузки')
    } finally {
      setUploading(false)
      setUploadPct(0)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  const onDrop = useCallback((e) => {
    e.preventDefault()
    setDragging(false)
    handleUpload(e.dataTransfer.files)
  }, [])

  const columns = [
    {
      key: 'original_name',
      header: 'Файл',
      render: (v) => (
        <div className="flex items-center gap-2">
          <FileText size={16} className="shrink-0 text-slate-400" />
          <span className="max-w-xs truncate font-medium">{v}</span>
        </div>
      ),
    },
    {
      key: 'file_size',
      header: 'Размер',
      render: (v) => formatBytes(v),
    },
    {
      key: 'uploaded_at',
      header: 'Дата загрузки',
      render: (v) => formatDate(v),
    },
    {
      key: 'status',
      header: 'Статус',
      render: (v) => <StatusBadge status={v} />,
    },
    {
      key: 'actions',
      header: '',
      cellClassName: 'text-right',
      render: (_, row) => (
        <button
          className="inline-flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs text-red-600 hover:bg-red-50 transition-colors"
          onClick={() => setDeleteTarget(row)}
        >
          <Trash2 size={14} />
          Удалить
        </button>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">База знаний</h1>
          <p className="mt-1 text-sm text-slate-500">
            {documents.length} {pluralDocs(documents.length)} · PDF, TXT, DOCX
          </p>
        </div>
        <div className="flex gap-2">
          <button className="btn-secondary" onClick={() => refetch()}>
            <RefreshCw size={15} />
            Обновить
          </button>
          <button
            className="btn-primary"
            onClick={() => fileRef.current?.click()}
            disabled={uploading}
          >
            <Upload size={15} />
            Загрузить файл
          </button>
        </div>
      </div>

      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => !uploading && fileRef.current?.click()}
        className={clsx(
          'cursor-pointer rounded-xl border-2 border-dashed px-6 py-10 text-center transition-colors',
          dragging
            ? 'border-blue-500 bg-blue-50'
            : 'border-slate-300 bg-white hover:border-blue-400 hover:bg-slate-50',
          uploading && 'pointer-events-none opacity-70'
        )}
      >
        <input
          ref={fileRef}
          type="file"
          accept=".pdf,.txt,.docx"
          className="hidden"
          onChange={(e) => handleUpload(e.target.files)}
        />
        <UploadCloud
          size={36}
          className={clsx('mx-auto mb-3', dragging ? 'text-blue-500' : 'text-slate-400')}
        />
        {uploading ? (
          <div className="space-y-2">
            <p className="text-sm font-medium text-blue-600">Загрузка… {uploadPct}%</p>
            <div className="mx-auto h-1.5 w-48 overflow-hidden rounded-full bg-slate-200">
              <div
                className="h-full rounded-full bg-blue-600 transition-all"
                style={{ width: `${uploadPct}%` }}
              />
            </div>
          </div>
        ) : (
          <>
            <p className="text-sm font-medium text-slate-700">
              Перетащите файл сюда или нажмите для выбора
            </p>
            <p className="mt-1 text-xs text-slate-400">PDF, TXT, DOCX · до 50 МБ</p>
          </>
        )}
      </div>

      <DataTable
        columns={columns}
        data={documents}
        loading={isLoading}
        emptyMessage="Документы не загружены"
      />

      <ConfirmDialog
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={() => deleteMutation.mutate(deleteTarget.id)}
        loading={deleteMutation.isPending}
        title="Удалить документ"
        message={`Вы уверены, что хотите удалить «${deleteTarget?.original_name}»? Чанки будут удалены из ChromaDB.`}
      />
    </div>
  )
}

function pluralDocs(n) {
  if (n % 10 === 1 && n % 100 !== 11) return 'документ'
  if ([2, 3, 4].includes(n % 10) && ![12, 13, 14].includes(n % 100)) return 'документа'
  return 'документов'
}
