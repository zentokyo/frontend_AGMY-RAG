import { Router } from 'express'
import { v4 as uuidv4 } from 'uuid'
import { query } from '../../db/index.js'
import { requireAppAuth } from '../../middleware/appAuth.js'

const router = Router()
router.use(requireAppAuth)

router.post('/answers', async (req, res, next) => {
  try {
    const { exam_question_id, answer_text } = req.body
    if (!exam_question_id || !answer_text?.trim()) {
      return res.status(400).json({ error: 'exam_question_id and answer_text are required' })
    }

    const { rows } = await query(
      `SELECT eq.exam_question_id, eq.exam_id, eq.status, q.answer_text, q.text
       FROM exam_question eq
       JOIN exam e ON e.exam_id = eq.exam_id
       JOIN question q ON q.question_id = eq.question_id
       WHERE eq.exam_question_id = $1 AND e.user_id = $2`,
      [exam_question_id, req.appUser.id]
    )
    if (!rows.length) return res.status(404).json({ error: 'Question not found' })
    const item = rows[0]
    if (item.status !== 'На вопрос нет ответа') {
      return res.status(409).json({ error: 'Question already answered' })
    }

    const normalizedGiven = answer_text.trim().toLowerCase()
    const normalizedModel = String(item.answer_text || '').trim().toLowerCase()
    const isCorrect = normalizedGiven === normalizedModel

    await query(
      `INSERT INTO answer (answer_id, exam_question_id, answer_text, is_correct)
       VALUES ($1, $2, $3, $4)`,
      [uuidv4(), exam_question_id, answer_text.trim(), isCorrect]
    )
    await query(
      `UPDATE exam_question SET status = $1 WHERE exam_question_id = $2`,
      ['На вопрос дан ответ', exam_question_id]
    )

    const { rows: pending } = await query(
      `SELECT COUNT(*)::int AS left_count
       FROM exam_question
       WHERE exam_id = $1 AND status = $2`,
      [item.exam_id, 'На вопрос нет ответа']
    )

    if (pending[0].left_count === 0) {
      await query(
        `UPDATE exam SET status = $1, end_exam = NOW() WHERE exam_id = $2`,
        ['Выполнен', item.exam_id]
      )
    }

    res.json({
      exam_id: item.exam_id,
      exam_question_id,
      is_correct: isCorrect,
      completed: pending[0].left_count === 0,
      left_count: pending[0].left_count,
    })
  } catch (err) {
    next(err)
  }
})

export default router
