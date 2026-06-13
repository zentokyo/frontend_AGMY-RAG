import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Plus, Pencil, Trash2, Search, ChevronLeft, ChevronRight,
  ChevronDown, Eye, BookOpen, Tag, AlertTriangle,
} from 'lucide-react'
import toast from 'react-hot-toast'
import clsx from 'clsx'
import { getQuestions, getThemes, createQuestion, updateQuestion, deleteQuestion } from '../api/questions.js'
import DataTable from '../components/Table/DataTable.jsx'
import Modal from '../components/Modal/Modal.jsx'
import ConfirmDialog from '../components/Modal/ConfirmDialog.jsx'

const EMPTY_FORM = { text: '', answer_text: '', theme_id: '' }

function ThemeSelect({ value, onChange, themes, placeholder = 'Выберите тему…', className = '', required = false }) {
  return (
    <div className={clsx('relative', className)}>
      <select
        className="select-input"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required={required}
      >
        <option value="">{placeholder}</option>
        {themes.map((t) => (
          <option key={t.id} value={t.id}>{t.title}</option>
        ))}
      </select>
      <ChevronDown
        size={16}
        className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-slate-400"
      />
    </div>
  )
}

// ─── Question form (create / edit) ──────────────────────────────────────────
function QuestionForm({ value, onChange, onSubmit, loading, submitLabel, themes }) {
  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <div>
        <label className="label">Тема *</label>
        <ThemeSelect
          value={value.theme_id}
          onChange={(themeId) => onChange({ ...value, theme_id: themeId })}
          themes={themes}
          required
        />
      </div>
      <div>
        <label className="label">Текст вопроса *</label>
        <textarea
          className="input resize-none" rows={3}
          placeholder="Введите текст вопроса…"
          value={value.text}
          onChange={(e) => onChange({ ...value, text: e.target.value })}
          required
        />
      </div>
      <div>
        <label className="label">Эталонный ответ *</label>
        <textarea
          className="input resize-none" rows={5}
          placeholder="Введите эталонный ответ…"
          value={value.answer_text}
          onChange={(e) => onChange({ ...value, answer_text: e.target.value })}
          required
        />
      </div>
      <div className="flex justify-end gap-3 border-t border-slate-200 pt-4">
        <button type="submit" className="btn-primary" disabled={loading}>
          {loading && <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />}
          {submitLabel}
        </button>
      </div>
    </form>
  )
}

// ─── View modal (read-only) ──────────────────────────────────────────────────
function ViewModal({ question, onClose, onEdit, onDelete }) {
  if (!question) return null
  return (
    <Modal open={!!question} onClose={onClose} title="Просмотр вопроса" size="lg">
      <div className="space-y-4">
        {/* Theme badge */}
        <div className="flex items-center gap-2">
          <Tag size={14} className="text-slate-400" />
          <span className="badge bg-blue-50 text-blue-700">{question.theme_title}</span>
        </div>

        {/* Question */}
        <div>
          <p className="label flex items-center gap-1.5">
            <BookOpen size={13} />Вопрос
          </p>
          <div className="rounded-lg bg-slate-50 border border-slate-200 px-4 py-3 text-sm text-slate-800 whitespace-pre-wrap">
            {question.text}
          </div>
        </div>

        {/* Answer */}
        <div>
          <p className="label flex items-center gap-1.5">
            <BookOpen size={13} />Эталонный ответ
          </p>
          <div className="rounded-lg bg-green-50 border border-green-200 px-4 py-3 text-sm text-slate-800 whitespace-pre-wrap">
            {question.answer_text}
          </div>
        </div>

        {/* Actions */}
        <div className="flex justify-between items-center border-t border-slate-200 pt-4">
          <button
            className="btn-danger"
            onClick={() => { onClose(); onDelete(question) }}
          >
            <Trash2 size={14} />Удалить
          </button>
          <button
            className="btn-primary"
            onClick={() => { onClose(); onEdit(question) }}
          >
            <Pencil size={14} />Редактировать
          </button>
        </div>
      </div>
    </Modal>
  )
}

// ─── Edit confirm dialog ─────────────────────────────────────────────────────
function EditConfirmDialog({ open, onClose, onConfirm }) {
  return (
    <Modal open={open} onClose={onClose} title="Подтвердить редактирование" size="sm">
      <div className="flex flex-col items-center gap-4 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-amber-100">
          <AlertTriangle size={22} className="text-amber-600" />
        </div>
        <p className="text-sm text-slate-600">
          Вы хотите изменить этот вопрос? Это действие обновит запись в базе данных.
        </p>
        <div className="flex w-full gap-3">
          <button className="btn-secondary flex-1 justify-center" onClick={onClose}>Отмена</button>
          <button className="btn-primary flex-1 justify-center" onClick={onConfirm}>
            <Pencil size={14} />Продолжить
          </button>
        </div>
      </div>
    </Modal>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────
export default function QuestionsPage() {
  const qc = useQueryClient()

  const [page,         setPage]         = useState(1)
  const [search,       setSearch]       = useState('')
  const [themeFilter,  setThemeFilter]  = useState('')

  // Modal states
  const [viewQuestion,    setViewQuestion]    = useState(null) // view modal
  const [createOpen,      setCreateOpen]      = useState(false)
  const [editTarget,      setEditTarget]      = useState(null) // edit modal
  const [editConfirm,     setEditConfirm]     = useState(null) // pending question for confirm dialog
  const [deleteTarget,    setDeleteTarget]    = useState(null)
  const [form,            setForm]            = useState(EMPTY_FORM)

  const LIMIT = 20

  const { data: themesData = [] } = useQuery({
    queryKey: ['themes'],
    queryFn: getThemes,
  })

  const { data, isLoading } = useQuery({
    queryKey: ['questions', { page, search, theme_id: themeFilter }],
    queryFn: () => getQuestions({ page, limit: LIMIT, search, theme_id: themeFilter }),
    placeholderData: (prev) => prev,
  })

  const questions  = data?.data        ?? []
  const pagination = data?.pagination  ?? { total: 0, pages: 1 }

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['questions'] })
    qc.invalidateQueries({ queryKey: ['question-stats'] })
  }

  const createMutation = useMutation({
    mutationFn: (d) => createQuestion(d),
    onSuccess: () => { toast.success('Вопрос создан'); invalidate(); setCreateOpen(false) },
    onError:   (e) => toast.error(e.response?.data?.error || 'Ошибка создания'),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }) => updateQuestion(id, data),
    onSuccess: () => { toast.success('Вопрос обновлён'); invalidate(); setEditTarget(null) },
    onError:   (e) => toast.error(e.response?.data?.error || 'Ошибка сохранения'),
  })

  const deleteMutation = useMutation({
    mutationFn: (id) => deleteQuestion(id),
    onSuccess: () => { toast.success('Вопрос удалён'); invalidate(); setDeleteTarget(null) },
    onError:   (e) => toast.error(e.response?.data?.error || 'Ошибка удаления'),
  })

  function openCreate() {
    setForm(EMPTY_FORM)
    setCreateOpen(true)
  }

  // "View" → user clicks "Редактировать" → confirm dialog → edit modal
  function handleViewEdit(row) {
    setForm({ text: row.text, answer_text: row.answer_text, theme_id: row.theme_id })
    setEditConfirm(row)
  }

  function confirmEdit() {
    setEditTarget(editConfirm)
    setEditConfirm(null)
  }

  const columns = [
    {
      key: 'text',
      header: 'Вопрос',
      render: (v) => (
        <p className="max-w-sm truncate text-sm font-medium text-slate-800" title={v}>{v}</p>
      ),
    },
    {
      key: 'answer_text',
      header: 'Ответ',
      render: (v) => (
        <p className="max-w-xs truncate text-sm text-slate-500" title={v}>{v}</p>
      ),
    },
    {
      key: 'theme_title',
      header: 'Тема',
      render: (v) => <span className="badge bg-blue-50 text-blue-700">{v}</span>,
    },
    {
      key: 'actions',
      header: '',
      cellClassName: 'text-right whitespace-nowrap',
      render: (_, row) => (
        <button
          className="inline-flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs text-slate-600 hover:bg-slate-100 transition-colors"
          onClick={() => setViewQuestion(row)}
        >
          <Eye size={13} />
          Просмотр
        </button>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900">База вопросов</h1>
          <p className="mt-1 text-sm text-slate-500">{pagination.total} вопросов</p>
        </div>
        <button className="btn-primary" onClick={openCreate}>
          <Plus size={16} />Добавить вопрос
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div className="relative">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text" className="input pl-9 w-64"
            placeholder="Поиск по тексту…"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1) }}
          />
        </div>
        <ThemeSelect
          className="w-64"
          value={themeFilter}
          onChange={(themeId) => { setThemeFilter(themeId); setPage(1) }}
          themes={themesData}
          placeholder="Все темы"
        />
      </div>

      <DataTable
        columns={columns}
        data={questions}
        loading={isLoading}
        emptyMessage="Вопросы не найдены"
      />

      {pagination.pages > 1 && (
        <div className="flex items-center justify-between text-sm text-slate-600">
          <p>Страница {page} из {pagination.pages} · {pagination.total} записей</p>
          <div className="flex gap-2">
            <button className="btn-secondary" onClick={() => setPage((p) => Math.max(p - 1, 1))} disabled={page === 1}>
              <ChevronLeft size={15} />Назад
            </button>
            <button className="btn-secondary" onClick={() => setPage((p) => Math.min(p + 1, pagination.pages))} disabled={page === pagination.pages}>
              Далее<ChevronRight size={15} />
            </button>
          </div>
        </div>
      )}

      {/* View modal */}
      <ViewModal
        question={viewQuestion}
        onClose={() => setViewQuestion(null)}
        onEdit={handleViewEdit}
        onDelete={(row) => setDeleteTarget(row)}
      />

      {/* Edit confirmation */}
      <EditConfirmDialog
        open={!!editConfirm}
        onClose={() => setEditConfirm(null)}
        onConfirm={confirmEdit}
      />

      {/* Create modal */}
      <Modal open={createOpen} onClose={() => setCreateOpen(false)} title="Новый вопрос" size="lg">
        <QuestionForm
          value={form} onChange={setForm} themes={themesData}
          onSubmit={(e) => { e.preventDefault(); createMutation.mutate(form) }}
          loading={createMutation.isPending}
          submitLabel="Создать"
        />
      </Modal>

      {/* Edit modal */}
      <Modal open={!!editTarget} onClose={() => setEditTarget(null)} title="Редактировать вопрос" size="lg">
        <QuestionForm
          value={form} onChange={setForm} themes={themesData}
          onSubmit={(e) => { e.preventDefault(); updateMutation.mutate({ id: editTarget.id, data: form }) }}
          loading={updateMutation.isPending}
          submitLabel="Сохранить изменения"
        />
      </Modal>

      {/* Delete confirm */}
      <ConfirmDialog
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={() => deleteMutation.mutate(deleteTarget.id)}
        loading={deleteMutation.isPending}
        title="Удалить вопрос"
        message={`Удалить вопрос «${deleteTarget?.text?.slice(0, 60)}»? Это действие необратимо.`}
      />
    </div>
  )
}
