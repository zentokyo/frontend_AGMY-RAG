import argparse
import asyncio
import json
import logging
import os
import re
import unicodedata
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aiobotocore.session import get_session
from botocore.client import Config as ClientConfig
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from unidecode import unidecode

from src.config import config

logger = logging.getLogger(__name__)

DEFAULT_MANIFEST_PATH = Path(__file__).resolve().parents[1] / "core" / "rag" / "source_manifest.json"
DEFAULT_DOWNLOADS_DIR = Path(os.getenv("DOWNLOADS", "/Users/elvsevolod/Downloads"))
DEFAULT_KAF_EPID_DIR = Path(
    os.getenv("KAF_EPID", "/Users/elvsevolod/Desktop/Проект для АГМУ/Каф_эпид")
)
DEFAULT_REPO_THEME_FILES_DIR = Path(__file__).resolve().parents[3] / "theme_files"
DEFAULT_THEME_FILES_DIR = Path(
    os.getenv(
        "THEME_FILES",
        "/theme_files" if Path("/theme_files").exists() else str(DEFAULT_REPO_THEME_FILES_DIR),
    )
)
DEFAULT_UPLOAD_CONCURRENCY = int(os.getenv("RAG_SOURCE_MANIFEST_UPLOAD_CONCURRENCY", "4"))

CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
}


@dataclass(frozen=True)
class SourceEntry:
    theme_order: int
    theme_title: str
    source_path: Path
    filename: str
    content_type: str


@dataclass(frozen=True)
class SyncResult:
    total_sources: int
    uploaded_objects: int
    created_files: int
    updated_files: int
    linked_files: int
    dry_run: bool


async def sync_source_manifest(
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    downloads_dir: Path = DEFAULT_DOWNLOADS_DIR,
    kaf_epid_dir: Path = DEFAULT_KAF_EPID_DIR,
    theme_files_dir: Path = DEFAULT_THEME_FILES_DIR,
    upload_concurrency: int = DEFAULT_UPLOAD_CONCURRENCY,
    reset_existing: bool = False,
    dry_run: bool = False,
) -> SyncResult:
    entries = load_source_entries(
        manifest_path,
        downloads_dir=downloads_dir,
        kaf_epid_dir=kaf_epid_dir,
        theme_files_dir=theme_files_dir,
    )
    validate_entries(entries)

    unique_uploads = _unique_entries_by_filename(entries)
    if dry_run:
        for entry in entries:
            logger.info(
                "DRY-RUN source: block=%d filename=%s path=%s",
                entry.theme_order,
                entry.filename,
                entry.source_path,
            )
        return SyncResult(
            total_sources=len(entries),
            uploaded_objects=len(unique_uploads),
            created_files=0,
            updated_files=0,
            linked_files=0,
            dry_run=True,
        )

    await _upload_entries_to_s3(unique_uploads, concurrency=upload_concurrency)
    created_files, updated_files, linked_files = await _sync_entries_to_sql(entries, reset_existing=reset_existing)
    result = SyncResult(
        total_sources=len(entries),
        uploaded_objects=len(unique_uploads),
        created_files=created_files,
        updated_files=updated_files,
        linked_files=linked_files,
        dry_run=False,
    )
    logger.info(
        "Source manifest sync finished: sources=%d uploaded=%d created=%d updated=%d linked=%d",
        result.total_sources,
        result.uploaded_objects,
        result.created_files,
        result.updated_files,
        result.linked_files,
    )
    return result


def load_source_entries(
    manifest_path: Path,
    downloads_dir: Path = DEFAULT_DOWNLOADS_DIR,
    kaf_epid_dir: Path = DEFAULT_KAF_EPID_DIR,
    theme_files_dir: Path = DEFAULT_THEME_FILES_DIR,
) -> list[SourceEntry]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    raw_sources = manifest.get("sources")
    if not isinstance(raw_sources, list):
        raise ValueError("source_manifest must contain a 'sources' list")

    entries = [
        _source_entry(
            raw_source,
            downloads_dir=downloads_dir,
            kaf_epid_dir=kaf_epid_dir,
            theme_files_dir=theme_files_dir,
        )
        for raw_source in raw_sources
    ]
    _validate_unique_manifest_keys(entries)
    return entries


def validate_entries(entries: list[SourceEntry]) -> None:
    missing_paths = [entry.source_path for entry in entries if not entry.source_path.is_file()]
    if missing_paths:
        formatted = "\n".join(f"- {path}" for path in missing_paths)
        raise FileNotFoundError(f"Source manifest contains missing files:\n{formatted}")

    unsupported = [entry for entry in entries if Path(entry.filename).suffix.lower() not in CONTENT_TYPES]
    if unsupported:
        formatted = "\n".join(f"- {entry.filename}" for entry in unsupported)
        raise ValueError(f"Source manifest contains unsupported file extensions:\n{formatted}")


def _source_entry(
    raw_source: dict[str, Any],
    downloads_dir: Path,
    kaf_epid_dir: Path,
    theme_files_dir: Path,
) -> SourceEntry:
    try:
        theme_order = int(raw_source["theme_order"])
        theme_title = str(raw_source["theme_title"]).strip()
        raw_path = str(raw_source["path"])
    except KeyError as exc:
        raise ValueError(f"Source manifest entry is missing required field: {exc.args[0]}") from exc

    source_path = _resolve_manifest_path(
        raw_path,
        downloads_dir=downloads_dir,
        kaf_epid_dir=kaf_epid_dir,
        theme_files_dir=theme_files_dir,
    )
    filename = str(raw_source.get("filename") or _to_ascii_filename(source_path.name)).strip()
    if not filename:
        raise ValueError(f"Source manifest entry has an empty filename: {raw_source}")

    content_type = str(raw_source.get("content_type") or _content_type_for(filename))
    return SourceEntry(
        theme_order=theme_order,
        theme_title=theme_title,
        source_path=source_path,
        filename=filename,
        content_type=content_type,
    )


def _resolve_manifest_path(raw_path: str, downloads_dir: Path, kaf_epid_dir: Path, theme_files_dir: Path) -> Path:
    path = (
        raw_path.replace("${DOWNLOADS}", str(downloads_dir))
        .replace("${KAF_EPID}", str(kaf_epid_dir))
        .replace("${THEME_FILES}", str(theme_files_dir))
    )
    resolved = Path(os.path.expandvars(path)).expanduser()
    if resolved.exists():
        return resolved
    return _find_normalized_path(resolved)


def _find_normalized_path(path: Path) -> Path:
    parent = path.parent
    if not parent.is_dir():
        return path

    target_name = unicodedata.normalize("NFC", path.name)
    for child in parent.iterdir():
        if unicodedata.normalize("NFC", child.name) == target_name:
            return child
    return path


def _validate_unique_manifest_keys(entries: list[SourceEntry]) -> None:
    seen: set[tuple[int, str]] = set()
    duplicates: list[tuple[int, str]] = []
    for entry in entries:
        key = (entry.theme_order, entry.filename)
        if key in seen:
            duplicates.append(key)
        seen.add(key)

    if duplicates:
        formatted = "\n".join(f"- block={theme_order} filename={filename}" for theme_order, filename in duplicates)
        raise ValueError(f"Source manifest contains duplicate block/filename pairs:\n{formatted}")


def _unique_entries_by_filename(entries: list[SourceEntry]) -> list[SourceEntry]:
    unique: dict[str, SourceEntry] = {}
    for entry in entries:
        existing = unique.get(entry.filename)
        if existing and existing.source_path != entry.source_path:
            raise ValueError(
                "Source manifest maps the same storage filename to different source files: "
                f"{entry.filename}"
            )
        unique.setdefault(entry.filename, entry)
    return list(unique.values())


async def _upload_entries_to_s3(entries: list[SourceEntry], concurrency: int) -> None:
    semaphore = asyncio.Semaphore(max(1, concurrency))
    s3_session = get_session()
    async with s3_session.create_client(
        "s3",
        endpoint_url=config.minio.s3_url,
        aws_access_key_id=config.minio.user,
        aws_secret_access_key=config.minio.password,
        region_name="us-east-1",
        config=ClientConfig(connect_timeout=50, read_timeout=120),
    ) as s3_client:
        tasks = [
            asyncio.create_task(_upload_entry_to_s3(s3_client, entry, semaphore))
            for entry in entries
        ]
        await asyncio.gather(*tasks)


async def _upload_entry_to_s3(s3_client: Any, entry: SourceEntry, semaphore: asyncio.Semaphore) -> None:
    async with semaphore:
        data = await asyncio.to_thread(entry.source_path.read_bytes)
        await s3_client.put_object(
            Bucket=config.minio.bucket,
            Key=entry.filename,
            Body=data,
            ContentType=entry.content_type,
            Metadata={"source_manifest": "true"},
        )
        logger.info("Uploaded source object: %s <- %s", entry.filename, entry.source_path)


async def _sync_entries_to_sql(entries: list[SourceEntry], reset_existing: bool) -> tuple[int, int, int]:
    engine = create_async_engine(config.postgres.db_url, echo=False)
    created_files = 0
    updated_files = 0
    linked_files = 0
    try:
        async with engine.begin() as connection:
            for entry in entries:
                theme_id = await _ensure_theme(connection, entry.theme_order, entry.theme_title)
                file_id = await _find_file_for_theme(connection, theme_id, entry.filename)
                if file_id:
                    if reset_existing:
                        await _reset_existing_file(connection, file_id, entry)
                        updated_files += 1
                    else:
                        await _update_existing_file_metadata(connection, file_id, entry)
                else:
                    file_id = str(uuid.uuid4())
                    await _insert_file(connection, file_id, entry)
                    created_files += 1

                linked = await _ensure_theme_file(connection, theme_id, file_id)
                linked_files += 1 if linked else 0
    finally:
        await engine.dispose()
    return created_files, updated_files, linked_files


async def _ensure_theme(connection: Any, theme_order: int, theme_title: str) -> str:
    result = await connection.execute(
        text(
            """
            SELECT theme_id, title
            FROM theme
            WHERE title = :theme_title
            ORDER BY theme_order ASC, theme_id ASC
            LIMIT 1
            """
        ),
        {"theme_title": theme_title},
    )
    row = result.mappings().first()
    if row:
        await connection.execute(
            text(
                """
                UPDATE theme
                SET theme_order = :theme_order
                WHERE theme_id = CAST(:theme_id AS uuid)
                  AND theme_order IS DISTINCT FROM :theme_order
                """
            ),
            {"theme_id": str(row["theme_id"]), "theme_order": theme_order},
        )
        return str(row["theme_id"])

    theme_id = str(uuid.uuid4())
    await connection.execute(
        text(
            """
            INSERT INTO theme (theme_id, title, theme_order)
            VALUES (CAST(:theme_id AS uuid), :title, :theme_order)
            """
        ),
        {"theme_id": theme_id, "title": theme_title, "theme_order": theme_order},
    )
    logger.info("Created missing theme from manifest: block=%d title=%s", theme_order, theme_title)
    return theme_id


async def _find_file_for_theme(connection: Any, theme_id: str, filename: str) -> str | None:
    result = await connection.execute(
        text(
            """
            SELECT f.file_id
            FROM file f
            JOIN theme_file tf ON tf.file_id = f.file_id
            WHERE tf.theme_id = CAST(:theme_id AS uuid)
              AND f.filename = :filename
            ORDER BY f.created_at NULLS LAST, f.file_id
            LIMIT 1
            """
        ),
        {"theme_id": theme_id, "filename": filename},
    )
    row = result.mappings().first()
    return str(row["file_id"]) if row else None


async def _reset_existing_file(connection: Any, file_id: str, entry: SourceEntry) -> None:
    await connection.execute(
        text(
            """
            UPDATE file
            SET content_type = :content_type,
                ingest_status = 'uploaded',
                ingest_error = NULL,
                indexed_chunks = 0,
                indexed_at = NULL
            WHERE file_id = CAST(:file_id AS uuid)
            """
        ),
        {"file_id": file_id, "content_type": entry.content_type},
    )


async def _update_existing_file_metadata(connection: Any, file_id: str, entry: SourceEntry) -> None:
    await connection.execute(
        text(
            """
            UPDATE file
            SET content_type = :content_type
            WHERE file_id = CAST(:file_id AS uuid)
              AND content_type IS DISTINCT FROM :content_type
            """
        ),
        {"file_id": file_id, "content_type": entry.content_type},
    )


async def _insert_file(connection: Any, file_id: str, entry: SourceEntry) -> None:
    await connection.execute(
        text(
            """
            INSERT INTO file (
                file_id,
                filename,
                content_type,
                ingest_status,
                ingest_error,
                indexed_chunks,
                indexed_at,
                created_at
            )
            VALUES (
                CAST(:file_id AS uuid),
                :filename,
                :content_type,
                'uploaded',
                NULL,
                0,
                NULL,
                NOW()
            )
            """
        ),
        {"file_id": file_id, "filename": entry.filename, "content_type": entry.content_type},
    )


async def _ensure_theme_file(connection: Any, theme_id: str, file_id: str) -> bool:
    result = await connection.execute(
        text(
            """
            INSERT INTO theme_file (theme_id, file_id)
            VALUES (CAST(:theme_id AS uuid), CAST(:file_id AS uuid))
            ON CONFLICT DO NOTHING
            RETURNING file_id
            """
        ),
        {"theme_id": theme_id, "file_id": file_id},
    )
    return result.mappings().first() is not None


def _content_type_for(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    try:
        return CONTENT_TYPES[ext]
    except KeyError as exc:
        raise ValueError(f"Unsupported source file extension: {filename}") from exc


def _to_ascii_filename(filename: str) -> str:
    source = Path(filename or "document")
    ext = source.suffix.lower()
    basename = source.name[: -len(source.suffix)] if source.suffix else source.name
    ascii_name = unidecode(basename).lower()
    safe_name = re.sub(r"[^a-z0-9._-]", "_", ascii_name).strip("_")
    return f"{safe_name or 'document'}{ext}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync curated source_manifest documents into SQL and MinIO")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST_PATH,
        help="Path to source_manifest.json",
    )
    parser.add_argument(
        "--downloads-dir",
        type=Path,
        default=DEFAULT_DOWNLOADS_DIR,
        help="Directory used for ${DOWNLOADS} manifest paths",
    )
    parser.add_argument(
        "--kaf-epid-dir",
        type=Path,
        default=DEFAULT_KAF_EPID_DIR,
        help="Directory used for ${KAF_EPID} manifest paths",
    )
    parser.add_argument(
        "--theme-files-dir",
        type=Path,
        default=DEFAULT_THEME_FILES_DIR,
        help="Directory used for ${THEME_FILES} manifest paths",
    )
    parser.add_argument(
        "--upload-concurrency",
        type=int,
        default=DEFAULT_UPLOAD_CONCURRENCY,
        help="Maximum number of source objects to upload to MinIO in parallel",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and print the manifest without uploading to MinIO or changing SQL",
    )
    parser.add_argument(
        "--reset-existing",
        action="store_true",
        help="Reset existing source files back to uploaded so a later reindex can rebuild them",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    result = asyncio.run(
        sync_source_manifest(
            manifest_path=args.manifest,
            downloads_dir=args.downloads_dir,
            kaf_epid_dir=args.kaf_epid_dir,
            theme_files_dir=args.theme_files_dir,
            upload_concurrency=args.upload_concurrency,
            reset_existing=args.reset_existing,
            dry_run=args.dry_run,
        )
    )
    logger.info("[SUCCESS] Source manifest sync result: %s", result)


if __name__ == "__main__":
    main()
