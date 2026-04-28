import { Router } from 'express'
import { query } from '../../db/index.js'
import { requireAppAuth } from '../../middleware/appAuth.js'

const router = Router()
router.use(requireAppAuth)

router.get('/themes', async (_req, res, next) => {
  try {
    const { rows } = await query(
      `SELECT t.theme_id, t.title, t.theme_order,
              COUNT(tf.file_id)::int AS file_count
       FROM theme t
       LEFT JOIN theme_file tf ON tf.theme_id = t.theme_id
       GROUP BY t.theme_id, t.title, t.theme_order
       ORDER BY t.theme_order ASC`
    )
    res.json(rows)
  } catch (err) {
    next(err)
  }
})

router.get('/themes/:id/download', async (req, res, next) => {
  try {
    const { id } = req.params
    const { rows } = await query(
      `SELECT f.file_id, f.filename
       FROM theme_file tf
       JOIN file f ON f.file_id = tf.file_id
       WHERE tf.theme_id = $1
       ORDER BY f.filename ASC`,
      [id]
    )
    if (!rows.length) return res.status(404).json({ error: 'Theme files not found' })

    // MVP during migration: return file list metadata.
    res.json({
      theme_id: id,
      files: rows,
      download_type: 'metadata',
      message: 'ZIP streaming will be added in the next iteration',
    })
  } catch (err) {
    next(err)
  }
})

export default router
