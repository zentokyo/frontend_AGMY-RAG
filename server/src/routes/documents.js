/**
 * /api/documents — Knowledge Base management
 *
 * Maps to the AGMY_RAG schema:
 *   theme       (theme_id UUID PK, title, theme_order)
 *   file        (file_id UUID PK, filename)
 *   theme_file  (theme_id FK, file_id FK)
 *
 * Files are stored in MinIO (same bucket as AGMY_RAG backend).
 * Filename is stored in `file.filename` and is also the S3 object key.
 */

import { Router } from 'express'
import { v4 as uuidv4 } from 'uuid'
import { extname } from 'path'
import { query } from '../db/index.js'
import { requireAuth } from '../middleware/auth.js'
import { upload } from '../middleware/upload.js'
import { uploadToS3, deleteFromS3 } from '../services/s3.js'

const router = Router()
router.use(requireAuth)

// ─── helpers ───────────────────────────────────────────────────────────────

/** Transliterate Cyrillic → ASCII (mirrors Python unidecode used by AGMY_RAG) */
function toAsciiFilename(name) {
  const map = {
    а:'a',б:'b',в:'v',г:'g',д:'d',е:'e',ё:'yo',ж:'zh',з:'z',и:'i',
    й:'j',к:'k',л:'l',м:'m',н:'n',о:'o',п:'p',р:'r',с:'s',т:'t',
    у:'u',ф:'f',х:'kh',ц:'ts',ч:'ch',ш:'sh',щ:'sch',ъ:'',ы:'y',ь:'',
    э:'e',ю:'yu',я:'ya',
  }
  return name
    .toLowerCase()
    .split('')
    .map((c) => map[c] ?? c)
    .join('')
    .replace(/[^a-z0-9._-]/g, '_')
}

// ─── GET /api/documents/stats ───────────────────────────────────────────────
router.get('/stats', async (_req, res, next) => {
  try {
    const { rows } = await query(`
      SELECT
        COUNT(DISTINCT t.theme_id)   AS total_themes,
        COUNT(tf.file_id)            AS total_files
      FROM theme t
      LEFT JOIN theme_file tf ON tf.theme_id = t.theme_id
    `)
    res.json(rows[0])
  } catch (err) { next(err) }
})

// ─── GET /api/documents ─────────────────────────────────────────────────────
router.get('/', async (_req, res, next) => {
  try {
    const { rows } = await query(`
      SELECT
        t.theme_id   AS id,
        t.title,
        t.theme_order,
        COALESCE(
          json_agg(
            json_build_object('file_id', f.file_id, 'filename', f.filename)
          ) FILTER (WHERE f.file_id IS NOT NULL),
          '[]'
        ) AS files,
        COUNT(tf.file_id) AS file_count
      FROM theme t
      LEFT JOIN theme_file tf ON tf.theme_id = t.theme_id
      LEFT JOIN file f        ON f.file_id   = tf.file_id
      GROUP BY t.theme_id, t.title, t.theme_order
      ORDER BY t.theme_order ASC
    `)
    res.json(rows)
  } catch (err) { next(err) }
})

// ─── POST /api/documents/upload ─────────────────────────────────────────────
// multipart/form-data: { title: string, files: File[] }
router.post('/upload', upload.array('files', 20), async (req, res, next) => {
  const { title } = req.body
  if (!title?.trim()) return res.status(400).json({ error: 'title is required' })
  if (!req.files?.length) return res.status(400).json({ error: 'At least one file is required' })

  const client = await (await import('../db/index.js')).getClient()
  try {
    await client.query('BEGIN')

    // Get next theme_order
    const { rows: orderRows } = await client.query(
      'SELECT COALESCE(MAX(theme_order), 0) AS max_order FROM theme'
    )
    const nextOrder = parseInt(orderRows[0].max_order) + 1
    const themeId = uuidv4()

    await client.query(
      'INSERT INTO theme (theme_id, title, theme_order) VALUES ($1, $2, $3)',
      [themeId, title.trim(), nextOrder]
    )

    // Also create exam_theme mirror (AGMY_RAG requirement)
    try {
      const { rows: etOrder } = await client.query(
        'SELECT COALESCE(MAX(exam_theme_order), 0) AS max_order FROM exam_theme'
      )
      const etNextOrder = parseInt(etOrder[0].max_order) + 1
      await client.query(
        'INSERT INTO exam_theme (exam_theme_id, title, exam_theme_order) VALUES ($1, $2, $3)',
        [uuidv4(), title.trim(), etNextOrder]
      )
    } catch {
      // exam_theme is optional — skip if table doesn't exist yet
    }

    const uploadedFiles = []
    for (const f of req.files) {
      const ext      = extname(f.originalname).toLowerCase()
      const basename = f.originalname.replace(/\.[^/.]+$/, '')
      const filename = toAsciiFilename(basename) + ext
      const fileId   = uuidv4()

      await uploadToS3(f.buffer, filename, f.mimetype)
      await client.query('INSERT INTO file (file_id, filename) VALUES ($1, $2)', [fileId, filename])
      await client.query(
        'INSERT INTO theme_file (theme_id, file_id) VALUES ($1, $2)',
        [themeId, fileId]
      )
      uploadedFiles.push({ file_id: fileId, filename })
    }

    await client.query('COMMIT')

    res.status(201).json({
      id:         themeId,
      title:      title.trim(),
      theme_order: nextOrder,
      files:      uploadedFiles,
      file_count: uploadedFiles.length,
    })
  } catch (err) {
    await client.query('ROLLBACK')
    next(err)
  } finally {
    client.release()
  }
})

// ─── DELETE /api/documents/:id ───────────────────────────────────────────────
// :id = theme_id (UUID)
router.delete('/:id', async (req, res, next) => {
  const { id } = req.params
  const client = await (await import('../db/index.js')).getClient()
  try {
    // Check theme exists
    const { rows } = await client.query('SELECT theme_id FROM theme WHERE theme_id = $1', [id])
    if (!rows.length) return res.status(404).json({ error: 'Theme not found' })

    await client.query('BEGIN')

    // Get all files belonging to this theme
    const { rows: files } = await client.query(
      'SELECT f.file_id, f.filename FROM file f JOIN theme_file tf ON tf.file_id = f.file_id WHERE tf.theme_id = $1',
      [id]
    )

    // Delete theme_file links first
    await client.query('DELETE FROM theme_file WHERE theme_id = $1', [id])

    // Delete file records
    for (const f of files) {
      await client.query('DELETE FROM file WHERE file_id = $1', [f.file_id])
    }

    // Delete theme
    await client.query('DELETE FROM theme WHERE theme_id = $1', [id])

    await client.query('COMMIT')

    res.json({ message: 'Theme deleted' })

    // Delete from MinIO asynchronously
    for (const f of files) {
      deleteFromS3(f.filename).catch(() => {})
    }
  } catch (err) {
    await client.query('ROLLBACK')
    next(err)
  } finally {
    client.release()
  }
})

export default router
