import { Router } from 'express'
import { query } from '../../db/index.js'
import { requireAppAuth } from '../../middleware/appAuth.js'

const router = Router()
router.use(requireAppAuth)

router.get('/stats/all', async (req, res, next) => {
  try {
    const { rows: totalRows } = await query(
      `SELECT
         COUNT(*)::int AS total_answers,
         COALESCE(SUM(CASE WHEN a.is_correct THEN 1 ELSE 0 END), 0)::int AS correct_answers
       FROM answer a
       JOIN exam_question eq ON eq.exam_question_id = a.exam_question_id
       JOIN exam e ON e.exam_id = eq.exam_id
       WHERE e.user_id = $1`,
      [req.appUser.id]
    )

    const { rows: byTheme } = await query(
      `SELECT
         et.title AS theme_title,
         COUNT(*)::int AS total_answers,
         COALESCE(SUM(CASE WHEN a.is_correct THEN 1 ELSE 0 END), 0)::int AS correct_answers
       FROM answer a
       JOIN exam_question eq ON eq.exam_question_id = a.exam_question_id
       JOIN exam e ON e.exam_id = eq.exam_id
       JOIN exam_theme et ON et.exam_theme_id = e.exam_theme_id
       WHERE e.user_id = $1
       GROUP BY et.title
       ORDER BY et.title ASC`,
      [req.appUser.id]
    )

    const total = totalRows[0]
    const accuracy = total.total_answers ? total.correct_answers / total.total_answers : 0
    res.json({
      total_answers: total.total_answers,
      correct_answers: total.correct_answers,
      accuracy,
      stat_by_theme: byTheme.map((r) => ({
        ...r,
        accuracy: r.total_answers ? r.correct_answers / r.total_answers : 0,
      })),
    })
  } catch (err) {
    next(err)
  }
})

router.get('/stats/last', async (req, res, next) => {
  try {
    const { rows: examRows } = await query(
      `SELECT exam_id, exam_theme_id
       FROM exam
       WHERE user_id = $1 AND status = $2
       ORDER BY end_exam DESC NULLS LAST, start_exam DESC
       LIMIT 1`,
      [req.appUser.id, 'Выполнен']
    )
    if (!examRows.length) return res.status(404).json({ error: 'No completed exams' })

    const exam = examRows[0]
    const { rows: statRows } = await query(
      `SELECT
         COUNT(*)::int AS total_answers,
         COALESCE(SUM(CASE WHEN a.is_correct THEN 1 ELSE 0 END), 0)::int AS correct_answers
       FROM answer a
       JOIN exam_question eq ON eq.exam_question_id = a.exam_question_id
       WHERE eq.exam_id = $1`,
      [exam.exam_id]
    )
    const { rows: answerList } = await query(
      `SELECT
         q.text AS question_text,
         a.answer_text AS user_answer,
         q.answer_text AS model_answer,
         a.is_correct
       FROM answer a
       JOIN exam_question eq ON eq.exam_question_id = a.exam_question_id
       JOIN question q ON q.question_id = eq.question_id
       WHERE eq.exam_id = $1
       ORDER BY eq.exam_question_id ASC`,
      [exam.exam_id]
    )
    const { rows: themeRows } = await query(
      `SELECT title FROM exam_theme WHERE exam_theme_id = $1`,
      [exam.exam_theme_id]
    )

    const totals = statRows[0]
    res.json({
      exam_id: exam.exam_id,
      theme_title: themeRows[0]?.title ?? null,
      total_answers: totals.total_answers,
      correct_answers: totals.correct_answers,
      accuracy: totals.total_answers ? totals.correct_answers / totals.total_answers : 0,
      answer_list: answerList,
    })
  } catch (err) {
    next(err)
  }
})

export default router
