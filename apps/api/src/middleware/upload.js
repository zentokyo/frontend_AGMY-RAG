import multer from 'multer'
import { extname } from 'path'

const ALLOWED_MIMES = [
  'application/pdf',
  'text/plain',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
]
const ALLOWED_EXTS  = ['.pdf', '.txt', '.docx']
const MAX_SIZE_BYTES = 50 * 1024 * 1024 // 50 MB

// Use memory storage — files go straight to MinIO, not disk
const storage = multer.memoryStorage()

function fileFilter(_req, file, cb) {
  const ext = extname(file.originalname).toLowerCase()
  if (ALLOWED_MIMES.includes(file.mimetype) && ALLOWED_EXTS.includes(ext)) {
    cb(null, true)
  } else {
    cb(new Error(`Unsupported file type. Allowed: ${ALLOWED_EXTS.join(', ')}`))
  }
}

export const upload = multer({
  storage,
  fileFilter,
  limits: { fileSize: MAX_SIZE_BYTES },
})
