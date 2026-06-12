import asyncio
import logging
import os
import re
from pathlib import Path
from uuid import UUID, uuid4

from aiobotocore.client import AioBaseClient
from anyio import to_thread
from botocore.exceptions import ClientError
from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from unidecode import unidecode

from src.api.commons.internal_auth import require_internal_token
from src.api.commons.public_auth import require_admin_auth
from src.config import config
from src.core.rag.admin_document_ingest_jobs import (
    CANCELLED_STATUS,
    CANCELLING_STATUS,
    DEAD_LETTER_STATUS,
    INGEST_MAX_ATTEMPTS,
    INGEST_STALE_AFTER_SECONDS,
    INGEST_WORKER_BATCH_SIZE,
    INGEST_WORKER_POLL_SECONDS,
    PAUSED_STATUS,
    PAUSING_STATUS,
    TERMINAL_INGEST_JOB_STATUSES,
    UPLOAD_INDEX_CONCURRENCY,
    create_ingest_job,
    queue_existing_file_jobs,
    update_file_ingest_status_params,
    update_file_ingest_status_query,
)
from src.core.rag.qdrant_store import QdrantKnowledgeStore

logger = logging.getLogger(__name__)

ALLOWED_MIMES = {
    "application/pdf",
    "text/plain",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
ALLOWED_EXTS = {".pdf", ".txt", ".docx"}
MAX_SIZE_BYTES = 50 * 1024 * 1024
UPLOAD_STORAGE_CONCURRENCY = int(os.getenv("RAG_UPLOAD_STORAGE_CONCURRENCY", "4"))

admin_documents_router = APIRouter(
    prefix="/internal/admin/documents",
    tags=["Internal Admin Documents"],
    dependencies=[Depends(require_internal_token)],
)
public_admin_documents_router = APIRouter(
    prefix="/api/documents",
    tags=["Admin Documents"],
    dependencies=[Depends(require_admin_auth)],
)


@admin_documents_router.get("/stats")
@public_admin_documents_router.get("/stats")
@inject
async def get_admin_document_stats_handler(
    session: FromDishka[AsyncSession],
) -> dict:
    result = await session.execute(
        text(
            """
            SELECT
              COUNT(DISTINCT t.theme_id)::int AS total_themes,
              COUNT(tf.file_id)::int          AS total_files
            FROM theme t
            LEFT JOIN theme_file tf ON tf.theme_id = t.theme_id
            """
        )
    )
    return dict(result.mappings().first())


@admin_documents_router.get("")
@public_admin_documents_router.get("")
@inject
async def get_admin_documents_handler(
    session: FromDishka[AsyncSession],
) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
              t.theme_id AS id,
              t.title,
              t.theme_order,
              f.file_id,
              f.filename,
              f.content_type,
              f.ingest_status,
              f.ingest_error,
              f.indexed_chunks,
              f.indexed_at,
              ij.job_id,
              ij.job_type,
              ij.status AS job_status,
              ij.stage AS job_stage,
              ij.progress_percent AS job_progress_percent,
              ij.attempt AS job_attempt,
              ij.error AS job_error,
              ij.result AS job_result,
              ij.started_at AS job_started_at,
              ij.finished_at AS job_finished_at,
              ij.created_at AS job_created_at,
              ij.updated_at AS job_updated_at
            FROM theme t
            LEFT JOIN theme_file tf ON tf.theme_id = t.theme_id
            LEFT JOIN file f ON f.file_id = tf.file_id
            LEFT JOIN LATERAL (
              SELECT
                job_id,
                job_type,
                status,
                stage,
                progress_percent,
                attempt,
                error,
                result,
                started_at,
                finished_at,
                created_at,
                updated_at
              FROM ingest_job
              WHERE file_id = f.file_id
              ORDER BY created_at DESC
              LIMIT 1
            ) ij ON TRUE
            ORDER BY t.theme_order ASC, f.filename ASC
            """
        )
    )

    documents: dict[str, dict] = {}
    for row in result.mappings().all():
        theme_id = str(row["id"])
        document = documents.setdefault(
            theme_id,
            {
                "id": theme_id,
                "title": row["title"],
                "theme_order": row["theme_order"],
                "files": [],
                "file_count": 0,
            },
        )
        if row["file_id"]:
            document["files"].append(
                {
                    "file_id": str(row["file_id"]),
                    "filename": row["filename"],
                    "content_type": row["content_type"],
                    "ingest_status": row["ingest_status"],
                    "ingest_error": row["ingest_error"],
                    "indexed_chunks": row["indexed_chunks"],
                    "indexed_at": row["indexed_at"].isoformat() if row["indexed_at"] else None,
                    "latest_job": _job_response(row),
                }
            )
            document["file_count"] += 1

    return list(documents.values())


@admin_documents_router.post("/upload")
@public_admin_documents_router.post("/upload")
@inject
async def upload_admin_document_handler(
    session: FromDishka[AsyncSession],
    s3_client: FromDishka[AioBaseClient],
    title: str | None = Form(default=None),
    files: list[UploadFile] | None = File(default=None),
):
    title_value = title.strip() if title else ""
    if not title_value:
        return JSONResponse(status_code=400, content={"error": "title is required"})

    prepared_files = await _prepare_files(files)
    if isinstance(prepared_files, JSONResponse):
        return prepared_files

    async with session.begin():
        order_result = await session.execute(text("SELECT COALESCE(MAX(theme_order), 0) AS max_order FROM theme"))
        next_order = int(order_result.mappings().first()["max_order"]) + 1
        theme_id = uuid4()

        await session.execute(
            text(
                """
                INSERT INTO theme (theme_id, title, theme_order)
                VALUES (:theme_id, :title, :theme_order)
                """
            ),
            {"theme_id": theme_id, "title": title_value, "theme_order": next_order},
        )

        exam_order_result = await session.execute(
            text("SELECT COALESCE(MAX(exam_theme_order), 0) AS max_order FROM exam_theme")
        )
        exam_next_order = int(exam_order_result.mappings().first()["max_order"]) + 1
        await session.execute(
            text(
                """
                INSERT INTO exam_theme (exam_theme_id, title, exam_theme_order)
                VALUES (:exam_theme_id, :title, :exam_theme_order)
                """
            ),
            {"exam_theme_id": uuid4(), "title": title_value, "exam_theme_order": exam_next_order},
        )

        for prepared in prepared_files:
            prepared["file_id"] = uuid4()

        await _upload_files_to_s3(s3_client, prepared_files)

        for prepared in prepared_files:
            await session.execute(
                text(
                    """
                    INSERT INTO file (file_id, filename, content_type, ingest_status)
                    VALUES (:file_id, :filename, :content_type, 'queued')
                    """
                ),
                {
                    "file_id": prepared["file_id"],
                    "filename": prepared["filename"],
                    "content_type": prepared["content_type"],
                },
            )
            await session.execute(
                text(
                    """
                    INSERT INTO theme_file (theme_id, file_id)
                    VALUES (:theme_id, :file_id)
                    """
                ),
                {"theme_id": theme_id, "file_id": prepared["file_id"]},
            )
            job = await create_ingest_job(
                session=session,
                file_id=str(prepared["file_id"]),
                job_type="upload",
            )
            prepared["job_id"] = job["job_id"]
            prepared["job_type"] = "upload"
            prepared["latest_job"] = job
            prepared["ingest_status"] = job["status"]

    return JSONResponse(
        status_code=202,
        content={
            "id": str(theme_id),
            "title": title_value,
            "theme_order": next_order,
            "files": [
                _file_response(prepared, ingest_status="queued")
                for prepared in prepared_files
            ],
            "file_count": len(prepared_files),
        },
    )


@admin_documents_router.post("/failed/reindex")
@public_admin_documents_router.post("/failed/reindex")
@inject
async def reindex_failed_admin_document_files_handler(
    session: FromDishka[AsyncSession],
):
    async with session.begin():
        result = await session.execute(
            text(
                """
                SELECT file_id::text AS file_id
                FROM file
                WHERE ingest_status = 'failed'
                ORDER BY created_at ASC
                """
            )
        )
        file_ids = [row["file_id"] for row in result.mappings().all()]
        jobs = await queue_existing_file_jobs(session, file_ids, job_type="retry_failed")

    return JSONResponse(status_code=202, content=_queue_jobs_response(jobs))


@admin_documents_router.get("/ingest/metrics")
@public_admin_documents_router.get("/ingest/metrics")
@inject
async def get_admin_document_ingest_metrics_handler(
    session: FromDishka[AsyncSession],
) -> dict:
    job_status_result = await session.execute(
        text(
            """
            SELECT status, COUNT(*)::int AS count
            FROM ingest_job
            GROUP BY status
            ORDER BY status
            """
        )
    )
    file_status_result = await session.execute(
        text(
            """
            SELECT ingest_status AS status, COUNT(*)::int AS count
            FROM file
            GROUP BY ingest_status
            ORDER BY ingest_status
            """
        )
    )
    summary_result = await session.execute(
        text(
            """
            SELECT
              COUNT(*) FILTER (WHERE status = 'queued')::int AS queue_depth,
              COUNT(*) FILTER (WHERE status = 'running')::int AS running_count,
              COUNT(*) FILTER (WHERE status = 'paused')::int AS paused_count,
              COUNT(*) FILTER (WHERE status = 'cancelling')::int AS cancelling_count,
              COUNT(*) FILTER (WHERE status = 'pausing')::int AS pausing_count,
              COUNT(*) FILTER (WHERE status = 'failed')::int AS failed_count,
              COUNT(*) FILTER (WHERE status = 'dead_letter')::int AS dead_letter_count,
              COUNT(*) FILTER (WHERE status = 'cancelled')::int AS cancelled_count,
              EXTRACT(EPOCH FROM (NOW() - (MIN(created_at) FILTER (WHERE status = 'queued'))))::float
                AS oldest_queued_age_seconds,
              (AVG(EXTRACT(EPOCH FROM (finished_at - started_at)))
                FILTER (WHERE finished_at IS NOT NULL AND started_at IS NOT NULL))::float
                AS avg_total_seconds,
              MAX(finished_at) FILTER (WHERE status = 'succeeded') AS last_success_at,
              MAX(finished_at) FILTER (WHERE status IN ('failed', 'dead_letter')) AS last_failure_at
            FROM ingest_job
            """
        )
    )
    timing_result = await session.execute(
        text(
            """
            SELECT
              AVG(NULLIF(result #>> '{timings,reading_seconds}', '')::numeric)::float
                AS reading_seconds,
              AVG(NULLIF(result #>> '{timings,extracting_seconds}', '')::numeric)::float
                AS extracting_seconds,
              AVG(NULLIF(result #>> '{timings,chunking_seconds}', '')::numeric)::float
                AS chunking_seconds,
              AVG(NULLIF(result #>> '{timings,qdrant_delete_seconds}', '')::numeric)::float
                AS qdrant_delete_seconds,
              AVG(NULLIF(result #>> '{timings,embedding_qdrant_upsert_seconds}', '')::numeric)::float
                AS embedding_qdrant_upsert_seconds
            FROM ingest_job
            WHERE result ? 'timings'
            """
        )
    )

    summary = dict(summary_result.mappings().first() or {})
    timings = {
        key: _round_float(value)
        for key, value in dict(timing_result.mappings().first() or {}).items()
        if value is not None
    }
    return {
        "jobs_by_status": _count_rows(job_status_result.mappings().all()),
        "files_by_status": _count_rows(file_status_result.mappings().all()),
        "queue": {
            "depth": summary.get("queue_depth") or 0,
            "running": summary.get("running_count") or 0,
            "paused": summary.get("paused_count") or 0,
            "cancelling": summary.get("cancelling_count") or 0,
            "pausing": summary.get("pausing_count") or 0,
            "oldest_queued_age_seconds": _round_float(summary.get("oldest_queued_age_seconds")),
        },
        "failures": {
            "failed": summary.get("failed_count") or 0,
            "dead_letter": summary.get("dead_letter_count") or 0,
            "cancelled": summary.get("cancelled_count") or 0,
            "last_failure_at": _isoformat(summary.get("last_failure_at")),
        },
        "performance": {
            "avg_total_seconds": _round_float(summary.get("avg_total_seconds")),
            "avg_stage_seconds": timings,
            "last_success_at": _isoformat(summary.get("last_success_at")),
        },
        "worker": {
            "batch_size": INGEST_WORKER_BATCH_SIZE,
            "poll_seconds": INGEST_WORKER_POLL_SECONDS,
            "stale_after_seconds": INGEST_STALE_AFTER_SECONDS,
            "index_concurrency": UPLOAD_INDEX_CONCURRENCY,
            "max_attempts": INGEST_MAX_ATTEMPTS,
        },
    }


@admin_documents_router.post("/{theme_id}/files")
@public_admin_documents_router.post("/{theme_id}/files")
@inject
async def add_admin_document_files_handler(
    theme_id: UUID,
    session: FromDishka[AsyncSession],
    s3_client: FromDishka[AioBaseClient],
    files: list[UploadFile] | None = File(default=None),
):
    prepared_files = await _prepare_files(files)
    if isinstance(prepared_files, JSONResponse):
        return prepared_files

    async with session.begin():
        theme_result = await session.execute(
            text("SELECT theme_id, title FROM theme WHERE theme_id = :theme_id"),
            {"theme_id": theme_id},
        )
        theme = theme_result.mappings().first()
        if not theme:
            return JSONResponse(status_code=404, content={"error": "Theme not found"})

        for prepared in prepared_files:
            prepared["file_id"] = uuid4()

        await _upload_files_to_s3(s3_client, prepared_files)

        for prepared in prepared_files:
            await session.execute(
                text(
                    """
                    INSERT INTO file (file_id, filename, content_type, ingest_status)
                    VALUES (:file_id, :filename, :content_type, 'queued')
                    """
                ),
                {
                    "file_id": prepared["file_id"],
                    "filename": prepared["filename"],
                    "content_type": prepared["content_type"],
                },
            )
            await session.execute(
                text(
                    """
                    INSERT INTO theme_file (theme_id, file_id)
                    VALUES (:theme_id, :file_id)
                    """
                ),
                {"theme_id": theme_id, "file_id": prepared["file_id"]},
            )
            job = await create_ingest_job(
                session=session,
                file_id=str(prepared["file_id"]),
                job_type="upload",
            )
            prepared["job_id"] = job["job_id"]
            prepared["job_type"] = "upload"
            prepared["latest_job"] = job
            prepared["ingest_status"] = job["status"]

    return JSONResponse(
        status_code=202,
        content={
            "added": [
                _file_response(prepared, ingest_status="queued")
                for prepared in prepared_files
            ],
            "theme_id": str(theme_id),
        },
    )


@admin_documents_router.post("/{theme_id}/reindex")
@public_admin_documents_router.post("/{theme_id}/reindex")
@inject
async def reindex_admin_document_theme_handler(
    theme_id: UUID,
    session: FromDishka[AsyncSession],
):
    async with session.begin():
        theme_result = await session.execute(
            text("SELECT theme_id FROM theme WHERE theme_id = :theme_id"),
            {"theme_id": theme_id},
        )
        if not theme_result.mappings().first():
            return JSONResponse(status_code=404, content={"error": "Theme not found"})

        file_result = await session.execute(
            text(
                """
                SELECT f.file_id::text AS file_id
                FROM file f
                JOIN theme_file tf ON tf.file_id = f.file_id
                WHERE tf.theme_id = :theme_id
                ORDER BY f.filename ASC
                """
            ),
            {"theme_id": theme_id},
        )
        file_ids = [row["file_id"] for row in file_result.mappings().all()]
        jobs = await queue_existing_file_jobs(session, file_ids, job_type="reindex_theme")

    return JSONResponse(status_code=202, content=_queue_jobs_response(jobs))


@admin_documents_router.post("/{theme_id}/files/{file_id}/reindex")
@public_admin_documents_router.post("/{theme_id}/files/{file_id}/reindex")
@inject
async def reindex_admin_document_file_handler(
    theme_id: UUID,
    file_id: UUID,
    session: FromDishka[AsyncSession],
):
    async with session.begin():
        result = await session.execute(
            text(
                """
                SELECT
                  f.file_id,
                  f.filename,
                  f.content_type,
                  t.theme_id,
                  t.title AS theme_title
                FROM file f
                JOIN theme_file tf ON tf.file_id = f.file_id
                JOIN theme t ON t.theme_id = tf.theme_id
                WHERE t.theme_id = :theme_id
                  AND f.file_id = :file_id
                """
            ),
            {"theme_id": theme_id, "file_id": file_id},
        )
        row = result.mappings().first()
        if row:
            await session.execute(
                update_file_ingest_status_query(),
                update_file_ingest_status_params(
                    file_id=str(file_id),
                    status="queued",
                    error=None,
                    indexed_chunks=0,
                ),
            )
            job = await create_ingest_job(
                session=session,
                file_id=str(file_id),
                job_type="reindex",
            )

    if not row:
        return JSONResponse(status_code=404, content={"error": "File not found"})

    prepared = {
        "file_id": str(row["file_id"]),
        "filename": row["filename"],
        "content_type": row["content_type"] or "application/octet-stream",
        "job_id": job["job_id"],
        "job_type": "reindex",
        "latest_job": job,
        "ingest_status": job["status"],
    }

    return JSONResponse(
        status_code=202,
        content=_file_response(prepared, ingest_status=job["status"]),
    )


@admin_documents_router.post("/{theme_id}/files/{file_id}/ingest/pause")
@public_admin_documents_router.post("/{theme_id}/files/{file_id}/ingest/pause")
@inject
async def pause_admin_document_file_ingest_handler(
    theme_id: UUID,
    file_id: UUID,
    session: FromDishka[AsyncSession],
):
    row = await _load_file_with_latest_job(session, theme_id, file_id)
    if not row:
        return JSONResponse(status_code=404, content={"error": "File not found"})
    job = _job_response(row)
    if not job:
        return JSONResponse(status_code=404, content={"error": "Ingest job not found"})
    if job["status"] in TERMINAL_INGEST_JOB_STATUSES:
        return JSONResponse(status_code=409, content={"error": "Terminal ingest job cannot be paused"})
    if job["status"] == PAUSED_STATUS:
        return JSONResponse(status_code=200, content={"file": _file_response_from_row(row), "latest_job": job})
    if job["status"] == CANCELLING_STATUS:
        return JSONResponse(status_code=409, content={"error": "Cancellation is already requested"})

    target_status = PAUSED_STATUS if job["status"] == "queued" else PAUSING_STATUS
    target_stage = PAUSED_STATUS if target_status == PAUSED_STATUS else PAUSING_STATUS
    await _update_job_control_status(
        session,
        job["job_id"],
        status=target_status,
        stage=target_stage,
        progress_percent=job["progress_percent"] or 0,
        error="Paused by admin",
    )
    await session.execute(
        update_file_ingest_status_query(),
        update_file_ingest_status_params(
            file_id=str(file_id),
            status=target_status,
            error="Paused by admin",
            indexed_chunks=0,
        ),
    )
    await session.commit()

    updated_row = await _load_file_with_latest_job(session, theme_id, file_id)
    return {"file": _file_response_from_row(updated_row), "latest_job": _job_response(updated_row)}


@admin_documents_router.post("/{theme_id}/files/{file_id}/ingest/resume")
@public_admin_documents_router.post("/{theme_id}/files/{file_id}/ingest/resume")
@inject
async def resume_admin_document_file_ingest_handler(
    theme_id: UUID,
    file_id: UUID,
    session: FromDishka[AsyncSession],
):
    row = await _load_file_with_latest_job(session, theme_id, file_id)
    if not row:
        return JSONResponse(status_code=404, content={"error": "File not found"})
    job = _job_response(row)
    if not job:
        return JSONResponse(status_code=404, content={"error": "Ingest job not found"})
    if job["status"] != PAUSED_STATUS:
        return JSONResponse(status_code=409, content={"error": "Only paused ingest jobs can be resumed"})

    await _update_job_control_status(
        session,
        job["job_id"],
        status="queued",
        stage="queued",
        progress_percent=0,
        error=None,
        clear_started_at=True,
        clear_finished_at=True,
    )
    await session.execute(
        update_file_ingest_status_query(),
        update_file_ingest_status_params(
            file_id=str(file_id),
            status="queued",
            error=None,
            indexed_chunks=0,
        ),
    )
    await session.commit()

    updated_row = await _load_file_with_latest_job(session, theme_id, file_id)
    return {"file": _file_response_from_row(updated_row), "latest_job": _job_response(updated_row)}


@admin_documents_router.post("/{theme_id}/files/{file_id}/ingest/cancel")
@public_admin_documents_router.post("/{theme_id}/files/{file_id}/ingest/cancel")
@inject
async def cancel_admin_document_file_ingest_handler(
    theme_id: UUID,
    file_id: UUID,
    session: FromDishka[AsyncSession],
):
    row = await _load_file_with_latest_job(session, theme_id, file_id)
    if not row:
        return JSONResponse(status_code=404, content={"error": "File not found"})
    job = _job_response(row)
    if not job:
        return JSONResponse(status_code=404, content={"error": "Ingest job not found"})
    if job["status"] in TERMINAL_INGEST_JOB_STATUSES:
        return JSONResponse(status_code=409, content={"error": "Terminal ingest job cannot be cancelled"})

    immediate = job["status"] in {"queued", PAUSED_STATUS}
    target_status = CANCELLED_STATUS if immediate else CANCELLING_STATUS
    target_stage = CANCELLED_STATUS if immediate else CANCELLING_STATUS
    await _update_job_control_status(
        session,
        job["job_id"],
        status=target_status,
        stage=target_stage,
        progress_percent=100 if immediate else job["progress_percent"] or 0,
        error="Cancelled by admin",
        set_finished_at=immediate,
    )
    await session.execute(
        update_file_ingest_status_query(),
        update_file_ingest_status_params(
            file_id=str(file_id),
            status=target_status,
            error="Cancelled by admin",
            indexed_chunks=0,
        ),
    )
    await session.commit()

    updated_row = await _load_file_with_latest_job(session, theme_id, file_id)
    return {"file": _file_response_from_row(updated_row), "latest_job": _job_response(updated_row)}


@admin_documents_router.get("/{theme_id}/files/{file_id}/jobs")
@public_admin_documents_router.get("/{theme_id}/files/{file_id}/jobs")
@inject
async def get_admin_document_file_jobs_handler(
    theme_id: UUID,
    file_id: UUID,
    session: FromDishka[AsyncSession],
) -> list[dict]:
    file_result = await session.execute(
        text(
            """
            SELECT f.file_id
            FROM file f
            JOIN theme_file tf ON tf.file_id = f.file_id
            WHERE tf.theme_id = :theme_id
              AND f.file_id = :file_id
            """
        ),
        {"theme_id": theme_id, "file_id": file_id},
    )
    if not file_result.mappings().first():
        return JSONResponse(status_code=404, content={"error": "File not found"})

    result = await session.execute(
        text(
            """
            SELECT
              job_id,
              job_type,
              status AS job_status,
              stage AS job_stage,
              progress_percent AS job_progress_percent,
              attempt AS job_attempt,
              error AS job_error,
              result AS job_result,
              started_at AS job_started_at,
              finished_at AS job_finished_at,
              created_at AS job_created_at,
              updated_at AS job_updated_at
            FROM ingest_job
            WHERE file_id = :file_id
            ORDER BY created_at DESC
            """
        ),
        {"file_id": file_id},
    )
    return [_job_response(row) for row in result.mappings().all()]


@admin_documents_router.delete("/{theme_id}")
@public_admin_documents_router.delete("/{theme_id}")
@inject
async def delete_admin_document_handler(
    theme_id: UUID,
    session: FromDishka[AsyncSession],
    s3_client: FromDishka[AioBaseClient],
    qdrant_store: FromDishka[QdrantKnowledgeStore],
):
    async with session.begin():
        theme_result = await session.execute(
            text("SELECT theme_id FROM theme WHERE theme_id = :theme_id"),
            {"theme_id": theme_id},
        )
        if not theme_result.mappings().first():
            return JSONResponse(status_code=404, content={"error": "Theme not found"})

        file_result = await session.execute(
            text(
                """
                SELECT f.file_id, f.filename
                FROM file f
                JOIN theme_file tf ON tf.file_id = f.file_id
                WHERE tf.theme_id = :theme_id
                """
            ),
            {"theme_id": theme_id},
        )
        files = [dict(row) for row in file_result.mappings().all()]

        await session.execute(text("DELETE FROM theme_file WHERE theme_id = :theme_id"), {"theme_id": theme_id})
        for file in files:
            await session.execute(
                text("DELETE FROM file WHERE file_id = :file_id"),
                {"file_id": file["file_id"]},
            )
        await session.execute(text("DELETE FROM theme WHERE theme_id = :theme_id"), {"theme_id": theme_id})

    for file in files:
        await _delete_from_s3(s3_client, file["filename"])
        try:
            await to_thread.run_sync(qdrant_store.delete_by_metadata, "file_id", str(file["file_id"]))
        except Exception as exc:
            logger.error("Failed to delete Qdrant chunks for file %s: %s", file["file_id"], exc)

    return {"message": "Theme deleted"}


async def _prepare_files(files: list[UploadFile] | None):
    if not files:
        return JSONResponse(status_code=400, content={"error": "At least one file is required"})
    if len(files) > 20:
        return JSONResponse(status_code=400, content={"error": "Too many files"})

    prepared = []
    for file in files:
        ext = Path(file.filename or "").suffix.lower()
        if file.content_type not in ALLOWED_MIMES or ext not in ALLOWED_EXTS:
            return JSONResponse(
                status_code=400,
                content={"error": f"Unsupported file type. Allowed: {', '.join(sorted(ALLOWED_EXTS))}"},
            )

        data = await file.read()
        if len(data) > MAX_SIZE_BYTES:
            return JSONResponse(status_code=400, content={"error": "File is too large"})

        prepared.append(
            {
                "filename": _to_ascii_filename(file.filename),
                "content_type": file.content_type or "application/octet-stream",
                "data": data,
            }
        )

    return prepared


async def _upload_to_s3(s3_client: AioBaseClient, prepared: dict) -> None:
    await s3_client.put_object(
        Bucket=config.minio.bucket,
        Key=prepared["filename"],
        Body=prepared["data"],
        ContentType=prepared["content_type"],
        Metadata={"original_filename": prepared["filename"]},
    )


async def _upload_files_to_s3(
    s3_client: AioBaseClient,
    prepared_files: list[dict],
    concurrency: int = UPLOAD_STORAGE_CONCURRENCY,
) -> None:
    semaphore = asyncio.Semaphore(max(1, concurrency))

    async def upload_one(prepared: dict) -> None:
        async with semaphore:
            await _upload_to_s3(s3_client, prepared)

    await asyncio.gather(*(upload_one(prepared) for prepared in prepared_files))


async def _delete_from_s3(s3_client: AioBaseClient, filename: str) -> None:
    try:
        await s3_client.delete_object(Bucket=config.minio.bucket, Key=filename)
    except ClientError:
        pass


async def _load_file_with_latest_job(
    session: AsyncSession,
    theme_id: UUID,
    file_id: UUID,
):
    result = await session.execute(
        text(
            """
            SELECT
              f.file_id,
              f.filename,
              f.content_type,
              f.ingest_status,
              f.ingest_error,
              f.indexed_chunks,
              f.indexed_at,
              ij.job_id,
              ij.job_type,
              ij.status AS job_status,
              ij.stage AS job_stage,
              ij.progress_percent AS job_progress_percent,
              ij.attempt AS job_attempt,
              ij.error AS job_error,
              ij.result AS job_result,
              ij.started_at AS job_started_at,
              ij.finished_at AS job_finished_at,
              ij.created_at AS job_created_at,
              ij.updated_at AS job_updated_at
            FROM file f
            JOIN theme_file tf ON tf.file_id = f.file_id
            LEFT JOIN LATERAL (
              SELECT
                job_id,
                job_type,
                status,
                stage,
                progress_percent,
                attempt,
                error,
                result,
                started_at,
                finished_at,
                created_at,
                updated_at
              FROM ingest_job
              WHERE file_id = f.file_id
              ORDER BY created_at DESC
              LIMIT 1
            ) ij ON TRUE
            WHERE tf.theme_id = :theme_id
              AND f.file_id = :file_id
            """
        ),
        {"theme_id": theme_id, "file_id": file_id},
    )
    return result.mappings().first()


async def _update_job_control_status(
    session: AsyncSession,
    job_id: str,
    status: str,
    stage: str,
    progress_percent: int,
    error: str | None,
    set_finished_at: bool = False,
    clear_started_at: bool = False,
    clear_finished_at: bool = False,
) -> None:
    await session.execute(
        text(
            """
            UPDATE ingest_job
            SET status = :status,
                stage = :stage,
                progress_percent = :progress_percent,
                error = :error,
                started_at = CASE WHEN :clear_started_at THEN NULL ELSE started_at END,
                finished_at = CASE
                  WHEN :clear_finished_at THEN NULL
                  WHEN :set_finished_at THEN NOW()
                  ELSE finished_at
                END,
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
            "set_finished_at": set_finished_at,
            "clear_started_at": clear_started_at,
            "clear_finished_at": clear_finished_at,
        },
    )


def _file_response_from_row(row) -> dict:
    return {
        "file_id": str(row["file_id"]),
        "filename": row["filename"],
        "content_type": row["content_type"],
        "ingest_status": row["ingest_status"],
        "ingest_error": row["ingest_error"],
        "indexed_chunks": row["indexed_chunks"],
        "indexed_at": row["indexed_at"].isoformat() if row["indexed_at"] else None,
        "latest_job": _job_response(row),
    }


def _file_response(
    prepared: dict,
    ingest_status: str,
    ingest_error: str | None = None,
    indexed_chunks: int = 0,
) -> dict:
    latest_job = prepared.get("latest_job")
    if not latest_job and prepared.get("job_id"):
        latest_job = {
            "job_id": str(prepared["job_id"]),
            "job_type": prepared.get("job_type"),
            "status": "queued",
            "stage": "queued",
            "progress_percent": 0,
            "attempt": None,
            "error": None,
            "result": None,
            "started_at": None,
            "finished_at": None,
            "created_at": None,
            "updated_at": None,
        }
    return {
        "file_id": str(prepared["file_id"]),
        "filename": prepared["filename"],
        "content_type": prepared["content_type"],
        "ingest_status": prepared.get("ingest_status") or ingest_status,
        "ingest_error": ingest_error,
        "indexed_chunks": indexed_chunks,
        "latest_job": latest_job,
    }


def _queue_jobs_response(jobs: list[dict]) -> dict:
    queued_jobs = [job for job in jobs if job["status"] == "queued"]
    dead_letter_jobs = [job for job in jobs if job["status"] == "dead_letter"]
    return {
        "queued": len(queued_jobs),
        "dead_lettered": len(dead_letter_jobs),
        "job_ids": [job["job_id"] for job in queued_jobs],
        "dead_letter_job_ids": [job["job_id"] for job in dead_letter_jobs],
    }


def _count_rows(rows) -> dict[str, int]:
    return {str(row["status"]): int(row["count"]) for row in rows}


def _round_float(value) -> float | None:
    return round(float(value), 3) if value is not None else None


def _isoformat(value) -> str | None:
    return value.isoformat() if value else None


def _job_response(row) -> dict | None:
    if not row.get("job_id"):
        return None
    result = row.get("job_result")
    return {
        "job_id": str(row["job_id"]),
        "job_type": row["job_type"],
        "status": row["job_status"],
        "stage": row["job_stage"],
        "progress_percent": row["job_progress_percent"],
        "attempt": row["job_attempt"],
        "error": row["job_error"],
        "result": result,
        "started_at": row["job_started_at"].isoformat() if row["job_started_at"] else None,
        "finished_at": row["job_finished_at"].isoformat() if row["job_finished_at"] else None,
        "created_at": row["job_created_at"].isoformat() if row["job_created_at"] else None,
        "updated_at": row["job_updated_at"].isoformat() if row["job_updated_at"] else None,
    }


def _to_ascii_filename(filename: str) -> str:
    source = Path(filename or "document")
    ext = source.suffix.lower()
    basename = source.name[: -len(source.suffix)] if source.suffix else source.name
    ascii_name = unidecode(basename).lower()
    safe_name = re.sub(r"[^a-z0-9._-]", "_", ascii_name).strip("_")
    return f"{safe_name or 'document'}{ext}"
