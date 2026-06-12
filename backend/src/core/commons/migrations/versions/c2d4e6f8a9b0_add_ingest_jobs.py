"""Add ingest job tracking.

Revision ID: c2d4e6f8a9b0
Revises: b7a9f2c1d3e4
Create Date: 2026-06-12
"""

from typing import Sequence, Union

from alembic import op

revision: str = "c2d4e6f8a9b0"
down_revision: Union[str, Sequence[str], None] = "b7a9f2c1d3e4"
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
            CREATE TABLE IF NOT EXISTS ingest_job (
              job_id UUID PRIMARY KEY,
              file_id UUID NOT NULL REFERENCES file(file_id) ON DELETE CASCADE,
              job_type VARCHAR(32) NOT NULL,
              status VARCHAR(32) NOT NULL DEFAULT 'queued',
              stage VARCHAR(64) NOT NULL DEFAULT 'queued',
              progress_percent INTEGER NOT NULL DEFAULT 0,
              attempt INTEGER NOT NULL DEFAULT 1,
              error TEXT,
              result JSONB,
              started_at TIMESTAMPTZ,
              finished_at TIMESTAMPTZ,
              created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
              updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_ingest_job_file_created
              ON ingest_job(file_id, created_at DESC)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_ingest_job_status
              ON ingest_job(status)
            """,
        )
    )


def downgrade() -> None:
    _execute_statements(
        (
            "DROP INDEX IF EXISTS idx_ingest_job_status",
            "DROP INDEX IF EXISTS idx_ingest_job_file_created",
            "DROP TABLE IF EXISTS ingest_job",
        )
    )
