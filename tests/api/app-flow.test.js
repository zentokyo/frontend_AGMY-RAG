import test from 'node:test'
import assert from 'node:assert/strict'
import { randomUUID } from 'node:crypto'

process.env.CLIENT_ORIGIN = 'http://127.0.0.1:5174'
process.env.PYTHON_API_URL ||= 'http://127.0.0.1:8001'
process.env.INTERNAL_API_TOKEN ||= 'change-me-internal-token'
process.env.DB_HOST ||= '127.0.0.1'
process.env.DB_PORT ||= process.env.POSTGRES_PUBLISHED_PORT || '5433'
process.env.DB_NAME ||= process.env.POSTGRES_DB || 'assistant'
process.env.DB_USER ||= process.env.POSTGRES_USER || 'postgres'
process.env.DB_PASSWORD ||= process.env.POSTGRES_PASSWORD || 'example'

const { query, closeDb } = await import('./db.js')

const baseUrl = process.env.PYTHON_API_URL
let cookieJar = ''

const themeId = randomUUID()
const examThemeId = randomUUID()
const questionId = randomUUID()
const fileId = randomUUID()

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

async function waitFor(check, timeoutMs = 10000) {
  const deadline = Date.now() + timeoutMs
  let lastError
  while (Date.now() < deadline) {
    try {
      const value = await check()
      if (value) return value
    } catch (error) {
      lastError = error
    }
    await sleep(250)
  }
  if (lastError) throw lastError
  assert.fail('Timed out waiting for condition')
}

test.before(async () => {
  await query(`CREATE EXTENSION IF NOT EXISTS "uuid-ossp";`).catch(() => {})

  await query(`
    CREATE TABLE IF NOT EXISTS theme (
      theme_id UUID PRIMARY KEY,
      title VARCHAR(255) NOT NULL,
      theme_order INTEGER NOT NULL DEFAULT 1
    );
  `)
  await query(`
    CREATE TABLE IF NOT EXISTS exam_theme (
      exam_theme_id UUID PRIMARY KEY,
      title VARCHAR(255) NOT NULL,
      exam_theme_order INTEGER NOT NULL DEFAULT 1
    );
  `)
  await query(`
    CREATE TABLE IF NOT EXISTS question (
      question_id UUID PRIMARY KEY,
      text TEXT NOT NULL,
      answer_text TEXT NOT NULL,
      theme_id UUID NOT NULL REFERENCES theme(theme_id)
    );
  `)
  // Tables needed for course structure (referenced by FK from exam)
  await query(`
    CREATE TABLE IF NOT EXISTS file (
      file_id UUID PRIMARY KEY,
      filename VARCHAR(500) NOT NULL
    );
  `)
  await query(`
    CREATE TABLE IF NOT EXISTS theme_file (
      theme_id UUID REFERENCES theme(theme_id),
      file_id  UUID REFERENCES file(file_id),
      PRIMARY KEY (theme_id, file_id)
    );
  `)
  await query(`
    CREATE TABLE IF NOT EXISTS course_block (
      id          SERIAL PRIMARY KEY,
      title       VARCHAR(255) NOT NULL,
      description TEXT,
      block_order INTEGER NOT NULL DEFAULT 0
    );
  `)
  await query(`
    CREATE TABLE IF NOT EXISTS block_topic (
      id            SERIAL PRIMARY KEY,
      block_id      INTEGER NOT NULL REFERENCES course_block(id) ON DELETE CASCADE,
      title         VARCHAR(255) NOT NULL,
      topic_order   INTEGER NOT NULL DEFAULT 0,
      exam_theme_id UUID REFERENCES exam_theme(exam_theme_id) ON DELETE SET NULL,
      theme_id      UUID REFERENCES theme(theme_id) ON DELETE SET NULL
    );
  `)
  await query(`
    CREATE TABLE IF NOT EXISTS exam (
      exam_id         UUID PRIMARY KEY,
      user_id         INTEGER NOT NULL,
      exam_theme_id   UUID NOT NULL REFERENCES exam_theme(exam_theme_id),
      type            VARCHAR(255) NOT NULL DEFAULT 'Итоговый экзамен',
      question_count  INTEGER NOT NULL,
      status          VARCHAR(255) NOT NULL,
      start_exam      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      end_exam        TIMESTAMPTZ NULL,
      rate            VARCHAR(255) NULL,
      exam_scope      VARCHAR(20) DEFAULT 'standalone',
      block_topic_id  INTEGER REFERENCES block_topic(id) ON DELETE SET NULL,
      course_block_id INTEGER REFERENCES course_block(id) ON DELETE SET NULL
    );
  `)
  await query(`
    CREATE TABLE IF NOT EXISTS exam_question (
      exam_question_id UUID PRIMARY KEY,
      exam_id UUID NOT NULL REFERENCES exam(exam_id),
      question_id UUID NOT NULL REFERENCES question(question_id),
      status VARCHAR(255) NOT NULL
    );
  `)
  await query(`
    CREATE TABLE IF NOT EXISTS answer (
      answer_id UUID PRIMARY KEY,
      exam_question_id UUID NOT NULL REFERENCES exam_question(exam_question_id),
      answer_text TEXT NOT NULL,
      is_correct BOOLEAN,
      evaluation_status VARCHAR(32) NOT NULL DEFAULT 'done',
      evaluation_method VARCHAR(64),
      evaluation_error TEXT
    );
  `)
  await query(`ALTER TABLE answer ALTER COLUMN is_correct DROP NOT NULL`).catch(() => {})
  await query(`ALTER TABLE answer ADD COLUMN IF NOT EXISTS evaluation_status VARCHAR(32) NOT NULL DEFAULT 'done'`)
  await query(`ALTER TABLE answer ADD COLUMN IF NOT EXISTS evaluation_method VARCHAR(64)`)
  await query(`ALTER TABLE answer ADD COLUMN IF NOT EXISTS evaluation_error TEXT`)

  // Ensure schema required for /api/app/* exists.
  await query(`
    CREATE TABLE IF NOT EXISTS app_users (
      id SERIAL PRIMARY KEY,
      email VARCHAR(255) UNIQUE NOT NULL,
      password_hash VARCHAR(255) NOT NULL,
      username VARCHAR(100),
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
  `)
  await query(`
    CREATE TABLE IF NOT EXISTS app_refresh_tokens (
      id SERIAL PRIMARY KEY,
      user_id INTEGER NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
      token_hash VARCHAR(500) NOT NULL,
      expires_at TIMESTAMPTZ NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
  `)

  // Progress tables (after app_users to satisfy FK)
  await query(`
    CREATE TABLE IF NOT EXISTS user_topic_progress (
      id           SERIAL PRIMARY KEY,
      user_id      INTEGER NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
      topic_id     INTEGER NOT NULL REFERENCES block_topic(id) ON DELETE CASCADE,
      status       VARCHAR(20) NOT NULL DEFAULT 'not_started',
      attempts     INTEGER NOT NULL DEFAULT 0,
      best_score   NUMERIC(6,4) NOT NULL DEFAULT 0,
      last_exam_id UUID,
      updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      UNIQUE(user_id, topic_id)
    );
  `)
  await query(`
    CREATE TABLE IF NOT EXISTS user_block_progress (
      id           SERIAL PRIMARY KEY,
      user_id      INTEGER NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
      block_id     INTEGER NOT NULL REFERENCES course_block(id) ON DELETE CASCADE,
      status       VARCHAR(20) NOT NULL DEFAULT 'not_started',
      attempts     INTEGER NOT NULL DEFAULT 0,
      best_score   NUMERIC(6,4) NOT NULL DEFAULT 0,
      last_exam_id UUID,
      updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      UNIQUE(user_id, block_id)
    );
  `)
  await query(`
    CREATE TABLE IF NOT EXISTS user_course_progress (
      id           SERIAL PRIMARY KEY,
      user_id      INTEGER NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
      status       VARCHAR(20) NOT NULL DEFAULT 'not_started',
      attempts     INTEGER NOT NULL DEFAULT 0,
      best_score   NUMERIC(6,4) NOT NULL DEFAULT 0,
      last_exam_id UUID,
      completed_at TIMESTAMPTZ,
      UNIQUE(user_id)
    );
  `)

  // Seed minimal domain data for exam flow.
  await query(
    `INSERT INTO theme (theme_id, title, theme_order)
     VALUES ($1, $2, 1)
     ON CONFLICT (theme_id) DO NOTHING`,
    [themeId, 'E2E Theme']
  )
  await query(
    `INSERT INTO exam_theme (exam_theme_id, title, exam_theme_order)
     VALUES ($1, $2, 1)
     ON CONFLICT (exam_theme_id) DO NOTHING`,
    [examThemeId, 'E2E Theme']
  )
  await query(
    `INSERT INTO question (question_id, text, answer_text, theme_id)
     VALUES ($1, $2, $3, $4)
     ON CONFLICT (question_id) DO NOTHING`,
    [questionId, 'Какой ответ правильный?', '42', themeId]
  )
  await query(
    `INSERT INTO file (file_id, filename)
     VALUES ($1, $2)
     ON CONFLICT (file_id) DO NOTHING`,
    [fileId, 'e2e-theme-material.pdf']
  )
  await query(
    `INSERT INTO theme_file (theme_id, file_id)
     VALUES ($1, $2)
     ON CONFLICT (theme_id, file_id) DO NOTHING`,
    [themeId, fileId]
  )

})

test.after(async () => {
  await closeDb()
})

test('app auth register/login/me/refresh/logout flow', async () => {
  const email = `e2e_${Date.now()}@example.com`
  const password = 'Password123'

  const regRes = await fetch(`${baseUrl}/api/app/auth/register`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ email, password, username: 'E2E User' }),
  })
  assert.equal(regRes.status, 201)
  const setCookie = regRes.headers.get('set-cookie')
  assert.ok(setCookie)
  cookieJar = setCookie.split(';')[0]
  const regBody = await regRes.json()
  assert.ok(regBody.accessToken)
  assert.equal(regBody.user.email, email)

  const meRes = await fetch(`${baseUrl}/api/app/auth/me`, {
    headers: { authorization: `Bearer ${regBody.accessToken}` },
  })
  assert.equal(meRes.status, 200)

  const refreshRes = await fetch(`${baseUrl}/api/app/auth/refresh`, {
    method: 'POST',
    headers: { cookie: cookieJar },
  })
  assert.equal(refreshRes.status, 200)
  const refreshBody = await refreshRes.json()
  assert.ok(refreshBody.accessToken)

  const logoutRes = await fetch(`${baseUrl}/api/app/auth/logout`, {
    method: 'POST',
    headers: { cookie: cookieJar },
  })
  assert.equal(logoutRes.status, 200)
})

test('app exam -> ask -> answer -> stats flow', async () => {
  const email = `e2e_exam_${Date.now()}@example.com`
  const password = 'Password123'
  const regRes = await fetch(`${baseUrl}/api/app/auth/register`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ email, password, username: 'E2E Exam' }),
  })
  assert.equal(regRes.status, 201)
  const { accessToken } = await regRes.json()

  const themesRes = await fetch(`${baseUrl}/api/app/exam-themes`, {
    headers: { authorization: `Bearer ${accessToken}` },
  })
  assert.equal(themesRes.status, 200)
  const themes = await themesRes.json()
  assert.ok(Array.isArray(themes))
  assert.ok(themes.length > 0)

  const appThemesRes = await fetch(`${baseUrl}/api/app/themes`, {
    headers: { authorization: `Bearer ${accessToken}` },
  })
  assert.equal(appThemesRes.status, 200)
  const appThemes = await appThemesRes.json()
  const seededTheme = appThemes.find((theme) => theme.theme_id === themeId)
  assert.ok(seededTheme)
  assert.equal(seededTheme.file_count >= 1, true)

  const downloadRes = await fetch(`${baseUrl}/api/app/themes/${themeId}/download`, {
    headers: { authorization: `Bearer ${accessToken}` },
  })
  assert.equal(downloadRes.status, 200)
  const download = await downloadRes.json()
  assert.equal(download.theme_id, themeId)
  assert.equal(download.download_type, 'metadata')
  assert.equal(download.files.length >= 1, true)

  const createExamRes = await fetch(`${baseUrl}/api/app/exams`, {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify({ question_count: 1, exam_theme_id: examThemeId }),
  })
  assert.equal(createExamRes.status, 201)
  const exam = await createExamRes.json()
  assert.ok(exam.exam_id)

  const askRes = await fetch(`${baseUrl}/api/app/exams/${exam.exam_id}/questions/ask`, {
    method: 'POST',
    headers: { authorization: `Bearer ${accessToken}` },
  })
  assert.equal(askRes.status, 200)
  const ask = await askRes.json()
  assert.ok(ask.question?.exam_question_id)

  const answerRes = await fetch(`${baseUrl}/api/app/answers`, {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify({
      exam_question_id: ask.question.exam_question_id,
      answer_text: '42',
    }),
  })
  assert.equal(answerRes.status, 200)
  const answer = await answerRes.json()
  assert.equal(answer.answer_recorded, true)
  assert.equal(answer.evaluation_status, 'pending')
  assert.equal(answer.completed, true)
  assert.equal(answer.result_ready, false)

  const statsAllRes = await fetch(`${baseUrl}/api/app/stats/all`, {
    headers: { authorization: `Bearer ${accessToken}` },
  })
  assert.equal(statsAllRes.status, 200)
  const statsAll = await statsAllRes.json()
  assert.equal(statsAll.total_answers >= 1, true)

  const statsLast = await waitFor(async () => {
    const statsLastRes = await fetch(`${baseUrl}/api/app/stats/last`, {
      headers: { authorization: `Bearer ${accessToken}` },
    })
    if (statsLastRes.status !== 200) return null
    return statsLastRes.json()
  })
  assert.ok(Array.isArray(statsLast.answer_list))
})

test('FastAPI public app routes derive user from JWT and isolate admin access', async () => {
  const email = `direct_fastapi_${Date.now()}@example.com`

  const unauthRes = await fetch(`${baseUrl}/api/app/course/blocks`)
  assert.equal(unauthRes.status, 401)

  const registerRes = await fetch(`${baseUrl}/api/app/auth/register`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      email,
      password: 'Password123',
      username: 'Direct FastAPI',
    }),
  })
  assert.equal(registerRes.status, 201)
  const cookie = registerRes.headers.get('set-cookie')?.split(';')[0]
  assert.ok(cookie?.startsWith('appRefreshToken='))

  const registerBody = await registerRes.json()
  assert.ok(registerBody.accessToken)
  assert.equal(registerBody.refreshToken, undefined)

  const authHeaders = { authorization: `Bearer ${registerBody.accessToken}` }
  const meRes = await fetch(`${baseUrl}/api/app/auth/me`, { headers: authHeaders })
  assert.equal(meRes.status, 200)
  const me = await meRes.json()
  assert.equal(me.user.email, email)

  const courseRes = await fetch(`${baseUrl}/api/app/course/blocks`, { headers: authHeaders })
  assert.equal(courseRes.status, 200)
  const course = await courseRes.json()
  assert.ok(Array.isArray(course.blocks))

  const adminRes = await fetch(`${baseUrl}/api/questions`, { headers: authHeaders })
  assert.equal(adminRes.status, 403)

  const logoutRes = await fetch(`${baseUrl}/api/app/auth/logout`, {
    method: 'POST',
    headers: { cookie },
  })
  assert.equal(logoutRes.status, 200)
})
