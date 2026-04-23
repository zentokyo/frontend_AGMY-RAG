-- AGMY RAG Admin Panel — Additional tables for admin auth
-- These are appended to the existing "assistant" DB schema
-- (theme, file, theme_file, question tables already exist via Alembic)

CREATE TABLE IF NOT EXISTS admin_users (
  id            SERIAL PRIMARY KEY,
  email         VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  role          VARCHAR(50)  NOT NULL DEFAULT 'admin',
  created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS admin_refresh_tokens (
  id         SERIAL PRIMARY KEY,
  user_id    INT          NOT NULL REFERENCES admin_users(id) ON DELETE CASCADE,
  token_hash VARCHAR(500) NOT NULL,
  expires_at TIMESTAMPTZ  NOT NULL,
  created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_admin_refresh_tokens_user_id ON admin_refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_admin_refresh_tokens_hash    ON admin_refresh_tokens(token_hash);
