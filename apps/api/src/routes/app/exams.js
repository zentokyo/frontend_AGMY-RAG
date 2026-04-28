import { Router } from 'express'
import { v4 as uuidv4 } from 'uuid'
import { query } from '../../db/index.js'
import { requireAppAuth } from '../../middleware/appAuth.js'

const router = Router()
router.use(requireAppAuth)

async function getOrCreateExamQuestions(examId, examThemeId, questionCount) {
  const { rows: existing } = await query(
    `SELECT eq.exam_question_id, eq.status, q.question_id, q.text, q.answer_text
     FROM exam_question eq
     JOIN question q ON q.question_id = eq.question_id
     WHERE eq.exam_id = $1
     ORDER BY eq.exam_question_id ASC`,
    [examId]
  )
  if (existing.length) return existing

  const { rows: qRows } = await query(
    `SELECT q.question_id, q.text, q.answer_text
     FROM question q
     WHERE q.theme_id = (
       SELECT t.theme_id
       FROM exam_theme et
       JOIN theme t ON t.title = et.title
       WHERE et.exam_theme_id = $1
       LIMIT 1
     )
     ORDER BY q.question_id ASC
     LIMIT $2`,
    [examThemeId, questionCount]
  )

  const picked = qRows.length ? qRows : (await query(
    `SELECT question_id, text, answer_text
     FROM question
     ORDER BY question_id ASC
     LIMIT $1`,
    [questionCount]
  )).rows

  for (const q of picked) {
    await query(
      `INSERT INTO exam_question (exam_question_id, exam_id, question_id, status)
       VALUES ($1, $2, $3, $4)`,
      [uuidv4(), examId, q.question_id, 'На вопрос нет ответа']
    )
  }

  return (await query(
    `SELECT eq.exam_question_id, eq.status, q.question_id, q.text, q.answer_text
     FROM exam_question eq
     JOIN question q ON q.question_id = eq.question_id
     WHERE eq.exam_id = $1
     ORDER BY eq.exam_question_id ASC`,
    [examId]
  )).rows
}

router.get('/exam-themes', async (_req, res, next) => {
  try {
    const { rows } = await query(
      `SELECT exam_theme_id, title, exam_theme_order
       FROM exam_theme
       ORDER BY exam_theme_order ASC`
    )
    res.json(rows.map((r) => ({ ...r, is_enable: true })))
  } catch (err) {
    next(err)
  }
})

router.post('/exams', async (req, res, next) => {
  try {
    const { question_count = 10, exam_theme_id } = req.body
    const count = Math.max(1, Math.min(Number(question_count) || 10, 10))

    const { rows: inWork } = await query(
      `SELECT exam_id, exam_theme_id, question_count, status, start_exam
       FROM exam
       WHERE user_id = $1 AND status = $2
       ORDER BY start_exam DESC
       LIMIT 1`,
      [req.appUser.id, 'В работе']
    )
    if (inWork.length) {
      return res.status(409).json({ error: 'User already has active exam', exam: inWork[0] })
    }

    const chosenThemeId = exam_theme_id || (await query(
      `SELECT exam_theme_id FROM exam_theme ORDER BY exam_theme_order ASC LIMIT 1`
    )).rows[0]?.exam_theme_id

    if (!chosenThemeId) {
      return res.status(400).json({ error: 'No exam themes available' })
    }

    const examId = uuidv4()
    await query(
      `INSERT INTO exam (exam_id, user_id, exam_theme_id, type, question_count, status, start_exam, end_exam, rate)
       VALUES ($1, $2, $3, $4, $5, $6, NOW(), NULL, NULL)`,
      [examId, req.appUser.id, chosenThemeId, 'Итоговый экзамен', count, 'В работе']
    )

    await getOrCreateExamQuestions(examId, chosenThemeId, count)

    const { rows } = await query(
      `SELECT exam_id, exam_theme_id, question_count, status, start_exam
       FROM exam WHERE exam_id = $1`,
      [examId]
    )
    res.status(201).json(rows[0])
  } catch (err) {
    next(err)
  }
})

router.get('/exams/in-progress', async (req, res, next) => {
  try {
    const { rows } = await query(
      `SELECT exam_id, exam_theme_id, question_count, status, start_exam
       FROM exam
       WHERE user_id = $1 AND status = $2
       ORDER BY start_exam DESC
       LIMIT 1`,
      [req.appUser.id, 'В работе']
    )
    if (!rows.length) return res.status(404).json({ error: 'No active exam' })
    res.json(rows[0])
  } catch (err) {
    next(err)
  }
})

router.post('/exams/:examId/questions/ask', async (req, res, next) => {
  try {
    const { examId } = req.params
    const { rows: examRows } = await query(
      `SELECT exam_id, exam_theme_id, question_count, status
       FROM exam WHERE exam_id = $1 AND user_id = $2`,
      [examId, req.appUser.id]
    )
    if (!examRows.length) return res.status(404).json({ error: 'Exam not found' })
    if (examRows[0].status !== 'В работе') return res.status(400).json({ error: 'Exam already completed' })

    const list = await getOrCreateExamQuestions(examId, examRows[0].exam_theme_id, examRows[0].question_count)
    const nextQuestion = list.find((q) => q.status === 'На вопрос нет ответа')
    if (!nextQuestion) {
      return res.status(404).json({ error: 'No unanswered questions left' })
    }

    res.json({
      exam_id: examId,
      question: {
        exam_question_id: nextQuestion.exam_question_id,
        question_id: nextQuestion.question_id,
        text: nextQuestion.text,
      },
    })
  } catch (err) {
    next(err)
  }
})

router.get('/exams/:examId/questions/unanswered', async (req, res, next) => {
  try {
    const { examId } = req.params
    const { rows } = await query(
      `SELECT eq.exam_question_id, q.question_id, q.text
       FROM exam_question eq
       JOIN exam e ON e.exam_id = eq.exam_id
       JOIN question q ON q.question_id = eq.question_id
       WHERE e.exam_id = $1
         AND e.user_id = $2
         AND eq.status = $3
       ORDER BY eq.exam_question_id ASC
       LIMIT 1`,
      [examId, req.appUser.id, 'На вопрос нет ответа']
    )
    if (!rows.length) return res.status(404).json({ error: 'No unanswered question' })
    res.json({ question: rows[0] })
  } catch (err) {
    next(err)
  }
})

export default router
