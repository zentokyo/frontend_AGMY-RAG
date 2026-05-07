-- Domain tables normally managed by Alembic (Python).
-- Created here as IF NOT EXISTS so Node.js migrations are self-contained.
-- Running these on a DB that already has Alembic-managed tables is safe.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS theme (
  theme_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title       VARCHAR(255) NOT NULL,
  theme_order INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS file (
  file_id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  filename VARCHAR(500) NOT NULL
);

CREATE TABLE IF NOT EXISTS theme_file (
  theme_id UUID NOT NULL REFERENCES theme(theme_id) ON DELETE CASCADE,
  file_id  UUID NOT NULL REFERENCES file(file_id)  ON DELETE CASCADE,
  PRIMARY KEY (theme_id, file_id)
);

CREATE TABLE IF NOT EXISTS exam_theme (
  exam_theme_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title            VARCHAR(255) NOT NULL,
  exam_theme_order INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS question (
  question_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  theme_id    UUID NOT NULL REFERENCES theme(theme_id) ON DELETE CASCADE,
  text        TEXT NOT NULL,
  answer_text TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS exam (
  exam_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         INTEGER NOT NULL,
  exam_theme_id   UUID NOT NULL REFERENCES exam_theme(exam_theme_id),
  type            VARCHAR(255) NOT NULL DEFAULT 'Итоговый экзамен',
  question_count  INTEGER NOT NULL,
  status          VARCHAR(255) NOT NULL,
  start_exam      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  end_exam        TIMESTAMPTZ,
  rate            VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS exam_question (
  exam_question_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  exam_id          UUID NOT NULL REFERENCES exam(exam_id) ON DELETE CASCADE,
  question_id      UUID NOT NULL REFERENCES question(question_id),
  status           VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS answer (
  answer_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  exam_question_id UUID NOT NULL REFERENCES exam_question(exam_question_id) ON DELETE CASCADE,
  answer_text      TEXT NOT NULL,
  is_correct       BOOLEAN NOT NULL
);
