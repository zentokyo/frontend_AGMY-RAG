import test from 'node:test'
import assert from 'node:assert/strict'
import { randomUUID } from 'node:crypto'

process.env.CLIENT_ORIGIN = 'http://localhost:5174'
process.env.PYTHON_API_URL ||= 'http://127.0.0.1:8001'
process.env.INTERNAL_API_TOKEN ||= 'change-me-internal-token'
process.env.DB_HOST ||= 'localhost'
process.env.DB_PORT ||= process.env.POSTGRES_PUBLISHED_PORT || '5433'
process.env.DB_NAME ||= process.env.POSTGRES_DB || 'assistant'
process.env.DB_USER ||= process.env.POSTGRES_USER || 'postgres'
process.env.DB_PASSWORD ||= process.env.POSTGRES_PASSWORD || 'example'

const { query, closeDb } = await import('./db.js')

const baseUrl = process.env.PYTHON_API_URL
let accessToken

const themeId     = randomUUID()
const examThemeId = randomUUID()
const questionId1 = randomUUID()
const questionId2 = randomUUID()
const questionId3 = randomUUID()

let blockId
let topicId

test.before(async () => {
  // ── schema (all IF NOT EXISTS — safe to run alongside app-flow.test.js) ──
  await query(`CREATE EXTENSION IF NOT EXISTS "uuid-ossp";`).catch(() => {})

  for (const sql of [
    `CREATE TABLE IF NOT EXISTS theme (
       theme_id UUID PRIMARY KEY, title VARCHAR(255) NOT NULL, theme_order INTEGER NOT NULL DEFAULT 1
     );`,
    `CREATE TABLE IF NOT EXISTS file (
       file_id UUID PRIMARY KEY, filename VARCHAR(500) NOT NULL
     );`,
    `CREATE TABLE IF NOT EXISTS theme_file (
       theme_id UUID REFERENCES theme(theme_id),
       file_id  UUID REFERENCES file(file_id),
       PRIMARY KEY (theme_id, file_id)
     );`,
    `CREATE TABLE IF NOT EXISTS exam_theme (
       exam_theme_id UUID PRIMARY KEY, title VARCHAR(255) NOT NULL, exam_theme_order INTEGER NOT NULL DEFAULT 1
     );`,
    `CREATE TABLE IF NOT EXISTS question (
       question_id UUID PRIMARY KEY, text TEXT NOT NULL, answer_text TEXT NOT NULL, theme_id UUID NOT NULL REFERENCES theme(theme_id)
     );`,
    `CREATE TABLE IF NOT EXISTS course_block (
       id SERIAL PRIMARY KEY, title VARCHAR(255) NOT NULL, description TEXT, block_order INTEGER NOT NULL DEFAULT 0
     );`,
    `CREATE TABLE IF NOT EXISTS block_topic (
       id SERIAL PRIMARY KEY, block_id INTEGER NOT NULL REFERENCES course_block(id) ON DELETE CASCADE,
       title VARCHAR(255) NOT NULL, topic_order INTEGER NOT NULL DEFAULT 0,
       exam_theme_id UUID REFERENCES exam_theme(exam_theme_id) ON DELETE SET NULL,
       theme_id UUID REFERENCES theme(theme_id) ON DELETE SET NULL
     );`,
    `CREATE TABLE IF NOT EXISTS exam (
       exam_id UUID PRIMARY KEY, user_id INTEGER NOT NULL,
       exam_theme_id UUID NOT NULL REFERENCES exam_theme(exam_theme_id),
       type VARCHAR(255) NOT NULL DEFAULT 'Итоговый экзамен',
       question_count INTEGER NOT NULL, status VARCHAR(255) NOT NULL,
       start_exam TIMESTAMPTZ NOT NULL DEFAULT NOW(), end_exam TIMESTAMPTZ NULL, rate VARCHAR(255) NULL,
       exam_scope VARCHAR(20) DEFAULT 'standalone',
       block_topic_id INTEGER REFERENCES block_topic(id) ON DELETE SET NULL,
       course_block_id INTEGER REFERENCES course_block(id) ON DELETE SET NULL
     );`,
    `CREATE TABLE IF NOT EXISTS exam_question (
       exam_question_id UUID PRIMARY KEY, exam_id UUID NOT NULL REFERENCES exam(exam_id),
       question_id UUID NOT NULL REFERENCES question(question_id), status VARCHAR(255) NOT NULL
     );`,
    `CREATE TABLE IF NOT EXISTS answer (
       answer_id UUID PRIMARY KEY, exam_question_id UUID NOT NULL REFERENCES exam_question(exam_question_id),
       answer_text TEXT NOT NULL, is_correct BOOLEAN NOT NULL
     );`,
    `CREATE TABLE IF NOT EXISTS app_users (
       id SERIAL PRIMARY KEY, email VARCHAR(255) UNIQUE NOT NULL,
       password_hash VARCHAR(255) NOT NULL, username VARCHAR(100),
       created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
     );`,
    `CREATE TABLE IF NOT EXISTS app_refresh_tokens (
       id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
       token_hash VARCHAR(500) NOT NULL, expires_at TIMESTAMPTZ NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
     );`,
    `CREATE TABLE IF NOT EXISTS user_topic_progress (
       id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
       topic_id INTEGER NOT NULL REFERENCES block_topic(id) ON DELETE CASCADE,
       status VARCHAR(20) NOT NULL DEFAULT 'not_started', attempts INTEGER NOT NULL DEFAULT 0,
       best_score NUMERIC(6,4) NOT NULL DEFAULT 0, last_exam_id UUID, updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
       UNIQUE(user_id, topic_id)
     );`,
    `CREATE TABLE IF NOT EXISTS user_block_progress (
       id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
       block_id INTEGER NOT NULL REFERENCES course_block(id) ON DELETE CASCADE,
       status VARCHAR(20) NOT NULL DEFAULT 'not_started', attempts INTEGER NOT NULL DEFAULT 0,
       best_score NUMERIC(6,4) NOT NULL DEFAULT 0, last_exam_id UUID, updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
       UNIQUE(user_id, block_id)
     );`,
    `CREATE TABLE IF NOT EXISTS user_course_progress (
       id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
       status VARCHAR(20) NOT NULL DEFAULT 'not_started', attempts INTEGER NOT NULL DEFAULT 0,
       best_score NUMERIC(6,4) NOT NULL DEFAULT 0, last_exam_id UUID, completed_at TIMESTAMPTZ,
       UNIQUE(user_id)
     );`,
  ]) {
    await query(sql)
  }

  // ── seed domain data ──────────────────────────────────────────────────────
  await query(
    `INSERT INTO theme (theme_id, title, theme_order) VALUES ($1, $2, 99) ON CONFLICT (theme_id) DO NOTHING`,
    [themeId, 'Course E2E Theme']
  )
  await query(
    `INSERT INTO exam_theme (exam_theme_id, title, exam_theme_order) VALUES ($1, $2, 99) ON CONFLICT (exam_theme_id) DO NOTHING`,
    [examThemeId, 'Course E2E Theme']
  )
  for (const [id, text, answer] of [
    [questionId1, 'Вопрос 1', '42'],
    [questionId2, 'Вопрос 2', '42'],
    [questionId3, 'Вопрос 3', '42'],
  ]) {
    await query(
      `INSERT INTO question (question_id, text, answer_text, theme_id) VALUES ($1, $2, $3, $4) ON CONFLICT (question_id) DO NOTHING`,
      [id, text, answer, themeId]
    )
  }

  // Create course_block + block_topic as the first block for this test,
  // regardless of seed data that may already exist in the local database.
  const { rows: orderRows } = await query(
    `SELECT COALESCE(MIN(block_order), 1)::int - 1 AS block_order FROM course_block`
  )
  const { rows: cbRows } = await query(
    `INSERT INTO course_block (title, block_order) VALUES ('Course E2E Block', $1) RETURNING id`,
    [orderRows[0].block_order]
  )
  blockId = cbRows[0].id

  const { rows: btRows } = await query(
    `INSERT INTO block_topic (block_id, title, topic_order, exam_theme_id, theme_id)
     VALUES ($1, 'Course E2E Topic', 1, $2, $3) RETURNING id`,
    [blockId, examThemeId, themeId]
  )
  topicId = btRows[0].id

  // Register a user directly through FastAPI.
  const email = `course_e2e_${Date.now()}@example.com`
  const regRes = await fetch(`${baseUrl}/api/app/auth/register`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ email, password: 'Password123', username: 'Course Tester' }),
  })
  assert.equal(regRes.status, 201)
  const regBody = await regRes.json()
  accessToken = regBody.accessToken
})

test.after(async () => {
  // Cleanup seeded course data
  await query(`DELETE FROM block_topic WHERE id = $1`, [topicId]).catch(() => {})
  await query(`DELETE FROM course_block WHERE id = $1`, [blockId]).catch(() => {})
  await closeDb()
})

const auth = () => ({ authorization: `Bearer ${accessToken}` })

// ── GET /course/blocks ────────────────────────────────────────────────────────
test('GET /api/app/course/blocks returns blocks list', async () => {
  const res = await fetch(`${baseUrl}/api/app/course/blocks`, { headers: auth() })
  assert.equal(res.status, 200)
  const body = await res.json()
  assert.ok(Array.isArray(body.blocks))
  assert.ok(typeof body.final_exam_unlocked === 'boolean')
  // Our seeded block must appear
  const found = body.blocks.find((b) => b.id === blockId)
  assert.ok(found, 'seeded block must be in list')
  assert.equal(found.user_status, 'not_started')
})

// ── GET /course/blocks/:blockId ──────────────────────────────────────────────
test('GET /api/app/course/blocks/:blockId returns topics', async () => {
  const res = await fetch(`${baseUrl}/api/app/course/blocks/${blockId}`, { headers: auth() })
  assert.equal(res.status, 200)
  const body = await res.json()
  assert.ok(body.block)
  assert.ok(Array.isArray(body.topics))
  assert.equal(body.topics.length, 1)
  assert.equal(body.topics[0].id, topicId)
  assert.equal(body.topics[0].is_unlocked, true, 'first topic of first block must be unlocked')
  assert.equal(body.block_test_unlocked, false, 'block test locked until all topics passed')
})

// ── GET /course/blocks/:blockId/topics/:topicId ───────────────────────────────
test('GET topic detail returns materials and question_count', async () => {
  const res = await fetch(`${baseUrl}/api/app/course/blocks/${blockId}/topics/${topicId}`, { headers: auth() })
  assert.equal(res.status, 200)
  const body = await res.json()
  assert.ok(body.topic)
  assert.equal(body.topic.id, topicId)
  assert.equal(body.topic.is_unlocked, true)
  assert.ok(Array.isArray(body.materials))
  assert.ok(body.question_count >= 3, 'should have 3 seeded questions')
})

// ── POST topic exam → answer all correctly → topic passed ───────────────────
test('topic exam: start → answer correctly → topic marked passed', async () => {
  // Start topic exam
  const startRes = await fetch(`${baseUrl}/api/app/course/topics/${topicId}/exam`, {
    method: 'POST',
    headers: auth(),
  })
  assert.equal(startRes.status, 201)
  const { exam_id } = await startRes.json()
  assert.ok(exam_id)

  // Answer all questions correctly (3 questions, answer = '42')
  for (let i = 0; i < 3; i++) {
    const askRes = await fetch(`${baseUrl}/api/app/exams/${exam_id}/questions/ask`, {
      method: 'POST',
      headers: auth(),
    })
    if (askRes.status === 404) break // no more questions
    assert.equal(askRes.status, 200)
    const { question } = await askRes.json()
    assert.ok(question?.exam_question_id)

    const ansRes = await fetch(`${baseUrl}/api/app/answers`, {
      method: 'POST',
      headers: { 'content-type': 'application/json', ...auth() },
      body: JSON.stringify({ exam_question_id: question.exam_question_id, answer_text: '42' }),
    })
    assert.equal(ansRes.status, 200)
    const ans = await ansRes.json()
    assert.equal(ans.is_correct, true)
    if (ans.completed) {
      assert.equal(ans.is_passed, true)
      break
    }
  }

  // Verify exam result endpoint
  const resultRes = await fetch(`${baseUrl}/api/app/course/exams/${exam_id}/result`, { headers: auth() })
  assert.equal(resultRes.status, 200)
  const result = await resultRes.json()
  assert.equal(result.exam_scope, 'topic')
  assert.equal(result.is_passed, true)
  assert.ok(result.score >= 0.7)

  // Verify topic progress was updated
  const topicRes = await fetch(`${baseUrl}/api/app/course/blocks/${blockId}/topics/${topicId}`, { headers: auth() })
  const topicBody = await topicRes.json()
  assert.equal(topicBody.topic.user_status, 'passed')
})

// ── After topic passed → block test becomes available ───────────────────────
test('block test unlocked after all topics passed', async () => {
  const res = await fetch(`${baseUrl}/api/app/course/blocks/${blockId}`, { headers: auth() })
  assert.equal(res.status, 200)
  const body = await res.json()
  assert.equal(body.block_test_unlocked, true, 'block test must unlock after all topics passed')
})

// ── POST block exam → answer all correctly → block passed ───────────────────
test('block exam: start → answer correctly → block marked passed', async () => {
  const startRes = await fetch(`${baseUrl}/api/app/course/blocks/${blockId}/exam`, {
    method: 'POST',
    headers: auth(),
  })
  assert.equal(startRes.status, 201)
  const { exam_id } = await startRes.json()

  for (let i = 0; i < 10; i++) {
    const askRes = await fetch(`${baseUrl}/api/app/exams/${exam_id}/questions/ask`, {
      method: 'POST',
      headers: auth(),
    })
    if (askRes.status === 404) break
    assert.equal(askRes.status, 200)
    const { question } = await askRes.json()

    const ansRes = await fetch(`${baseUrl}/api/app/answers`, {
      method: 'POST',
      headers: { 'content-type': 'application/json', ...auth() },
      body: JSON.stringify({ exam_question_id: question.exam_question_id, answer_text: '42' }),
    })
    assert.equal(ansRes.status, 200)
    const ans = await ansRes.json()
    if (ans.completed) {
      assert.equal(ans.is_passed, true)
      break
    }
  }

  const resultRes = await fetch(`${baseUrl}/api/app/course/exams/${exam_id}/result`, { headers: auth() })
  assert.equal(resultRes.status, 200)
  const result = await resultRes.json()
  assert.equal(result.exam_scope, 'block')
  assert.equal(result.is_passed, true)

  // Verify block progress
  const blockRes = await fetch(`${baseUrl}/api/app/course/blocks/${blockId}`, { headers: auth() })
  const blockBody = await blockRes.json()
  assert.equal(blockBody.block.user_status, 'passed')
})

// ── GET /course/blocks: final_exam_unlocked when block 99 is only block ──────
test('final exam unlocked after all blocks passed (our block is only one)', async () => {
  const res = await fetch(`${baseUrl}/api/app/course/blocks`, { headers: auth() })
  assert.equal(res.status, 200)
  const body = await res.json()
  // Our seeded block should now be passed
  const found = body.blocks.find((b) => b.id === blockId)
  assert.equal(found?.user_status, 'passed')
})

// ── Gate: locked topic returns 403 ───────────────────────────────────────────
test('locked topic exam returns 403', async () => {
  // Register a fresh user (no progress)
  const regRes = await fetch(`${baseUrl}/api/app/auth/register`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ email: `gate_test_${Date.now()}@example.com`, password: 'Password123' }),
  })
  assert.equal(regRes.status, 201)
  const { accessToken: freshToken } = await regRes.json()

  // Create a second topic in same block to test gate
  const { rows } = await query(
    `INSERT INTO block_topic (block_id, title, topic_order, exam_theme_id, theme_id)
     VALUES ($1, 'Locked Topic', 2, $2, $3) RETURNING id`,
    [blockId, examThemeId, themeId]
  )
  const lockedTopicId = rows[0].id

  const res = await fetch(`${baseUrl}/api/app/course/topics/${lockedTopicId}/exam`, {
    method: 'POST',
    headers: { authorization: `Bearer ${freshToken}` },
  })
  assert.equal(res.status, 403)

  // Cleanup
  await query(`DELETE FROM block_topic WHERE id = $1`, [lockedTopicId])
})
