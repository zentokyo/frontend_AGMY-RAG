import { Router } from 'express'
import { unlink } from 'fs/promises'
import { join, resolve } from 'path'
import { existsSync } from 'fs'
import { query } from '../db/index.js'
import { requireAuth } from '../middleware/auth.js'
import { upload } from '../middleware/upload.js'
import { runIngest, deleteFromChroma } from '../services/python.js'

const router = Router()

// All document routes require authentication
router.use(requireAuth)

// GET /api/documents/stats
router.get('/stats', async (_req, res, next) => {
  try {
    const { rows } = await query(`
      SELECT
        COUNT(*)                             AS total,
        COUNT(*) FILTER (WHERE status = 'indexed')     AS indexed,
        COUNT(*) FILTER (WHERE status = 'processing')  AS processing,
        COUNT(*) FILTER (WHERE status = 'error')       AS error,
        COALESCE(SUM(file_size), 0)          AS total_size
      FROM documents
    `)
    res.json(rows[0])
  } catch (err) {
    next(err)
  }
})

// GET /api/documents
router.get('/', async (_req, res, next) => {
  try {
    const { rows } = await query(`
      SELECT id, original_name, stored_filename, file_size, mime_type, status, error_message, uploaded_at
      FROM documents
      ORDER BY uploaded_at DESC
    `)
    res.json(rows)
  } catch (err) {
    next(err)
  }
})

// POST /api/documents/upload
router.post('/upload', upload.single('file'), async (req, res, next) => {
  if (!req.file) {
    return res.status(400).json({ error: 'No file uploaded' })
  }

  const { originalname, filename, size, mimetype } = req.file

  let docId
  try {
    const { rows } = await query(
      `INSERT INTO documents (original_name, stored_filename, file_size, mime_type, status)
       VALUES ($1, $2, $3, $4, 'processing') RETURNING id`,
      [originalname, filename, size, mimetype]
    )
    docId = rows[0].id
  } catch (err) {
    return next(err)
  }

  res.status(202).json({
    id: docId,
    original_name: originalname,
    stored_filename: filename,
    file_size: size,
    mime_type: mimetype,
    status: 'processing',
  })

  // Run ingestion asynchronously — client polls for status
  runIngest()
    .then(() =>
      query(`UPDATE documents SET status = 'indexed', error_message = NULL WHERE id = $1`, [docId])
    )
    .catch((err) =>
      query(`UPDATE documents SET status = 'error', error_message = $1 WHERE id = $2`, [
        err.message.slice(0, 500),
        docId,
      ])
    )
})

// DELETE /api/documents/:id
router.delete('/:id', async (req, res, next) => {
  const { id } = req.params
  try {
    const { rows } = await query('SELECT * FROM documents WHERE id = $1', [id])
    if (!rows.length) return res.status(404).json({ error: 'Document not found' })

    const doc = rows[0]

    // Remove file from disk
    const kbPath = resolve(process.env.KB_PATH || join('..', '..', 'uploads'))
    const filePath = join(kbPath, doc.stored_filename)
    if (existsSync(filePath)) {
      await unlink(filePath).catch(() => {}) // don't fail if file already gone
    }

    await query('DELETE FROM documents WHERE id = $1', [id])

    res.json({ message: 'Document deleted' })

    // Remove chunks from ChromaDB asynchronously
    if (doc.status === 'indexed') {
      deleteFromChroma(doc.stored_filename).catch((err) =>
        console.error('[python] Failed to remove chunks from ChromaDB:', err.message)
      )
    }
  } catch (err) {
    next(err)
  }
})

export default router
