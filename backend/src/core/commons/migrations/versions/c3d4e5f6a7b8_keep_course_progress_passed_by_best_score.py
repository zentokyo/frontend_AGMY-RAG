"""Keep course progress passed by best score.

Revision ID: c3d4e5f6a7b8
Revises: a1b2c3d4e5f6
Create Date: 2026-06-14
"""

from typing import Sequence, Union

from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
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
            UPDATE user_topic_progress
            SET status = 'passed',
                updated_at = NOW()
            WHERE best_score >= 0.7
              AND status <> 'passed'
            """,
            """
            UPDATE user_block_progress
            SET status = 'passed',
                updated_at = NOW()
            WHERE best_score >= 0.7
              AND status <> 'passed'
            """,
            """
            UPDATE user_course_progress
            SET status = 'passed',
                completed_at = COALESCE(completed_at, NOW())
            WHERE best_score >= 0.7
              AND status <> 'passed'
            """,
        )
    )


def downgrade() -> None:
    # This is a data repair migration. Do not re-lock users on downgrade.
    pass
