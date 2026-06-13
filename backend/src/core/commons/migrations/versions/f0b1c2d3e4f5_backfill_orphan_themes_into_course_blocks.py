"""Backfill orphan knowledge themes into course blocks.

Revision ID: f0b1c2d3e4f5
Revises: e4f6a8b0c2d4
Create Date: 2026-06-14
"""

from typing import Sequence, Union

from alembic import op

revision: str = "f0b1c2d3e4f5"
down_revision: Union[str, Sequence[str], None] = "e4f6a8b0c2d4"
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
            DO $$
            DECLARE
              target_block_id INTEGER;
              next_block_order INTEGER;
            BEGIN
              IF NOT EXISTS (
                SELECT 1
                FROM theme t
                WHERE NOT EXISTS (
                  SELECT 1
                  FROM block_topic bt
                  WHERE bt.theme_id = t.theme_id
                )
              ) THEN
                RETURN;
              END IF;

              SELECT id INTO target_block_id
              FROM course_block
              WHERE title = 'Нераспределённые темы'
              ORDER BY block_order ASC
              LIMIT 1;

              IF target_block_id IS NULL THEN
                SELECT COALESCE(MAX(block_order), 0) + 1
                INTO next_block_order
                FROM course_block;

                INSERT INTO course_block (title, description, block_order)
                VALUES (
                  'Нераспределённые темы',
                  'Темы, созданные до обязательной привязки к блоку',
                  next_block_order
                )
                RETURNING id INTO target_block_id;
              END IF;

              WITH orphan_themes AS (
                SELECT
                  t.theme_id,
                  t.title,
                  ROW_NUMBER() OVER (ORDER BY t.theme_order ASC, t.title ASC, t.theme_id ASC) AS rn
                FROM theme t
                WHERE NOT EXISTS (
                  SELECT 1
                  FROM block_topic bt
                  WHERE bt.theme_id = t.theme_id
                )
              ),
              base_order AS (
                SELECT COALESCE(MAX(topic_order), 0) AS value
                FROM block_topic
                WHERE block_id = target_block_id
              )
              INSERT INTO block_topic (block_id, title, topic_order, exam_theme_id, theme_id)
              SELECT
                target_block_id,
                ot.title,
                bo.value + ot.rn,
                (
                  SELECT et.exam_theme_id
                  FROM exam_theme et
                  WHERE et.title = ot.title
                  ORDER BY et.exam_theme_order ASC
                  LIMIT 1
                ),
                ot.theme_id
              FROM orphan_themes ot
              CROSS JOIN base_order bo;
            END $$
            """,
        )
    )


def downgrade() -> None:
    # Keep admin-created course structure intact on downgrade.
    pass
