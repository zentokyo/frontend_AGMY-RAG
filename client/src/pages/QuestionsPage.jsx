import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Pencil, Trash2, Search, Filter, ChevronLeft, ChevronRight } from 'lucide-react'
import toast from 'react-hot-toast'
import clsx from 'clsx'
import { getQuestions, createQuestion, updateQuestion, deleteQuestion } from '../api/questions.js'
import DataTable from '../components/Table/DataTable.jsx'
import Modal from '../components/Modal/Modal.jsx'
import ConfirmDialog from '../components/Modal/ConfirmDialog.jsx'
import { formatDate } from '../utils/format.js'

const EMPTY_FORM = {
  question_text: '',
  reference_answer: '',
  category: '',
  tags: '',
  is_active: true,
}

function QuestionForm({ value, onChange, onSubmit, loading, submitLabel }) {
  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <div>
        <label className="label">Вопрос *</label>
        <textarea
          className="input resize-none"
          rows={3}
          placeholder="Введите текст вопроса…"
          value={value.question_text}
          onChange={(e) => onChange({ ...value, question_text: e.target.value })}
          required
        />
      </div>
      <div>
        <label className="label">Эталонный ответ *</label>
        <textarea
          className="input resize-none"
          rows={5}
          placeholder="Введите эталонный ответ…"
          value={value.reference_answer}
          onChange={(e) => onChange({ ...value, reference_answer: e.target.value })}
          required
        />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="label">Категория</label>
          <input
            type="text"
            className="input"
            placeholder="Например: Гражданское право"
            value={value.category}
            onChange={(e) => onChange({ ...value, category: e.target.value })}
          />
        </div>
        <div>
          <label className="label">Теги (через запятую)</label>
          <input
            type="text"
            className="input"
            placeholder="страхование, ОСАГО"
            value={value.tags}
            onChange={(e) => onChange({ ...value, tags: e.target.value })}
          />
        </div>
      </div>
      <div className="flex items-center gap-3">
        <label className="relative inline-flex cursor-pointer items-center">
          <input
            type="checkbox"
            className="sr-only peer"
            checked={value.is_active}
            onChange={(e) => onChange({ ...value, is_active: e.target.checked })}
          />
          <div className="h-5 w-9 rounded-full bg-slate-200 peer-checked:bg-blue-600 peer-focus:ring-2 peer-focus:ring-blue-300 after:absolute after:left-0.5 after:top-0.5 after:h-4 after:w-4 after:rounded-full after:bg-white after:transition-all peer-checked:after:translate-x-4" />
        </label>
        <span className="text-sm text-slate-700">Активен</span>
      </div>
      <div className="flex justify-end gap-3 pt-2 border-t border-slate-200">
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

  const [page,      setPage]      = useState(1)
  const [search,    setSearch]    = useState('')
  const [category,  setCategory]  = useState('')
  const [isActive,  setIsActive]  = useState('')

  const [createOpen,    setCreateOpen]    = useState(false)
  const [editTarget,    setEditTarget]    = useState(null)
  const [deleteTarget,  setDeleteTarget]  = useState(null)
  const [form,          setForm]          = useState(EMPTY_FORM)

  const LIMIT = 20

  const { data, isLoading } = useQuery({
    queryKey: ['questions', { page, search, category, isActive }],
    queryFn: () => getQuestions({ page, limit: LIMIT, search, category, is_active: isActive }),
    keepPreviousData: true,
  })

  const questions   = data?.data        ?? []
  const pagination  = data?.pagination  ?? { total: 0, pages: 1 }

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

  function formToPayload(f) {
    return {
      question_text:    f.question_text.trim(),
      reference_answer: f.reference_answer.trim(),
      category:         f.category.trim() || null,
      tags:             f.tags ? f.tags.split(',').map((t) => t.trim()).filter(Boolean) : [],
      is_active:        f.is_active,
    }
  }

  function openCreate() { setForm(EMPTY_FORM); setCreateOpen(true) }

  function openEdit(row) {
    setForm({
      question_text:    row.question_text,
      reference_answer: row.reference_answer,
      category:         row.category || '',
      tags:             (row.tags || []).join(', '),
      is_active:        row.is_active,
    })
    setEditTarget(row)
  }

  const columns = [
    {
      key: 'question_text',
      header: 'Вопрос',
      render: (v) => (
        <p className="max-w-xs truncate text-sm font-medium text-slate-800" title={v}>{v}</p>
      ),
    },
    {
      key: 'category',
      header: 'Категория',
      render: (v) => v ? (
        <span className="badge bg-slate-100 text-slate-600">{v}</span>
      ) : (
        <span className="text-slate-400 text-xs">—</span>
      ),
    },
    {
      key: 'tags',
      header: 'Теги',
      render: (v) => v?.length ? (
        <div className="flex flex-wrap gap-1">
          {v.slice(0, 3).map((t) => (
            <span key={t} className="badge bg-blue-50 text-blue-600">{t}</span>
          ))}
          {v.length > 3 && <span className="text-xs text-slate-400">+{v.length - 3}</span>}
        </div>
      ) : null,
    },
    {
      key: 'is_active',
      header: 'Статус',
      render: (v) => (
        <span className={clsx('badge', v ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-500')}>
          {v ? 'Активен' : 'Неактивен'}
        </span>
      ),
    },
    {
      key: 'created_at',
      header: 'Создан',
      render: (v) => <span className="text-xs text-slate-400">{formatDate(v)}</span>,
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
      {/* Header */}
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
            placeholder="Поиск по вопросу или ответу…"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1) }}
          />
        </div>
        <div className="relative">
          <Filter size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            className="input pl-9 w-48"
            placeholder="Категория"
            value={category}
            onChange={(e) => { setCategory(e.target.value); setPage(1) }}
          />
        </div>
        <select
          className="input w-36"
          value={isActive}
          onChange={(e) => { setIsActive(e.target.value); setPage(1) }}
        >
          <option value="">Все</option>
          <option value="true">Активные</option>
          <option value="false">Неактивные</option>
        </select>
      </div>

      <DataTable
        columns={columns}
        data={questions}
        loading={isLoading}
        emptyMessage="Вопросы не найдены"
      />

      {/* Pagination */}
      {pagination.pages > 1 && (
        <div className="flex items-center justify-between text-sm text-slate-600">
          <p>
            Страница {page} из {pagination.pages} · {pagination.total} записей
          </p>
          <div className="flex gap-2">
            <button
              className="btn-secondary"
              onClick={() => setPage((p) => Math.max(p - 1, 1))}
              disabled={page === 1}
            >
              <ChevronLeft size={15} />
              Назад
            </button>
            <button
              className="btn-secondary"
              onClick={() => setPage((p) => Math.min(p + 1, pagination.pages))}
              disabled={page === pagination.pages}
            >
              Далее
              <ChevronRight size={15} />
            </button>
          </div>
        </div>
      )}

      {/* Create modal */}
      <Modal open={createOpen} onClose={() => setCreateOpen(false)} title="Новый вопрос" size="lg">
        <QuestionForm
          value={form}
          onChange={setForm}
          onSubmit={(e) => { e.preventDefault(); createMutation.mutate(formToPayload(form)) }}
          loading={createMutation.isPending}
          submitLabel="Создать"
        />
      </Modal>

      {/* Edit modal */}
      <Modal open={!!editTarget} onClose={() => setEditTarget(null)} title="Редактировать вопрос" size="lg">
        <QuestionForm
          value={form}
          onChange={setForm}
          onSubmit={(e) => {
            e.preventDefault()
            updateMutation.mutate({ id: editTarget.id, data: formToPayload(form) })
          }}
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
        message={`Удалить вопрос «${deleteTarget?.question_text?.slice(0, 60)}…»?`}
      />
    </div>
  )
}
