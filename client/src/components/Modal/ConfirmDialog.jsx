import Modal from './Modal.jsx'
import { AlertTriangle } from 'lucide-react'

export default function ConfirmDialog({ open, onClose, onConfirm, title, message, loading }) {
  return (
    <Modal open={open} onClose={onClose} title={title} size="sm">
      <div className="flex flex-col items-center gap-4 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-red-100">
          <AlertTriangle size={22} className="text-red-600" />
        </div>
        <p className="text-sm text-slate-600">{message}</p>
        <div className="flex w-full gap-3">
          <button className="btn-secondary flex-1 justify-center" onClick={onClose}>
            Отмена
          </button>
          <button
            className="btn-danger flex-1 justify-center"
            onClick={onConfirm}
            disabled={loading}
          >
            {loading ? (
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
            ) : null}
            Удалить
          </button>
        </div>
      </div>
    </Modal>
  )
}
