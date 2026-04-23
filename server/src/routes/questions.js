import { Router } from 'express'
import { query } from '../db/index.js'
import { requireAuth } from '../middleware/auth.js'

const router = Router()

router.use(requireAuth)

// GET /api/questions/stats
router.get('/stats', async (_req, res, next) => {
  try {
    const { rows } = await query(`
      SELECT
        COUNT(*)                                       AS total,
        COUNT(*) FILTER (WHERE is_active = true)       AS active,
        COUNT(*) FILTER (WHERE is_active = false)      AS inactive,
        COUNT(DISTINCT category) FILTER (WHERE category IS NOT NULL) AS categories
      FROM questions
    `)

    const cats = await query(`
      SELECT category, COUNT(*) AS count
      FROM questions
      WHERE category IS NOT NULL
      GROUP BY category
      ORDER BY count DESC
      LIMIT 10
    `)

    res.json({ ...rows[0], by_category: cats.rows })
  } catch (err) {
    next(err)
  }
})

// GET /api/questions
router.get('/', async (req, res, next) => {
  try {
    const page     = Math.max(parseInt(req.query.page  || '1'), 1)
    const limit    = Math.min(parseInt(req.query.limit || '20'), 100)
    const offset   = (page - 1) * limit
    const search   = req.query.search   || ''
    const category = req.query.category || ''
    const isActive = req.query.is_active

    const conditions = []
    const params = []
    let p = 1

    if (search) {
      conditions.push(`(question_text ILIKE $${p} OR reference_answer ILIKE $${p})`)
      params.push(`%${search}%`)
      p++
    }
    if (category) {
      conditions.push(`category = $${p}`)
      params.push(category)
      p++
    }
    if (isActive !== undefined && isActive !== '') {
      conditions.push(`is_active = $${p}`)
      params.push(isActive === 'true')
      p++
    }

    const where = conditions.length ? `WHERE ${conditions.join(' AND ')}` : ''

    const countRes = await query(`SELECT COUNT(*) FROM questions ${where}`, params)
    const total = parseInt(countRes.rows[0].count)

    const dataRes = await query(
      `SELECT id, question_text, reference_answer, category, tags, is_active, created_at, updated_at
       FROM questions ${where}
       ORDER BY created_at DESC
       LIMIT $${p} OFFSET $${p + 1}`,
      [...params, limit, offset]
    )

    res.json({
      data: dataRes.rows,
      pagination: { total, page, limit, pages: Math.ceil(total / limit) },
    })
  } catch (err) {
    next(err)
  }
})

// POST /api/questions
router.post('/', async (req, res, next) => {
  try {
    const { question_text, reference_answer, category, tags, is_active } = req.body

    if (!question_text?.trim()) return res.status(400).json({ error: 'question_text is required' })
    if (!reference_answer?.trim()) return res.status(400).json({ error: 'reference_answer is required' })

    const tagsArray = Array.isArray(tags) ? tags : []

    const { rows } = await query(
      `INSERT INTO questions (question_text, reference_answer, category, tags, is_active)
       VALUES ($1, $2, $3, $4, $5) RETURNING *`,
      [
        question_text.trim(),
        reference_answer.trim(),
        category?.trim() || null,
        tagsArray,
        is_active !== false,
      ]
    )

    res.status(201).json(rows[0])
  } catch (err) {
    next(err)
  }
})

// PUT /api/questions/:id
router.put('/:id', async (req, res, next) => {
  try {
    const { id } = req.params
    const { question_text, reference_answer, category, tags, is_active } = req.body

    const { rows: existing } = await query('SELECT id FROM questions WHERE id = $1', [id])
    if (!existing.length) return res.status(404).json({ error: 'Question not found' })

    const tagsArray = Array.isArray(tags) ? tags : []

    const { rows } = await query(
      `UPDATE questions
       SET question_text = $1, reference_answer = $2, category = $3, tags = $4, is_active = $5
       WHERE id = $6 RETURNING *`,
      [
        question_text?.trim(),
        reference_answer?.trim(),
        category?.trim() || null,
        tagsArray,
        is_active !== false,
        id,
      ]
    )

    res.json(rows[0])
  } catch (err) {
    next(err)
  }
})

// DELETE /api/questions/:id
router.delete('/:id', async (req, res, next) => {
  try {
    const { id } = req.params
    const { rows } = await query('DELETE FROM questions WHERE id = $1 RETURNING id', [id])
    if (!rows.length) return res.status(404).json({ error: 'Question not found' })
    res.json({ message: 'Question deleted' })
  } catch (err) {
    next(err)
  }
})

export default router
