"""Add file ingest status columns.

Revision ID: b7a9f2c1d3e4
Revises: 8f3c2a1b7d90
Create Date: 2026-06-11
"""

from typing import Sequence, Union

from alembic import op

revision: str = "b7a9f2c1d3e4"
down_revision: Union[str, Sequence[str], None] = "8f3c2a1b7d90"
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
            ALTER TABLE file
              ADD COLUMN IF NOT EXISTS content_type VARCHAR(255) NOT NULL DEFAULT 'application/octet-stream'
            """,
            """
            ALTER TABLE file
              ADD COLUMN IF NOT EXISTS ingest_status VARCHAR(32) NOT NULL DEFAULT 'uploaded'
            """,
            """
            ALTER TABLE file
              ADD COLUMN IF NOT EXISTS ingest_error TEXT
            """,
            """
            ALTER TABLE file
              ADD COLUMN IF NOT EXISTS indexed_chunks INTEGER NOT NULL DEFAULT 0
            """,
            """
            ALTER TABLE file
              ADD COLUMN IF NOT EXISTS indexed_at TIMESTAMPTZ
            """,
            """
            ALTER TABLE file
              ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_file_ingest_status
              ON file(ingest_status)
            """,
        )
    )


def downgrade() -> None:
    _execute_statements(
        (
            "DROP INDEX IF EXISTS idx_file_ingest_status",
            "ALTER TABLE file DROP COLUMN IF EXISTS created_at",
            "ALTER TABLE file DROP COLUMN IF EXISTS indexed_at",
            "ALTER TABLE file DROP COLUMN IF EXISTS indexed_chunks",
            "ALTER TABLE file DROP COLUMN IF EXISTS ingest_error",
            "ALTER TABLE file DROP COLUMN IF EXISTS ingest_status",
            "ALTER TABLE file DROP COLUMN IF EXISTS content_type",
        )
    )
