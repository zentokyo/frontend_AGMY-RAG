import { randomUUID } from 'node:crypto'
import { closeDb, query } from '../../../tests/api/db.js'

const themeId = randomUUID()
const examThemeId = randomUUID()
const questionId = randomUUID()

const THEME_TITLE = 'E2E UI Theme'
const QUESTION_TEXT = 'Сколько будет 6 * 7?'
const ANSWER_TEXT = '42'
const ADMIN_PASSWORD_HASH = '$2b$12$RIMUlCoyBiZ1SpzPVHYrkeh55RBU/LOX6oYJuFSAe7XQ6pkzQV7Om'

async function run() {
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
  await query(
    `INSERT INTO admin_users (email, password_hash, role)
     VALUES ('admin@example.com', $1, 'admin')
     ON CONFLICT (email)
     DO UPDATE SET password_hash = EXCLUDED.password_hash, role = 'admin'`,
    [ADMIN_PASSWORD_HASH]
  )

  await query(
    `INSERT INTO theme (theme_id, title, theme_order)
     VALUES ($1, $2, 9999)
     ON CONFLICT (theme_id) DO NOTHING`,
    [themeId, THEME_TITLE]
  )
  await query(
    `INSERT INTO exam_theme (exam_theme_id, title, exam_theme_order)
     VALUES ($1, $2, 9999)
     ON CONFLICT (exam_theme_id) DO NOTHING`,
    [examThemeId, THEME_TITLE]
  )
  await query(
    `INSERT INTO question (question_id, text, answer_text, theme_id)
     VALUES ($1, $2, $3, $4)
     ON CONFLICT (question_id) DO NOTHING`,
    [questionId, QUESTION_TEXT, ANSWER_TEXT, themeId]
  )

  console.log('[e2e:setup] seeded theme/question for UI tests')
}

run()
  .catch((err) => {
    console.error('[e2e:setup] failed:', err.message)
    process.exit(1)
  })
  .finally(async () => {
    await closeDb()
  })
