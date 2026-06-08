import asyncio
from pathlib import Path

import asyncpg
from alembic import command
from alembic.config import Config as AlembicConfig

from src.config import config

LEGACY_ALEMBIC_HEAD = "05eee169c8d0"
LEGACY_DOMAIN_TABLES = {
    "answer",
    "exam",
    "exam_question",
    "exam_theme",
    "file",
    "question",
    "theme",
    "theme_file",
}


async def _should_adopt_legacy_schema() -> bool:
    connection = await asyncpg.connect(
        host=config.postgres.host,
        port=config.postgres.port,
        user=config.postgres.user,
        password=config.postgres.password,
        database=config.postgres.db,
    )
    try:
        has_alembic_version_table = await connection.fetchval(
            "SELECT to_regclass('public.alembic_version') IS NOT NULL"
        )
        if has_alembic_version_table:
            current_revision = await connection.fetchval(
                "SELECT version_num FROM alembic_version LIMIT 1"
            )
            if current_revision:
                return False

        rows = await connection.fetch(
            """
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public' AND tablename = ANY($1::text[])
            """,
            list(LEGACY_DOMAIN_TABLES),
        )
        existing_tables = {row["tablename"] for row in rows}
    finally:
        await connection.close()

    if not existing_tables:
        return False
    if existing_tables != LEGACY_DOMAIN_TABLES:
        missing = ", ".join(sorted(LEGACY_DOMAIN_TABLES - existing_tables))
        raise RuntimeError(
            "Cannot adopt a partial legacy database schema. "
            f"Missing domain tables: {missing}"
        )
    return True


def _alembic_config() -> AlembicConfig:
    backend_dir = Path(__file__).resolve().parents[2]
    return AlembicConfig(str(backend_dir / "alembic.ini"))


def migrate() -> None:
    alembic_config = _alembic_config()
    should_adopt_legacy_schema = asyncio.run(_should_adopt_legacy_schema())
    _ensure_event_loop()

    if should_adopt_legacy_schema:
        command.stamp(alembic_config, LEGACY_ALEMBIC_HEAD, purge=True)
    command.upgrade(alembic_config, "head")


def _ensure_event_loop() -> None:
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())


def main() -> None:
    migrate()


if __name__ == "__main__":
    main()
