import asyncio
from collections import Counter
import json
import logging
import os
import time
from typing import Any

from aiobotocore.client import AioBaseClient
from aiobotocore.session import get_session as get_s3_session
from anyio import to_thread
from botocore.client import Config as ClientConfig
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from src.config import config
from src.core.rag.document_ingestion import (
    DocumentExtractionError,
    extract_documents,
    prepare_documents_for_chunking,
)
from src.core.rag.ingest import GigaChatEmbeddings, split_text
from src.core.rag.qdrant_store import QdrantKnowledgeStore

logger = logging.getLogger(__name__)

UPLOAD_INDEX_CONCURRENCY = int(os.getenv("RAG_UPLOAD_INDEX_CONCURRENCY", "2"))
INGEST_WORKER_BATCH_SIZE = int(os.getenv("RAG_INGEST_WORKER_BATCH_SIZE", str(UPLOAD_INDEX_CONCURRENCY)))
INGEST_WORKER_POLL_SECONDS = float(os.getenv("RAG_INGEST_WORKER_POLL_SECONDS", "3"))
INGEST_STALE_AFTER_SECONDS = int(os.getenv("RAG_INGEST_STALE_AFTER_SECONDS", "1800"))
INGEST_MAX_ATTEMPTS = int(os.getenv("RAG_INGEST_MAX_ATTEMPTS", "3"))
_ingest_max_attempts = INGEST_MAX_ATTEMPTS
DEAD_LETTER_STATUS = "dead_letter"
CANCELLED_STATUS = "cancelled"
CANCELLING_STATUS = "cancelling"
PAUSED_STATUS = "paused"
PAUSING_STATUS = "pausing"
TERMINAL_INGEST_JOB_STATUSES = {"succeeded", "failed", DEAD_LETTER_STATUS, CANCELLED_STATUS}
ACTIVE_INGEST_JOB_STATUSES = {"queued", "running", CANCELLING_STATUS, PAUSING_STATUS}


def get_ingest_max_attempts() -> int:
    return _ingest_max_attempts


def set_ingest_max_attempts(value: int) -> None:
    global _ingest_max_attempts
    _ingest_max_attempts = max(1, int(value))


async def create_ingest_job(
    session: AsyncSession,
    file_id: str,
    job_type: str,
) -> dict[str, Any]:
    from uuid import uuid4

    job_id = str(uuid4())
    attempt_result = await session.execute(
        text(
            """
            SELECT COALESCE(MAX(attempt), 0) + 1 AS attempt
            FROM ingest_job
            WHERE file_id = CAST(:file_id AS uuid)
            """
        ),
        {"file_id": file_id},
    )
    attempt = int(attempt_result.mappings().first()["attempt"])
    max_attempts = get_ingest_max_attempts()
    is_dead_letter = attempt > max_attempts
    status = DEAD_LETTER_STATUS if is_dead_letter else "queued"
    stage = DEAD_LETTER_STATUS if is_dead_letter else "queued"
    progress_percent = 100 if is_dead_letter else 0
    error = _max_attempts_error(attempt) if is_dead_letter else None
    result = (
        {
            "reason": "max_attempts_exceeded",
            "attempt": attempt,
            "max_attempts": max_attempts,
        }
        if is_dead_letter
        else None
    )
    await session.execute(
        text(
            """
            INSERT INTO ingest_job (
              job_id,
              file_id,
              job_type,
              status,
              stage,
              progress_percent,
              attempt,
              error,
              result,
              finished_at
            )
            VALUES (
              CAST(:job_id AS uuid),
              CAST(:file_id AS uuid),
              :job_type,
              :status,
              :stage,
              :progress_percent,
              :attempt,
              :error,
              CAST(:result AS jsonb),
              CASE WHEN :is_dead_letter THEN NOW() ELSE NULL END
            )
            """
        ),
        {
            "job_id": job_id,
            "file_id": file_id,
            "job_type": job_type,
            "status": status,
            "stage": stage,
            "progress_percent": progress_percent,
            "attempt": attempt,
            "error": error,
            "result": json.dumps(result, ensure_ascii=False) if result is not None else None,
            "is_dead_letter": is_dead_letter,
        },
    )
    if is_dead_letter:
        await session.execute(
            update_file_ingest_status_query(),
            update_file_ingest_status_params(
                file_id=file_id,
                status=DEAD_LETTER_STATUS,
                error=error,
                indexed_chunks=0,
            ),
        )
    return {
        "job_id": job_id,
        "job_type": job_type,
        "status": status,
        "stage": stage,
        "progress_percent": progress_percent,
        "attempt": attempt,
        "error": error,
        "result": result,
        "started_at": None,
        "finished_at": None,
        "created_at": None,
        "updated_at": None,
    }


async def queue_existing_file_jobs(
    session: AsyncSession,
    file_ids: list[str],
    job_type: str,
) -> list[dict[str, Any]]:
    jobs = []
    for file_id in file_ids:
        await session.execute(
            update_file_ingest_status_query(),
            update_file_ingest_status_params(
                file_id=file_id,
                status="queued",
                error=None,
                indexed_chunks=0,
            ),
        )
        jobs.append(
            await create_ingest_job(
                session=session,
                file_id=file_id,
                job_type=job_type,
            )
        )
    return jobs


async def run_ingest_worker_forever(
    batch_size: int = INGEST_WORKER_BATCH_SIZE,
    poll_seconds: float = INGEST_WORKER_POLL_SECONDS,
    stale_after_seconds: int = INGEST_STALE_AFTER_SECONDS,
) -> None:
    engine = create_async_engine(config.postgres.db_url, echo=False)
    store = QdrantKnowledgeStore(GigaChatEmbeddings())
    s3_session = get_s3_session()
    try:
        async with s3_session.create_client(
            "s3",
            endpoint_url=config.minio.s3_url,
            aws_access_key_id=config.minio.user,
            aws_secret_access_key=config.minio.password,
            region_name="us-east-1",
            config=ClientConfig(connect_timeout=50, read_timeout=120),
        ) as s3_client:
            while True:
                processed = await run_ingest_worker_once(
                    engine=engine,
                    s3_client=s3_client,
                    qdrant_store=store,
                    batch_size=batch_size,
                    stale_after_seconds=stale_after_seconds,
                )
                if processed == 0:
                    await asyncio.sleep(poll_seconds)
    finally:
        await engine.dispose()


async def run_ingest_worker_once(
    engine: AsyncEngine | None = None,
    s3_client: AioBaseClient | None = None,
    qdrant_store: QdrantKnowledgeStore | None = None,
    batch_size: int = INGEST_WORKER_BATCH_SIZE,
    stale_after_seconds: int = INGEST_STALE_AFTER_SECONDS,
) -> int:
    own_engine = engine is None
    engine = engine or create_async_engine(config.postgres.db_url, echo=False)
    try:
        rows = await claim_ingest_jobs(
            engine=engine,
            limit=batch_size,
            stale_after_seconds=stale_after_seconds,
        )
        if not rows:
            return 0

        await process_claimed_ingest_jobs(
            engine=engine,
            rows=rows,
            s3_client=s3_client,
            qdrant_store=qdrant_store,
        )
        return len(rows)
    finally:
        if own_engine:
            await engine.dispose()


async def claim_ingest_jobs(
    engine: AsyncEngine,
    limit: int,
    stale_after_seconds: int = INGEST_STALE_AFTER_SECONDS,
) -> list[dict]:
    await reset_stale_ingest_jobs(engine, stale_after_seconds=stale_after_seconds)
    async with engine.begin() as connection:
        result = await connection.execute(
            text(
                """
                WITH claimed AS (
                  SELECT ij.job_id
                  FROM ingest_job ij
                  WHERE ij.status = 'queued'
                  ORDER BY ij.created_at ASC
                  FOR UPDATE OF ij SKIP LOCKED
                  LIMIT :limit
                ),
                updated AS (
                  UPDATE ingest_job ij
                  SET status = 'running',
                      stage = 'claimed',
                      progress_percent = 1,
                      error = NULL,
                      started_at = COALESCE(ij.started_at, NOW()),
                      updated_at = NOW()
                  FROM claimed
                  WHERE ij.job_id = claimed.job_id
                  RETURNING
                    ij.job_id,
                    ij.job_type,
                    ij.attempt,
                    ij.created_at,
                    ij.file_id
                )
                SELECT
                  updated.job_id,
                  updated.job_type,
                  updated.attempt,
                  f.file_id,
                  f.filename,
                  f.content_type,
                  t.theme_id,
                  t.title AS theme_title
                FROM updated
                JOIN file f ON f.file_id = updated.file_id
                JOIN theme_file tf ON tf.file_id = f.file_id
                JOIN theme t ON t.theme_id = tf.theme_id
                ORDER BY updated.created_at ASC
                """
            ),
            {"limit": max(1, limit)},
        )
        return [dict(row) for row in result.mappings().all()]


async def reset_stale_ingest_jobs(
    engine: AsyncEngine,
    stale_after_seconds: int = INGEST_STALE_AFTER_SECONDS,
) -> int:
    async with engine.begin() as connection:
        result = await connection.execute(
            text(
                """
                UPDATE ingest_job
                SET status = 'queued',
                    stage = 'queued',
                    progress_percent = 0,
                    error = NULL,
                    updated_at = NOW()
                WHERE status = 'running'
                  AND updated_at < NOW() - (:stale_after_seconds * INTERVAL '1 second')
                """
            ),
            {"stale_after_seconds": max(1, stale_after_seconds)},
        )
    return int(result.rowcount or 0)


async def process_claimed_ingest_jobs(
    engine: AsyncEngine,
    rows: list[dict],
    s3_client: AioBaseClient | None = None,
    qdrant_store: QdrantKnowledgeStore | None = None,
) -> None:
    if not rows:
        return

    store = qdrant_store or QdrantKnowledgeStore(GigaChatEmbeddings())
    if s3_client is not None:
        await _process_with_s3_client(engine, rows, s3_client, store)
        return

    s3_session = get_s3_session()
    async with s3_session.create_client(
        "s3",
        endpoint_url=config.minio.s3_url,
        aws_access_key_id=config.minio.user,
        aws_secret_access_key=config.minio.password,
        region_name="us-east-1",
        config=ClientConfig(connect_timeout=50, read_timeout=120),
    ) as managed_s3_client:
        await _process_with_s3_client(engine, rows, managed_s3_client, store)


async def _process_with_s3_client(
    engine: AsyncEngine,
    rows: list[dict],
    s3_client: AioBaseClient,
    qdrant_store: QdrantKnowledgeStore,
) -> None:
    semaphore = asyncio.Semaphore(max(1, UPLOAD_INDEX_CONCURRENCY))
    await asyncio.gather(
        *[
            index_existing_file(
                engine=engine,
                s3_client=s3_client,
                row=row,
                qdrant_store=qdrant_store,
                semaphore=semaphore,
            )
            for row in rows
        ]
    )


async def index_existing_file(
    engine: AsyncEngine,
    s3_client: AioBaseClient,
    row: dict,
    qdrant_store: QdrantKnowledgeStore,
    semaphore: asyncio.Semaphore,
) -> None:
    async with semaphore:
        job_id = str(row["job_id"])
        file_id = str(row["file_id"])
        filename = row["filename"]
        timings: dict[str, float] = {}
        job_started = time.perf_counter()
        logger.info("Worker indexing %s (%s), job=%s", filename, file_id, job_id)

        if await stop_if_job_interrupted(engine, job_id, file_id, progress_percent=1):
            return
        await update_ingest_job_with_engine(
            engine,
            job_id,
            "running",
            stage="starting",
            progress_percent=5,
            set_started_at=True,
        )
        await update_file_ingest_status_with_engine(engine, file_id, "indexing")
        try:
            if await stop_if_job_interrupted(engine, job_id, file_id, progress_percent=5):
                return
            await update_ingest_job_with_engine(
                engine,
                job_id,
                "running",
                stage="reading",
                progress_percent=10,
            )
            started = time.perf_counter()
            data = await read_from_s3(s3_client, filename)
            timings["reading_seconds"] = _elapsed_seconds(started)

            prepared_file = {
                "file_id": file_id,
                "filename": filename,
                "content_type": row["content_type"] or "application/octet-stream",
                "data": data,
            }
            if await stop_if_job_interrupted(engine, job_id, file_id, progress_percent=10):
                return
            await update_ingest_job_with_engine(
                engine,
                job_id,
                "running",
                stage="extracting",
                progress_percent=25,
            )
            started = time.perf_counter()
            documents = await to_thread.run_sync(
                extract_documents_sync,
                prepared_file,
                str(row["theme_id"]),
                row["theme_title"],
            )
            timings["extracting_seconds"] = _elapsed_seconds(started)

            if await stop_if_job_interrupted(engine, job_id, file_id, progress_percent=25):
                return
            await update_ingest_job_with_engine(
                engine,
                job_id,
                "running",
                stage="chunking",
                progress_percent=45,
            )
            started = time.perf_counter()
            chunks = await to_thread.run_sync(chunk_documents_sync, documents, row["theme_title"])
            timings["chunking_seconds"] = _elapsed_seconds(started)
            if not chunks:
                raise DocumentExtractionError("No chunks were produced from the uploaded file")
            report = ingest_report(documents, chunks)
            report["timings"] = dict(timings)

            if await stop_if_job_interrupted(engine, job_id, file_id, progress_percent=45, result=report):
                return
            await update_ingest_job_with_engine(
                engine,
                job_id,
                "running",
                stage="embedding",
                progress_percent=65,
                result=report,
            )
            chunks_written, qdrant_timings = await to_thread.run_sync(
                replace_chunks_for_file,
                prepared_file,
                chunks,
                qdrant_store,
            )
            timings.update(qdrant_timings)
        except Exception as exc:
            logger.exception("Failed to index file %s in worker", file_id)
            failed_status = DEAD_LETTER_STATUS if int(row.get("attempt") or 1) >= get_ingest_max_attempts() else "failed"
            failed_stage = DEAD_LETTER_STATUS if failed_status == DEAD_LETTER_STATUS else "failed"
            failed_error = (
                f"{truncate_error(exc)}; {_max_attempts_error(int(row.get('attempt') or 1))}"
                if failed_status == DEAD_LETTER_STATUS
                else truncate_error(exc)
            )
            await update_file_ingest_status_with_engine(
                engine,
                file_id,
                failed_status,
                error=failed_error,
            )
            await update_ingest_job_with_engine(
                engine,
                job_id,
                failed_status,
                stage=failed_stage,
                progress_percent=100,
                error=failed_error,
                result={
                    "timings": timings,
                    "total_seconds": _elapsed_seconds(job_started),
                    "failed_stage": failed_stage,
                },
                set_finished_at=True,
            )
            return

        report["chunks_written"] = chunks_written
        report["timings"] = dict(timings)
        report["total_seconds"] = _elapsed_seconds(job_started)
        await update_file_ingest_status_with_engine(
            engine,
            file_id,
            "indexed",
            indexed_chunks=chunks_written,
        )
        await update_ingest_job_with_engine(
            engine,
            job_id,
            "succeeded",
            stage="done",
            progress_percent=100,
            result=report,
            set_finished_at=True,
        )


async def stop_if_job_interrupted(
    engine: AsyncEngine,
    job_id: str,
    file_id: str,
    progress_percent: int,
    result: dict[str, Any] | None = None,
) -> bool:
    status = await get_ingest_job_status(engine, job_id)
    if status == CANCELLING_STATUS:
        await update_file_ingest_status_with_engine(
            engine,
            file_id,
            CANCELLED_STATUS,
            error="Cancelled by admin",
        )
        await update_ingest_job_with_engine(
            engine,
            job_id,
            CANCELLED_STATUS,
            stage=CANCELLED_STATUS,
            progress_percent=100,
            error="Cancelled by admin",
            result=result,
            set_finished_at=True,
        )
        return True
    if status == PAUSING_STATUS:
        await update_file_ingest_status_with_engine(
            engine,
            file_id,
            PAUSED_STATUS,
            error="Paused by admin",
        )
        await update_ingest_job_with_engine(
            engine,
            job_id,
            PAUSED_STATUS,
            stage=PAUSED_STATUS,
            progress_percent=progress_percent,
            error="Paused by admin",
            result=result,
        )
        return True
    return status in {CANCELLED_STATUS, PAUSED_STATUS}


async def get_ingest_job_status(engine: AsyncEngine, job_id: str) -> str | None:
    async with engine.begin() as connection:
        result = await connection.execute(
            text(
                """
                SELECT status
                FROM ingest_job
                WHERE job_id = CAST(:job_id AS uuid)
                """
            ),
            {"job_id": job_id},
        )
        row = result.mappings().first()
    return str(row["status"]) if row else None


async def read_from_s3(s3_client: AioBaseClient, filename: str) -> bytes:
    response = await s3_client.get_object(Bucket=config.minio.bucket, Key=filename)
    async with response["Body"] as stream:
        return await stream.read()


async def update_file_ingest_status_with_engine(
    engine: AsyncEngine,
    file_id: str,
    status: str,
    error: str | None = None,
    indexed_chunks: int = 0,
) -> None:
    async with engine.begin() as connection:
        await connection.execute(
            update_file_ingest_status_query(),
            update_file_ingest_status_params(
                file_id=file_id,
                status=status,
                error=error,
                indexed_chunks=indexed_chunks,
            ),
        )


async def update_ingest_job_with_engine(
    engine: AsyncEngine,
    job_id: str,
    status: str,
    stage: str,
    progress_percent: int,
    error: str | None = None,
    result: dict[str, Any] | None = None,
    set_started_at: bool = False,
    set_finished_at: bool = False,
) -> None:
    async with engine.begin() as connection:
        await connection.execute(
            text(
                """
                UPDATE ingest_job
                SET status = :status,
                    stage = :stage,
                    progress_percent = :progress_percent,
                    error = :error,
                    result = COALESCE(CAST(:result AS jsonb), result),
                    started_at = CASE WHEN :set_started_at THEN NOW() ELSE started_at END,
                    finished_at = CASE WHEN :set_finished_at THEN NOW() ELSE finished_at END,
                    updated_at = NOW()
                WHERE job_id = CAST(:job_id AS uuid)
                """
            ),
            {
                "job_id": job_id,
                "status": status,
                "stage": stage,
                "progress_percent": max(0, min(100, progress_percent)),
                "error": error,
                "result": json.dumps(result, ensure_ascii=False) if result is not None else None,
                "set_started_at": set_started_at,
                "set_finished_at": set_finished_at,
            },
        )


def update_file_ingest_status_query():
    return text(
        """
        UPDATE file
        SET ingest_status = :status,
            ingest_error = :error,
            indexed_chunks = :indexed_chunks,
            indexed_at = CASE WHEN :set_indexed_at THEN NOW() ELSE indexed_at END
        WHERE file_id = CAST(:file_id AS uuid)
        """
    )


def update_file_ingest_status_params(
    file_id: str,
    status: str,
    error: str | None,
    indexed_chunks: int,
) -> dict:
    return {
        "file_id": file_id,
        "status": status,
        "error": error,
        "indexed_chunks": indexed_chunks,
        "set_indexed_at": status == "indexed",
    }


def extract_documents_sync(
    prepared: dict,
    theme_id: str,
    theme_title: str,
) -> list:
    return extract_documents(
        data=prepared["data"],
        filename=prepared["filename"],
        content_type=prepared["content_type"],
        file_id=str(prepared["file_id"]),
        theme_id=theme_id,
        theme_title=theme_title,
    )


def chunk_documents_sync(documents: list, theme_title: str) -> list:
    prepared_documents = prepare_documents_for_chunking(documents, fallback_section=theme_title)
    return split_text(prepared_documents)


def replace_chunks_for_file(
    prepared: dict,
    chunks: list,
    qdrant_store: QdrantKnowledgeStore,
) -> tuple[int, dict[str, float]]:
    store = clone_qdrant_store(qdrant_store) if isinstance(qdrant_store, QdrantKnowledgeStore) else qdrant_store
    timings = {}
    started = time.perf_counter()
    store.delete_by_metadata("file_id", str(prepared["file_id"]))
    timings["qdrant_delete_seconds"] = _elapsed_seconds(started)
    started = time.perf_counter()
    chunks_written = store.upsert_documents(chunks, incremental=True)
    timings["embedding_qdrant_upsert_seconds"] = _elapsed_seconds(started)
    return chunks_written, timings


def ingest_report(documents: list, chunks: list) -> dict[str, Any]:
    extractors = Counter(str(document.metadata.get("extractor") or "unknown") for document in documents)
    pages = {
        int(document.metadata["page"])
        for document in documents
        if document.metadata.get("page") is not None
    }
    section_titles = {
        str(chunk.metadata.get("section_title") or "")
        for chunk in chunks
        if chunk.metadata.get("section_title")
    }
    chunk_lengths = [len(chunk.page_content) for chunk in chunks]
    return {
        "extracted_documents": len(documents),
        "extracted_chars": sum(len(document.page_content) for document in documents),
        "pages": len(pages) or None,
        "extractors": dict(extractors),
        "ocr_pages": sum(1 for document in documents if document.metadata.get("extractor") == "tesseract-ocr"),
        "sections": len(section_titles),
        "chunks": len(chunks),
        "chunk_chars_min": min(chunk_lengths) if chunk_lengths else 0,
        "chunk_chars_max": max(chunk_lengths) if chunk_lengths else 0,
        "missing_section_titles": sum(1 for chunk in chunks if not chunk.metadata.get("section_title")),
    }


def clone_qdrant_store(store: QdrantKnowledgeStore) -> QdrantKnowledgeStore:
    return QdrantKnowledgeStore(
        store.embeddings,
        url=store.url,
        collection_name=store.collection_name,
        vector_size=store.vector_size,
    )


def truncate_error(exc: Exception) -> str:
    return str(exc)[:1000] or exc.__class__.__name__


def _max_attempts_error(attempt: int) -> str:
    return f"Max ingest attempts exceeded: attempt {attempt}, limit {get_ingest_max_attempts()}"


def _elapsed_seconds(started: float) -> float:
    return round(max(0.0, time.perf_counter() - started), 3)
