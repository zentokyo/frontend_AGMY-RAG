-- AGMY RAG Admin Panel — Initial Schema

CREATE TABLE IF NOT EXISTS users (
  id            SERIAL PRIMARY KEY,
  email         VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  role          VARCHAR(50)  NOT NULL DEFAULT 'admin',
  created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS refresh_tokens (
  id         SERIAL PRIMARY KEY,
  user_id    INT          NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token_hash VARCHAR(500) NOT NULL,
  expires_at TIMESTAMPTZ  NOT NULL,
  created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_hash    ON refresh_tokens(token_hash);

CREATE TABLE IF NOT EXISTS documents (
  id               SERIAL PRIMARY KEY,
  original_name    VARCHAR(500) NOT NULL,
  stored_filename  VARCHAR(500) NOT NULL UNIQUE,
  file_size        BIGINT,
  mime_type        VARCHAR(100),
  status           VARCHAR(50)  NOT NULL DEFAULT 'processing',
  error_message    TEXT,
  uploaded_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- status: processing | indexed | error

CREATE TABLE IF NOT EXISTS questions (
  id               SERIAL PRIMARY KEY,
  question_text    TEXT        NOT NULL,
  reference_answer TEXT        NOT NULL,
  category         VARCHAR(255),
  tags             TEXT[]      NOT NULL DEFAULT '{}',
  is_active        BOOLEAN     NOT NULL DEFAULT true,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_questions_category  ON questions(category);
CREATE INDEX IF NOT EXISTS idx_questions_is_active ON questions(is_active);

-- Auto-update updated_at on questions
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS questions_updated_at ON questions;
CREATE TRIGGER questions_updated_at
  BEFORE UPDATE ON questions
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();
