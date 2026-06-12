"""Add async answer evaluation status.

Revision ID: e4f6a8b0c2d4
Revises: c2d4e6f8a9b0
Create Date: 2026-06-12
"""

from typing import Sequence, Union

from alembic import op

revision: str = "e4f6a8b0c2d4"
down_revision: Union[str, Sequence[str], None] = "c2d4e6f8a9b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _execute_statements(statements: tuple[str, ...]) -> None:
    bind = op.get_bind()
    for statement in statements:
        bind.exec_driver_sql(statement)


def upgrade() -> None:
    _execute_statements(
        (
            "ALTER TABLE answer ALTER COLUMN is_correct DROP NOT NULL",
            """
            ALTER TABLE answer
              ADD COLUMN IF NOT EXISTS evaluation_status VARCHAR(32) NOT NULL DEFAULT 'done'
            """,
            """
            ALTER TABLE answer
              ADD COLUMN IF NOT EXISTS evaluation_method VARCHAR(64)
            """,
            """
            ALTER TABLE answer
              ADD COLUMN IF NOT EXISTS evaluation_error TEXT
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_answer_evaluation_status
              ON answer(evaluation_status)
            """,
        )
    )


def downgrade() -> None:
    _execute_statements(
        (
            "DROP INDEX IF EXISTS idx_answer_evaluation_status",
            "ALTER TABLE answer DROP COLUMN IF EXISTS evaluation_error",
            "ALTER TABLE answer DROP COLUMN IF EXISTS evaluation_method",
            "ALTER TABLE answer DROP COLUMN IF EXISTS evaluation_status",
            "UPDATE answer SET is_correct = FALSE WHERE is_correct IS NULL",
            "ALTER TABLE answer ALTER COLUMN is_correct SET NOT NULL",
        )
    )
