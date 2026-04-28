/**
 * /api/questions — Q&A management
 *
 * Maps to the AGMY_RAG schema:
 *   question (question_id UUID PK, theme_id UUID FK, text, answer_text)
 *   theme    (theme_id UUID PK, title)
 */

import { Router } from 'express'
import { v4 as uuidv4 } from 'uuid'
import { query } from '../db/index.js'
import { requireAuth } from '../middleware/auth.js'

const router = Router()
router.use(requireAuth)

// ─── GET /api/questions/stats ───────────────────────────────────────────────
router.get('/stats', async (_req, res, next) => {
  try {
    const total = await query('SELECT COUNT(*) AS total FROM question')
    const byTheme = await query(`
      SELECT t.title AS theme, COUNT(q.question_id) AS count
      FROM question q
      JOIN theme t ON t.theme_id = q.theme_id
      GROUP BY t.title
      ORDER BY count DESC
      LIMIT 10
    `)
    res.json({
      total:      parseInt(total.rows[0].total),
      by_theme:   byTheme.rows,
    })
  } catch (err) { next(err) }
})

// ─── GET /api/questions/themes ─────────────────────────────────────────────
// Helper: list themes for the dropdown in create/edit forms
router.get('/themes', async (_req, res, next) => {
  try {
    const { rows } = await query(
      'SELECT theme_id AS id, title FROM theme ORDER BY theme_order ASC'
    )
    res.json(rows)
  } catch (err) { next(err) }
})

// ─── GET /api/questions ─────────────────────────────────────────────────────
router.get('/', async (req, res, next) => {
  try {
    const page     = Math.max(parseInt(req.query.page  || '1'), 1)
    const limit    = Math.min(parseInt(req.query.limit || '20'), 100)
    const offset   = (page - 1) * limit
    const search   = req.query.search   || ''
    const themeId  = req.query.theme_id || ''

    const conditions = []
    const params = []
    let p = 1

    if (search) {
      conditions.push(`(q.text ILIKE $${p} OR q.answer_text ILIKE $${p})`)
      params.push(`%${search}%`)
      p++
    }
    if (themeId) {
      conditions.push(`q.theme_id = $${p}`)
      params.push(themeId)
      p++
    }

    const where = conditions.length ? `WHERE ${conditions.join(' AND ')}` : ''

    const countRes = await query(`SELECT COUNT(*) FROM question q ${where}`, params)
    const total = parseInt(countRes.rows[0].count)

    const dataRes = await query(
      `SELECT
         q.question_id AS id,
         q.text,
         q.answer_text,
         q.theme_id,
         t.title AS theme_title
       FROM question q
       JOIN theme t ON t.theme_id = q.theme_id
       ${where}
       ORDER BY t.theme_order ASC, q.text ASC
       LIMIT $${p} OFFSET $${p + 1}`,
      [...params, limit, offset]
    )

    res.json({
      data: dataRes.rows,
      pagination: { total, page, limit, pages: Math.ceil(total / limit) },
    })
  } catch (err) { next(err) }
})

// ─── POST /api/questions ─────────────────────────────────────────────────────
router.post('/', async (req, res, next) => {
  try {
    const { text, answer_text, theme_id } = req.body
    if (!text?.trim())        return res.status(400).json({ error: 'text is required' })
    if (!answer_text?.trim()) return res.status(400).json({ error: 'answer_text is required' })
    if (!theme_id)            return res.status(400).json({ error: 'theme_id is required' })

    // Verify theme exists
    const { rows: themeRows } = await query('SELECT theme_id, title FROM theme WHERE theme_id = $1', [theme_id])
    if (!themeRows.length) return res.status(400).json({ error: 'Theme not found' })

    const questionId = uuidv4()
    await query(
      'INSERT INTO question (question_id, theme_id, text, answer_text) VALUES ($1, $2, $3, $4)',
      [questionId, theme_id, text.trim(), answer_text.trim()]
    )

    res.status(201).json({
      id:          questionId,
      text:        text.trim(),
      answer_text: answer_text.trim(),
      theme_id,
      theme_title: themeRows[0].title,
    })
  } catch (err) { next(err) }
})

// ─── PUT /api/questions/:id ──────────────────────────────────────────────────
router.put('/:id', async (req, res, next) => {
  try {
    const { id } = req.params
    const { text, answer_text, theme_id } = req.body

    const { rows: existing } = await query('SELECT question_id FROM question WHERE question_id = $1', [id])
    if (!existing.length) return res.status(404).json({ error: 'Question not found' })

    if (theme_id) {
      const { rows: themeRows } = await query('SELECT theme_id FROM theme WHERE theme_id = $1', [theme_id])
      if (!themeRows.length) return res.status(400).json({ error: 'Theme not found' })
    }

    await query(
      `UPDATE question
       SET text = COALESCE($1, text),
           answer_text = COALESCE($2, answer_text),
           theme_id = COALESCE($3, theme_id)
       WHERE question_id = $4`,
      [text?.trim() || null, answer_text?.trim() || null, theme_id || null, id]
    )

    const { rows } = await query(
      `SELECT q.question_id AS id, q.text, q.answer_text, q.theme_id, t.title AS theme_title
       FROM question q JOIN theme t ON t.theme_id = q.theme_id
       WHERE q.question_id = $1`,
      [id]
    )
    res.json(rows[0])
  } catch (err) { next(err) }
})

// ─── DELETE /api/questions/:id ───────────────────────────────────────────────
router.delete('/:id', async (req, res, next) => {
  try {
    const { id } = req.params
    const { rows } = await query('DELETE FROM question WHERE question_id = $1 RETURNING question_id', [id])
    if (!rows.length) return res.status(404).json({ error: 'Question not found' })
    res.json({ message: 'Question deleted' })
  } catch (err) { next(err) }
})

export default router
