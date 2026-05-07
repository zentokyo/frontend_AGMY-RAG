import { Router } from 'express'
import { v4 as uuidv4 } from 'uuid'
import { query } from '../../db/index.js'
import { requireAppAuth } from '../../middleware/appAuth.js'

const router = Router()
router.use(requireAppAuth)

const PASS_THRESHOLD = 0.7
const TOPIC_QUESTION_COUNT = 3
const BLOCK_QUESTION_COUNT = 10
const FINAL_QUESTION_COUNT = 10

// ── helpers ──────────────────────────────────────────────────────────────────

async function getActiveExam(userId) {
  const { rows } = await query(
    `SELECT exam_id FROM exam WHERE user_id = $1 AND status = 'В работе' LIMIT 1`,
    [userId]
  )
  return rows[0] || null
}

async function isBlockUnlocked(userId, blockOrder) {
  // The block with the lowest order in the course is always unlocked
  const { rows: minRows } = await query(`SELECT MIN(block_order) AS min_order FROM course_block`)
  const minOrder = minRows[0]?.min_order
  if (!minOrder || blockOrder === minOrder) return true

  // Find the immediately preceding block by order
  const { rows: prevRows } = await query(
    `SELECT block_order FROM course_block WHERE block_order < $1 ORDER BY block_order DESC LIMIT 1`,
    [blockOrder]
  )
  if (!prevRows.length) return true
  const { rows } = await query(
    `SELECT ubp.status
     FROM user_block_progress ubp
     JOIN course_block cb ON cb.id = ubp.block_id
     WHERE ubp.user_id = $1 AND cb.block_order = $2`,
    [userId, prevRows[0].block_order]
  )
  return rows[0]?.status === 'passed'
}

async function isTopicUnlocked(userId, topicOrder, blockId, blockUnlocked) {
  if (!blockUnlocked) return false
  // The topic with the lowest order in the block is always unlocked
  const { rows: minRows } = await query(
    `SELECT MIN(topic_order) AS min_order FROM block_topic WHERE block_id = $1`,
    [blockId]
  )
  const minOrder = minRows[0]?.min_order
  if (!minOrder || topicOrder === minOrder) return true

  // Find the immediately preceding topic by order
  const { rows: prevRows } = await query(
    `SELECT topic_order FROM block_topic WHERE block_id = $1 AND topic_order < $2 ORDER BY topic_order DESC LIMIT 1`,
    [blockId, topicOrder]
  )
  if (!prevRows.length) return true
  const { rows } = await query(
    `SELECT utp.status
     FROM user_topic_progress utp
     JOIN block_topic bt ON bt.id = utp.topic_id
     WHERE utp.user_id = $1 AND bt.block_id = $2 AND bt.topic_order = $3`,
    [userId, blockId, prevRows[0].topic_order]
  )
  return rows[0]?.status === 'passed'
}

async function createExamWithQuestions(userId, { examThemeId, questionCount, examScope, blockTopicId, courseBlockId, questionThemeIds }) {
  let questionRows
  if (questionThemeIds && questionThemeIds.length > 0) {
    const { rows } = await query(
      `SELECT question_id FROM question WHERE theme_id = ANY($1::uuid[]) ORDER BY RANDOM() LIMIT $2`,
      [questionThemeIds, questionCount]
    )
    questionRows = rows
  } else {
    const { rows } = await query(
      `SELECT question_id FROM question ORDER BY RANDOM() LIMIT $1`,
      [questionCount]
    )
    questionRows = rows
  }

  if (!questionRows.length) {
    throw Object.assign(new Error('No questions available for this exam'), { status: 400 })
  }

  let actualThemeId = examThemeId
  if (!actualThemeId) {
    const { rows } = await query(`SELECT exam_theme_id FROM exam_theme ORDER BY exam_theme_order ASC LIMIT 1`)
    actualThemeId = rows[0]?.exam_theme_id
  }
  if (!actualThemeId) {
    throw Object.assign(new Error('No exam theme available'), { status: 400 })
  }

  const examId = uuidv4()
  const examType = examScope === 'final' ? 'Итоговый экзамен' : 'Не итоговый экзамен'
  await query(
    `INSERT INTO exam (exam_id, user_id, exam_theme_id, type, question_count, status, start_exam, end_exam, rate, exam_scope, block_topic_id, course_block_id)
     VALUES ($1, $2, $3, $4, $5, 'В работе', NOW(), NULL, NULL, $6, $7, $8)`,
    [examId, userId, actualThemeId, examType, questionRows.length, examScope, blockTopicId ?? null, courseBlockId ?? null]
  )

  for (const q of questionRows) {
    await query(
      `INSERT INTO exam_question (exam_question_id, exam_id, question_id, status) VALUES ($1, $2, $3, $4)`,
      [uuidv4(), examId, q.question_id, 'На вопрос нет ответа']
    )
  }

  return examId
}

// ── GET /api/app/course/blocks ───────────────────────────────────────────────
router.get('/course/blocks', async (req, res, next) => {
  try {
    const userId = req.appUser.id

    const { rows: blocks } = await query(
      `SELECT
         cb.id, cb.title, cb.description, cb.block_order,
         COALESCE(ubp.status, 'not_started') AS user_status,
         COALESCE(ubp.best_score, 0)::float  AS best_score,
         COALESCE(ubp.attempts, 0)::int       AS attempts,
         COUNT(bt.id)::int                    AS topics_total,
         COUNT(CASE WHEN COALESCE(utp.status, 'not_started') = 'passed' THEN 1 END)::int AS topics_passed
       FROM course_block cb
       LEFT JOIN block_topic bt ON bt.block_id = cb.id
       LEFT JOIN user_topic_progress utp ON utp.topic_id = bt.id AND utp.user_id = $1
       LEFT JOIN user_block_progress ubp ON ubp.block_id = cb.id AND ubp.user_id = $1
       GROUP BY cb.id, cb.title, cb.description, cb.block_order, ubp.status, ubp.best_score, ubp.attempts
       ORDER BY cb.block_order ASC`,
      [userId]
    )

    const result = blocks.map((b, idx) => ({
      ...b,
      is_unlocked: idx === 0 || blocks[idx - 1].user_status === 'passed',
    }))

    const { rows: cpRows } = await query(
      `SELECT status, best_score::float, attempts, completed_at, last_exam_id
       FROM user_course_progress WHERE user_id = $1`,
      [userId]
    )

    const allBlocksPassed = result.length > 0 && result.every((b) => b.user_status === 'passed')

    res.json({
      blocks: result,
      course_progress: cpRows[0] || { status: 'not_started', best_score: 0, attempts: 0 },
      final_exam_unlocked: allBlocksPassed,
    })
  } catch (err) {
    next(err)
  }
})

// ── GET /api/app/course/blocks/:blockId ──────────────────────────────────────
router.get('/course/blocks/:blockId', async (req, res, next) => {
  try {
    const userId = req.appUser.id
    const { blockId } = req.params

    const { rows: blockRows } = await query(
      `SELECT cb.id, cb.title, cb.description, cb.block_order,
              COALESCE(ubp.status, 'not_started')  AS user_status,
              COALESCE(ubp.best_score, 0)::float    AS best_score,
              COALESCE(ubp.attempts, 0)::int         AS attempts,
              ubp.last_exam_id
       FROM course_block cb
       LEFT JOIN user_block_progress ubp ON ubp.block_id = cb.id AND ubp.user_id = $1
       WHERE cb.id = $2`,
      [userId, blockId]
    )
    if (!blockRows.length) return res.status(404).json({ error: 'Block not found' })
    const block = blockRows[0]
    const blockUnlocked = await isBlockUnlocked(userId, block.block_order)

    const { rows: topics } = await query(
      `SELECT
         bt.id, bt.title, bt.topic_order, bt.exam_theme_id, bt.theme_id,
         COALESCE(utp.status, 'not_started')  AS user_status,
         COALESCE(utp.best_score, 0)::float    AS best_score,
         COALESCE(utp.attempts, 0)::int         AS attempts,
         utp.last_exam_id
       FROM block_topic bt
       LEFT JOIN user_topic_progress utp ON utp.topic_id = bt.id AND utp.user_id = $1
       WHERE bt.block_id = $2
       ORDER BY bt.topic_order ASC`,
      [userId, blockId]
    )

    const topicsWithUnlock = topics.map((t, idx) => ({
      ...t,
      is_unlocked: blockUnlocked && (idx === 0 || topics[idx - 1].user_status === 'passed'),
    }))

    const allTopicsPassed = topics.length > 0 && topics.every((t) => t.user_status === 'passed')

    res.json({
      block: { ...block, is_unlocked: blockUnlocked },
      topics: topicsWithUnlock,
      block_test_unlocked: allTopicsPassed,
    })
  } catch (err) {
    next(err)
  }
})

// ── GET /api/app/course/blocks/:blockId/topics/:topicId ──────────────────────
router.get('/course/blocks/:blockId/topics/:topicId', async (req, res, next) => {
  try {
    const userId = req.appUser.id
    const { blockId, topicId } = req.params

    const { rows: topicRows } = await query(
      `SELECT bt.id, bt.title, bt.topic_order, bt.exam_theme_id, bt.theme_id, bt.block_id,
              COALESCE(utp.status, 'not_started')  AS user_status,
              COALESCE(utp.best_score, 0)::float    AS best_score,
              COALESCE(utp.attempts, 0)::int         AS attempts,
              utp.last_exam_id
       FROM block_topic bt
       LEFT JOIN user_topic_progress utp ON utp.topic_id = bt.id AND utp.user_id = $1
       WHERE bt.id = $2 AND bt.block_id = $3`,
      [userId, topicId, blockId]
    )
    if (!topicRows.length) return res.status(404).json({ error: 'Topic not found' })
    const topic = topicRows[0]

    const { rows: blockRows } = await query(
      `SELECT block_order FROM course_block WHERE id = $1`,
      [blockId]
    )
    const blockUnlocked = blockRows.length ? await isBlockUnlocked(userId, blockRows[0].block_order) : false
    const topicUnlocked = await isTopicUnlocked(userId, topic.topic_order, parseInt(blockId), blockUnlocked)

    let materials = []
    if (topic.theme_id) {
      const { rows } = await query(
        `SELECT f.file_id, f.filename
         FROM theme_file tf JOIN file f ON f.file_id = tf.file_id
         WHERE tf.theme_id = $1 ORDER BY f.filename ASC`,
        [topic.theme_id]
      )
      materials = rows
    }

    // Count available questions
    let questionCount = 0
    if (topic.theme_id) {
      const { rows } = await query(
        `SELECT COUNT(*)::int AS cnt FROM question WHERE theme_id = $1`,
        [topic.theme_id]
      )
      questionCount = rows[0]?.cnt ?? 0
    }

    res.json({
      topic: { ...topic, is_unlocked: topicUnlocked },
      materials,
      question_count: questionCount,
    })
  } catch (err) {
    next(err)
  }
})

// ── POST /api/app/course/topics/:topicId/exam ────────────────────────────────
router.post('/course/topics/:topicId/exam', async (req, res, next) => {
  try {
    const userId = req.appUser.id
    const { topicId } = req.params

    const { rows: topicRows } = await query(
      `SELECT bt.id, bt.title, bt.topic_order, bt.exam_theme_id, bt.theme_id, bt.block_id,
              cb.block_order
       FROM block_topic bt
       JOIN course_block cb ON cb.id = bt.block_id
       WHERE bt.id = $1`,
      [topicId]
    )
    if (!topicRows.length) return res.status(404).json({ error: 'Topic not found' })
    const topic = topicRows[0]

    const blockUnlocked = await isBlockUnlocked(userId, topic.block_order)
    const topicUnlocked = await isTopicUnlocked(userId, topic.topic_order, topic.block_id, blockUnlocked)
    if (!topicUnlocked) {
      return res.status(403).json({ error: 'Topic is locked. Complete the previous topic first.' })
    }

    const active = await getActiveExam(userId)
    if (active) {
      return res.status(409).json({ error: 'You have an active exam', exam_id: active.exam_id })
    }

    let questionThemeIds = []
    if (topic.theme_id) {
      questionThemeIds = [topic.theme_id]
    } else if (topic.exam_theme_id) {
      const { rows } = await query(
        `SELECT t.theme_id FROM exam_theme et
         JOIN theme t ON t.title = et.title
         WHERE et.exam_theme_id = $1 LIMIT 1`,
        [topic.exam_theme_id]
      )
      if (rows.length) questionThemeIds = [rows[0].theme_id]
    }

    const examId = await createExamWithQuestions(userId, {
      examThemeId: topic.exam_theme_id,
      questionCount: TOPIC_QUESTION_COUNT,
      examScope: 'topic',
      blockTopicId: parseInt(topicId),
      courseBlockId: null,
      questionThemeIds,
    })

    res.status(201).json({ exam_id: examId })
  } catch (err) {
    next(err)
  }
})

// ── POST /api/app/course/blocks/:blockId/exam ────────────────────────────────
router.post('/course/blocks/:blockId/exam', async (req, res, next) => {
  try {
    const userId = req.appUser.id
    const { blockId } = req.params

    const { rows: blockRows } = await query(
      `SELECT id, block_order FROM course_block WHERE id = $1`,
      [blockId]
    )
    if (!blockRows.length) return res.status(404).json({ error: 'Block not found' })

    const blockUnlocked = await isBlockUnlocked(userId, blockRows[0].block_order)
    if (!blockUnlocked) {
      return res.status(403).json({ error: 'Block is locked. Complete the previous block first.' })
    }

    const { rows: topicStatus } = await query(
      `SELECT COUNT(bt.id)::int AS total,
              COUNT(CASE WHEN COALESCE(utp.status,'not_started') = 'passed' THEN 1 END)::int AS passed
       FROM block_topic bt
       LEFT JOIN user_topic_progress utp ON utp.topic_id = bt.id AND utp.user_id = $1
       WHERE bt.block_id = $2`,
      [userId, blockId]
    )
    if (topicStatus[0].total === 0) return res.status(400).json({ error: 'No topics in this block' })
    if (topicStatus[0].passed < topicStatus[0].total) {
      return res.status(403).json({
        error: 'Complete all topics in this block first.',
        topics_passed: topicStatus[0].passed,
        topics_total: topicStatus[0].total,
      })
    }

    const active = await getActiveExam(userId)
    if (active) return res.status(409).json({ error: 'You have an active exam', exam_id: active.exam_id })

    const { rows: themeRows } = await query(
      `SELECT DISTINCT theme_id FROM block_topic WHERE block_id = $1 AND theme_id IS NOT NULL`,
      [blockId]
    )
    const questionThemeIds = themeRows.map((r) => r.theme_id)

    const { rows: etRows } = await query(
      `SELECT exam_theme_id FROM block_topic WHERE block_id = $1 AND exam_theme_id IS NOT NULL ORDER BY topic_order ASC LIMIT 1`,
      [blockId]
    )

    const examId = await createExamWithQuestions(userId, {
      examThemeId: etRows[0]?.exam_theme_id ?? null,
      questionCount: BLOCK_QUESTION_COUNT,
      examScope: 'block',
      blockTopicId: null,
      courseBlockId: parseInt(blockId),
      questionThemeIds,
    })

    res.status(201).json({ exam_id: examId })
  } catch (err) {
    next(err)
  }
})

// ── POST /api/app/course/final-exam ─────────────────────────────────────────
router.post('/course/final-exam', async (req, res, next) => {
  try {
    const userId = req.appUser.id

    const { rows: blockStatus } = await query(
      `SELECT COUNT(cb.id)::int AS total,
              COUNT(CASE WHEN COALESCE(ubp.status,'not_started') = 'passed' THEN 1 END)::int AS passed
       FROM course_block cb
       LEFT JOIN user_block_progress ubp ON ubp.block_id = cb.id AND ubp.user_id = $1`,
      [userId]
    )
    if (blockStatus[0].total === 0) return res.status(400).json({ error: 'No blocks in course' })
    if (blockStatus[0].passed < blockStatus[0].total) {
      return res.status(403).json({
        error: 'Complete all blocks first.',
        blocks_passed: blockStatus[0].passed,
        blocks_total: blockStatus[0].total,
      })
    }

    const active = await getActiveExam(userId)
    if (active) return res.status(409).json({ error: 'You have an active exam', exam_id: active.exam_id })

    const examId = await createExamWithQuestions(userId, {
      examThemeId: null,
      questionCount: FINAL_QUESTION_COUNT,
      examScope: 'final',
      blockTopicId: null,
      courseBlockId: null,
      questionThemeIds: [],
    })

    res.status(201).json({ exam_id: examId })
  } catch (err) {
    next(err)
  }
})

// ── GET /api/app/course/exams/:examId/result ─────────────────────────────────
router.get('/course/exams/:examId/result', async (req, res, next) => {
  try {
    const { examId } = req.params
    const userId = req.appUser.id

    const { rows: examRows } = await query(
      `SELECT e.exam_id, e.status, e.exam_scope, e.block_topic_id, e.course_block_id, e.exam_theme_id,
              et.title AS theme_title
       FROM exam e
       JOIN exam_theme et ON et.exam_theme_id = e.exam_theme_id
       WHERE e.exam_id = $1 AND e.user_id = $2`,
      [examId, userId]
    )
    if (!examRows.length) return res.status(404).json({ error: 'Exam not found' })
    const exam = examRows[0]

    const { rows: statRows } = await query(
      `SELECT COUNT(*)::int AS total_answers,
              COALESCE(SUM(CASE WHEN a.is_correct THEN 1 ELSE 0 END), 0)::int AS correct_answers
       FROM answer a
       JOIN exam_question eq ON eq.exam_question_id = a.exam_question_id
       WHERE eq.exam_id = $1`,
      [examId]
    )

    const { rows: answerList } = await query(
      `SELECT q.text AS question_text, a.answer_text AS user_answer,
              q.answer_text AS model_answer, a.is_correct
       FROM answer a
       JOIN exam_question eq ON eq.exam_question_id = a.exam_question_id
       JOIN question q ON q.question_id = eq.question_id
       WHERE eq.exam_id = $1
       ORDER BY eq.exam_question_id ASC`,
      [examId]
    )

    const totals = statRows[0]
    const score = totals.total_answers ? totals.correct_answers / totals.total_answers : 0

    let context = {}
    if (exam.block_topic_id) {
      const { rows } = await query(
        `SELECT bt.block_id, bt.topic_order FROM block_topic bt WHERE bt.id = $1`,
        [exam.block_topic_id]
      )
      context = { block_id: rows[0]?.block_id, topic_id: exam.block_topic_id, topic_order: rows[0]?.topic_order }
    } else if (exam.course_block_id) {
      const { rows } = await query(
        `SELECT block_order FROM course_block WHERE id = $1`,
        [exam.course_block_id]
      )
      context = { block_id: exam.course_block_id, block_order: rows[0]?.block_order }
    }

    res.json({
      exam_id: examId,
      exam_scope: exam.exam_scope ?? 'standalone',
      status: exam.status,
      theme_title: exam.theme_title,
      total_answers: totals.total_answers,
      correct_answers: totals.correct_answers,
      score,
      is_passed: score >= PASS_THRESHOLD,
      pass_threshold: PASS_THRESHOLD,
      answer_list: answerList,
      context,
    })
  } catch (err) {
    next(err)
  }
})

export default router
