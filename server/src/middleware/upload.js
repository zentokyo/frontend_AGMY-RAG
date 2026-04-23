import multer from 'multer'
import { extname, join, dirname } from 'path'
import { fileURLToPath } from 'url'
import { existsSync, mkdirSync } from 'fs'
import { v4 as uuidv4 } from 'uuid'

const __dirname = dirname(fileURLToPath(import.meta.url))

const ALLOWED_MIMES = [
  'application/pdf',
  'text/plain',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
]

const ALLOWED_EXTS = ['.pdf', '.txt', '.docx']
const MAX_SIZE_BYTES = 50 * 1024 * 1024 // 50 MB

// Files are saved directly to the knowledge_base path configured via .env,
// falling back to a local uploads/ directory for development.
function getUploadDir() {
  const kbPath = process.env.KB_PATH
  if (kbPath) {
    const resolved = join(process.cwd(), kbPath)
    if (!existsSync(resolved)) mkdirSync(resolved, { recursive: true })
    return resolved
  }
  const fallback = join(__dirname, '..', '..', 'uploads')
  if (!existsSync(fallback)) mkdirSync(fallback, { recursive: true })
  return fallback
}

const storage = multer.diskStorage({
  destination: (_req, _file, cb) => cb(null, getUploadDir()),
  filename: (_req, file, cb) => {
    const ext = extname(file.originalname).toLowerCase()
    cb(null, `${uuidv4()}${ext}`)
  },
})

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
