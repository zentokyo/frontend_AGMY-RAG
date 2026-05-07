-- Course structure: blocks → topics → progress tracking

CREATE TABLE IF NOT EXISTS course_block (
  id          SERIAL PRIMARY KEY,
  title       VARCHAR(255) NOT NULL,
  description TEXT,
  block_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS block_topic (
  id            SERIAL PRIMARY KEY,
  block_id      INTEGER NOT NULL REFERENCES course_block(id) ON DELETE CASCADE,
  title         VARCHAR(255) NOT NULL,
  topic_order   INTEGER NOT NULL DEFAULT 0,
  exam_theme_id UUID REFERENCES exam_theme(exam_theme_id) ON DELETE SET NULL,
  theme_id      UUID REFERENCES theme(theme_id) ON DELETE SET NULL
);

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

-- Extend exam with course context (idempotent)
ALTER TABLE exam ADD COLUMN IF NOT EXISTS exam_scope      VARCHAR(20) DEFAULT 'standalone';
ALTER TABLE exam ADD COLUMN IF NOT EXISTS block_topic_id  INTEGER REFERENCES block_topic(id)  ON DELETE SET NULL;
ALTER TABLE exam ADD COLUMN IF NOT EXISTS course_block_id INTEGER REFERENCES course_block(id) ON DELETE SET NULL;

-- ─────────────────────────────────────────────────────────────
-- Seed: build default course structure from existing exam_themes
-- Groups exam_themes (sorted by exam_theme_order) into blocks of 5
-- Runs only when course_block is empty.
-- ─────────────────────────────────────────────────────────────
DO $$
DECLARE
  v_group_size INTEGER := 5;
  v_total      INTEGER;
  v_num_blocks INTEGER;
  i            INTEGER;
BEGIN
  IF EXISTS (SELECT 1 FROM course_block LIMIT 1) THEN
    RETURN;
  END IF;
  SELECT COUNT(*) INTO v_total FROM exam_theme;
  IF v_total = 0 THEN
    RETURN;
  END IF;
  v_num_blocks := CEIL(v_total::float / v_group_size)::int;
  FOR i IN 1..v_num_blocks LOOP
    INSERT INTO course_block (title, description, block_order)
    VALUES ('Блок ' || i, NULL, i);
  END LOOP;
END $$;

DO $$
DECLARE
  v_group_size INTEGER := 5;
  r            RECORD;
  v_block_id   INTEGER;
  v_row_num    INTEGER := 0;
BEGIN
  IF EXISTS (SELECT 1 FROM block_topic LIMIT 1) THEN
    RETURN;
  END IF;
  FOR r IN (
    SELECT exam_theme_id, title, exam_theme_order
    FROM exam_theme
    ORDER BY exam_theme_order ASC
  ) LOOP
    v_row_num := v_row_num + 1;
    SELECT id INTO v_block_id
    FROM course_block
    WHERE block_order = CEIL(v_row_num::float / v_group_size)::int;

    INSERT INTO block_topic (block_id, title, topic_order, exam_theme_id, theme_id)
    VALUES (
      v_block_id,
      r.title,
      ((v_row_num - 1) % v_group_size) + 1,
      r.exam_theme_id,
      (SELECT theme_id FROM theme WHERE title = r.title LIMIT 1)
    );
  END LOOP;
END $$;
