"""Add web authentication and course schema.

Revision ID: 8f3c2a1b7d90
Revises: 05eee169c8d0
Create Date: 2026-06-05
"""

from typing import Sequence, Union

from alembic import op

revision: str = "8f3c2a1b7d90"
down_revision: Union[str, Sequence[str], None] = "05eee169c8d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _execute_statements(statements: tuple[str, ...]) -> None:
    bind = op.get_bind()
    for statement in statements:
        bind.exec_driver_sql(statement)


def upgrade() -> None:
    _execute_statements(
        (
            """
        CREATE TABLE IF NOT EXISTS admin_users (
          id            SERIAL PRIMARY KEY,
          email         VARCHAR(255) UNIQUE NOT NULL,
          password_hash VARCHAR(255) NOT NULL,
          role          VARCHAR(50) NOT NULL DEFAULT 'admin',
          created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,
            """
        CREATE TABLE IF NOT EXISTS admin_refresh_tokens (
          id         SERIAL PRIMARY KEY,
          user_id    INTEGER NOT NULL REFERENCES admin_users(id) ON DELETE CASCADE,
          token_hash VARCHAR(500) NOT NULL,
          expires_at TIMESTAMPTZ NOT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,
            """
        CREATE INDEX IF NOT EXISTS idx_admin_refresh_tokens_user_id
          ON admin_refresh_tokens(user_id)
        """,
            """
        CREATE INDEX IF NOT EXISTS idx_admin_refresh_tokens_hash
          ON admin_refresh_tokens(token_hash)
        """,
            """
        CREATE TABLE IF NOT EXISTS app_users (
          id            SERIAL PRIMARY KEY,
          email         VARCHAR(255) UNIQUE NOT NULL,
          password_hash VARCHAR(255) NOT NULL,
          username      VARCHAR(100),
          created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,
            """
        CREATE INDEX IF NOT EXISTS idx_app_users_email ON app_users(email)
        """,
            """
        CREATE TABLE IF NOT EXISTS app_refresh_tokens (
          id         SERIAL PRIMARY KEY,
          user_id    INTEGER NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
          token_hash VARCHAR(500) NOT NULL,
          expires_at TIMESTAMPTZ NOT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,
            """
        CREATE INDEX IF NOT EXISTS idx_app_refresh_tokens_user_id
          ON app_refresh_tokens(user_id)
        """,
            """
        CREATE INDEX IF NOT EXISTS idx_app_refresh_tokens_hash
          ON app_refresh_tokens(token_hash)
        """,
            """
        CREATE OR REPLACE FUNCTION update_app_users_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
          NEW.updated_at = NOW();
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """,
            """
        DROP TRIGGER IF EXISTS trigger_update_app_users_updated_at ON app_users
        """,
            """
        CREATE TRIGGER trigger_update_app_users_updated_at
          BEFORE UPDATE ON app_users
          FOR EACH ROW
          EXECUTE FUNCTION update_app_users_updated_at()
        """,
            """
        CREATE TABLE IF NOT EXISTS course_block (
          id          SERIAL PRIMARY KEY,
          title       VARCHAR(255) NOT NULL,
          description TEXT,
          block_order INTEGER NOT NULL DEFAULT 0
        )
        """,
            """
        CREATE TABLE IF NOT EXISTS block_topic (
          id            SERIAL PRIMARY KEY,
          block_id      INTEGER NOT NULL REFERENCES course_block(id) ON DELETE CASCADE,
          title         VARCHAR(255) NOT NULL,
          topic_order   INTEGER NOT NULL DEFAULT 0,
          exam_theme_id UUID REFERENCES exam_theme(exam_theme_id) ON DELETE SET NULL,
          theme_id      UUID REFERENCES theme(theme_id) ON DELETE SET NULL
        )
        """,
            """
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
        )
        """,
            """
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
        )
        """,
            """
        CREATE TABLE IF NOT EXISTS user_course_progress (
          id           SERIAL PRIMARY KEY,
          user_id      INTEGER NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
          status       VARCHAR(20) NOT NULL DEFAULT 'not_started',
          attempts     INTEGER NOT NULL DEFAULT 0,
          best_score   NUMERIC(6,4) NOT NULL DEFAULT 0,
          last_exam_id UUID,
          completed_at TIMESTAMPTZ,
          UNIQUE(user_id)
        )
        """,
            """
        ALTER TABLE exam
          ADD COLUMN IF NOT EXISTS exam_scope VARCHAR(20) DEFAULT 'standalone'
        """,
            """
        ALTER TABLE exam
          ADD COLUMN IF NOT EXISTS block_topic_id INTEGER
          REFERENCES block_topic(id) ON DELETE SET NULL
        """,
            """
        ALTER TABLE exam
          ADD COLUMN IF NOT EXISTS course_block_id INTEGER
          REFERENCES course_block(id) ON DELETE SET NULL
        """,
        )
    )

    _execute_statements(
        (
            """
        DO $$
        DECLARE
          group_size INTEGER := 5;
          total_themes INTEGER;
          block_count INTEGER;
          block_number INTEGER;
        BEGIN
          IF EXISTS (SELECT 1 FROM course_block LIMIT 1) THEN
            RETURN;
          END IF;

          SELECT COUNT(*) INTO total_themes FROM exam_theme;
          IF total_themes = 0 THEN
            RETURN;
          END IF;

          block_count := CEIL(total_themes::float / group_size)::int;
          FOR block_number IN 1..block_count LOOP
            INSERT INTO course_block (title, description, block_order)
            VALUES ('Блок ' || block_number, NULL, block_number);
          END LOOP;
        END $$
        """,
            """
        DO $$
        DECLARE
          group_size INTEGER := 5;
          exam_theme_row RECORD;
          target_block_id INTEGER;
          row_number INTEGER := 0;
        BEGIN
          IF EXISTS (SELECT 1 FROM block_topic LIMIT 1) THEN
            RETURN;
          END IF;

          FOR exam_theme_row IN (
            SELECT exam_theme_id, title, exam_theme_order
            FROM exam_theme
            ORDER BY exam_theme_order ASC
          ) LOOP
            row_number := row_number + 1;
            SELECT id INTO target_block_id
            FROM course_block
            WHERE block_order = CEIL(row_number::float / group_size)::int;

            INSERT INTO block_topic (
              block_id,
              title,
              topic_order,
              exam_theme_id,
              theme_id
            )
            VALUES (
              target_block_id,
              exam_theme_row.title,
              ((row_number - 1) % group_size) + 1,
              exam_theme_row.exam_theme_id,
              (SELECT theme_id FROM theme WHERE title = exam_theme_row.title LIMIT 1)
            );
          END LOOP;
        END $$
        """,
        )
    )


def downgrade() -> None:
    _execute_statements(
        (
            "ALTER TABLE exam DROP COLUMN IF EXISTS course_block_id",
            "ALTER TABLE exam DROP COLUMN IF EXISTS block_topic_id",
            "ALTER TABLE exam DROP COLUMN IF EXISTS exam_scope",
            "DROP TABLE IF EXISTS user_course_progress",
            "DROP TABLE IF EXISTS user_block_progress",
            "DROP TABLE IF EXISTS user_topic_progress",
            "DROP TABLE IF EXISTS block_topic",
            "DROP TABLE IF EXISTS course_block",
            "DROP TRIGGER IF EXISTS trigger_update_app_users_updated_at ON app_users",
            "DROP FUNCTION IF EXISTS update_app_users_updated_at()",
            "DROP TABLE IF EXISTS app_refresh_tokens",
            "DROP TABLE IF EXISTS app_users",
            "DROP TABLE IF EXISTS admin_refresh_tokens",
            "DROP TABLE IF EXISTS admin_users",
        )
    )
