import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Pencil, Trash2, Search, ChevronLeft, ChevronRight } from 'lucide-react'
import toast from 'react-hot-toast'
import { getQuestions, getThemes, createQuestion, updateQuestion, deleteQuestion } from '../api/questions.js'
import DataTable from '../components/Table/DataTable.jsx'
import Modal from '../components/Modal/Modal.jsx'
import ConfirmDialog from '../components/Modal/ConfirmDialog.jsx'

const EMPTY_FORM = { text: '', answer_text: '', theme_id: '' }

function QuestionForm({ value, onChange, onSubmit, loading, submitLabel, themes }) {
  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <div>
        <label className="label">Тема *</label>
        <select
          className="input"
          value={value.theme_id}
          onChange={(e) => onChange({ ...value, theme_id: e.target.value })}
          required
        >
          <option value="">Выберите тему…</option>
          {themes.map((t) => (
            <option key={t.id} value={t.id}>{t.title}</option>
          ))}
        </select>
      </div>

      <div>
        <label className="label">Текст вопроса *</label>
        <textarea
          className="input resize-none"
          rows={3}
          placeholder="Введите текст вопроса…"
          value={value.text}
          onChange={(e) => onChange({ ...value, text: e.target.value })}
          required
        />
      </div>

      <div>
        <label className="label">Эталонный ответ *</label>
        <textarea
          className="input resize-none"
          rows={5}
          placeholder="Введите эталонный ответ…"
          value={value.answer_text}
          onChange={(e) => onChange({ ...value, answer_text: e.target.value })}
          required
        />
      </div>

      <div className="flex justify-end gap-3 border-t border-slate-200 pt-4">
        <button type="submit" className="btn-primary" disabled={loading}>
          {loading && (
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
          )}
          {submitLabel}
        </button>
      </div>
    </form>
  )
}

export default function QuestionsPage() {
  const qc = useQueryClient()

  const [page,         setPage]         = useState(1)
  const [search,       setSearch]       = useState('')
  const [themeFilter,  setThemeFilter]  = useState('')
  const [createOpen,   setCreateOpen]   = useState(false)
  const [editTarget,   setEditTarget]   = useState(null)
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [form,         setForm]         = useState(EMPTY_FORM)

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

  function openCreate() { setForm(EMPTY_FORM); setCreateOpen(true) }

  function openEdit(row) {
    setForm({ text: row.text, answer_text: row.answer_text, theme_id: row.theme_id })
    setEditTarget(row)
  }

  const columns = [
    {
      key: 'text',
      header: 'Вопрос',
      render: (v) => (
        <p className="max-w-xs truncate text-sm font-medium text-slate-800" title={v}>{v}</p>
      ),
    },
    {
      key: 'answer_text',
      header: 'Ответ',
      render: (v) => (
        <p className="max-w-xs truncate text-sm text-slate-600" title={v}>{v}</p>
      ),
    },
    {
      key: 'theme_title',
      header: 'Тема',
      render: (v) => (
        <span className="badge bg-blue-50 text-blue-700">{v}</span>
      ),
    },
    {
      key: 'actions',
      header: '',
      cellClassName: 'text-right whitespace-nowrap',
      render: (_, row) => (
        <div className="flex items-center justify-end gap-1">
          <button
            className="inline-flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs text-blue-600 hover:bg-blue-50 transition-colors"
            onClick={() => openEdit(row)}
          >
            <Pencil size={13} />
            Изменить
          </button>
          <button
            className="inline-flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs text-red-600 hover:bg-red-50 transition-colors"
            onClick={() => setDeleteTarget(row)}
          >
            <Trash2 size={13} />
            Удалить
          </button>
        </div>
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
          <Plus size={16} />
          Добавить вопрос
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div className="relative">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            className="input pl-9 w-64"
            placeholder="Поиск по тексту…"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1) }}
          />
        </div>
        <select
          className="input w-52"
          value={themeFilter}
          onChange={(e) => { setThemeFilter(e.target.value); setPage(1) }}
        >
          <option value="">Все темы</option>
          {themesData.map((t) => (
            <option key={t.id} value={t.id}>{t.title}</option>
          ))}
        </select>
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

      {/* Create */}
      <Modal open={createOpen} onClose={() => setCreateOpen(false)} title="Новый вопрос" size="lg">
        <QuestionForm
          value={form}
          onChange={setForm}
          themes={themesData}
          onSubmit={(e) => { e.preventDefault(); createMutation.mutate(form) }}
          loading={createMutation.isPending}
          submitLabel="Создать"
        />
      </Modal>

      {/* Edit */}
      <Modal open={!!editTarget} onClose={() => setEditTarget(null)} title="Редактировать вопрос" size="lg">
        <QuestionForm
          value={form}
          onChange={setForm}
          themes={themesData}
          onSubmit={(e) => { e.preventDefault(); updateMutation.mutate({ id: editTarget.id, data: form }) }}
          loading={updateMutation.isPending}
          submitLabel="Сохранить"
        />
      </Modal>

      {/* Delete confirm */}
      <ConfirmDialog
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={() => deleteMutation.mutate(deleteTarget.id)}
        loading={deleteMutation.isPending}
        title="Удалить вопрос"
        message={`Удалить вопрос «${deleteTarget?.text?.slice(0, 60)}»?`}
      />
    </div>
  )
}
