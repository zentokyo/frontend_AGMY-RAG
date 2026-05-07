import { Router } from 'express'
import { v4 as uuidv4 } from 'uuid'
import { query } from '../../db/index.js'
import { requireAppAuth } from '../../middleware/appAuth.js'

const router = Router()
router.use(requireAppAuth)

const PASS_THRESHOLD = 0.7

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
    const leftCount = pending[0].left_count
    const completed = leftCount === 0

    let isPassed = null
    let score = null

    if (completed) {
      await query(
        `UPDATE exam SET status = $1, end_exam = NOW() WHERE exam_id = $2`,
        ['Выполнен', item.exam_id]
      )

      // Calculate score and update course progress
      const { rows: scoreRows } = await query(
        `SELECT COUNT(*)::int AS total,
                COALESCE(SUM(CASE WHEN a.is_correct THEN 1 ELSE 0 END), 0)::int AS correct
         FROM answer a
         JOIN exam_question eq ON eq.exam_question_id = a.exam_question_id
         WHERE eq.exam_id = $1`,
        [item.exam_id]
      )

      const { rows: examCtx } = await query(
        `SELECT exam_scope, block_topic_id, course_block_id FROM exam WHERE exam_id = $1`,
        [item.exam_id]
      )

      const totals = scoreRows[0]
      score = totals.total ? totals.correct / totals.total : 0
      isPassed = score >= PASS_THRESHOLD
      const status = isPassed ? 'passed' : 'failed'
      const ctx = examCtx[0] || {}

      if (ctx.exam_scope === 'topic' && ctx.block_topic_id) {
        await query(
          `INSERT INTO user_topic_progress (user_id, topic_id, status, attempts, best_score, last_exam_id, updated_at)
           VALUES ($1, $2, $3, 1, $4, $5, NOW())
           ON CONFLICT (user_id, topic_id) DO UPDATE SET
             status     = $3,
             attempts   = user_topic_progress.attempts + 1,
             best_score = GREATEST(user_topic_progress.best_score, $4),
             last_exam_id = $5,
             updated_at = NOW()`,
          [req.appUser.id, ctx.block_topic_id, status, score, item.exam_id]
        )
      }

      if (ctx.exam_scope === 'block' && ctx.course_block_id) {
        await query(
          `INSERT INTO user_block_progress (user_id, block_id, status, attempts, best_score, last_exam_id, updated_at)
           VALUES ($1, $2, $3, 1, $4, $5, NOW())
           ON CONFLICT (user_id, block_id) DO UPDATE SET
             status     = $3,
             attempts   = user_block_progress.attempts + 1,
             best_score = GREATEST(user_block_progress.best_score, $4),
             last_exam_id = $5,
             updated_at = NOW()`,
          [req.appUser.id, ctx.course_block_id, status, score, item.exam_id]
        )
      }

      if (ctx.exam_scope === 'final') {
        await query(
          `INSERT INTO user_course_progress (user_id, status, attempts, best_score, last_exam_id, completed_at)
           VALUES ($1, $2, 1, $3, $4, $5)
           ON CONFLICT (user_id) DO UPDATE SET
             status       = $2,
             attempts     = user_course_progress.attempts + 1,
             best_score   = GREATEST(user_course_progress.best_score, $3),
             last_exam_id = $4,
             completed_at = $5`,
          [req.appUser.id, status, score, item.exam_id, isPassed ? new Date() : null]
        )
      }
    }

    res.json({
      exam_id: item.exam_id,
      exam_question_id,
      is_correct: isCorrect,
      completed,
      left_count: leftCount,
      ...(completed ? { is_passed: isPassed, score } : {}),
    })
  } catch (err) {
    next(err)
  }
})

export default router
