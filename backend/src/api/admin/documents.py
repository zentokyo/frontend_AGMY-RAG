import re
from pathlib import Path
from uuid import UUID, uuid4

from aiobotocore.client import AioBaseClient
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

ALLOWED_MIMES = {
    "application/pdf",
    "text/plain",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
ALLOWED_EXTS = {".pdf", ".txt", ".docx"}
MAX_SIZE_BYTES = 50 * 1024 * 1024

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
              f.filename
            FROM theme t
            LEFT JOIN theme_file tf ON tf.theme_id = t.theme_id
            LEFT JOIN file f ON f.file_id = tf.file_id
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

        uploaded_files = []
        for prepared in prepared_files:
            file_id = uuid4()
            await _upload_to_s3(s3_client, prepared)
            await session.execute(
                text("INSERT INTO file (file_id, filename) VALUES (:file_id, :filename)"),
                {"file_id": file_id, "filename": prepared["filename"]},
            )
            await session.execute(
                text(
                    """
                    INSERT INTO theme_file (theme_id, file_id)
                    VALUES (:theme_id, :file_id)
                    """
                ),
                {"theme_id": theme_id, "file_id": file_id},
            )
            uploaded_files.append({"file_id": str(file_id), "filename": prepared["filename"]})

    return JSONResponse(
        status_code=201,
        content={
            "id": str(theme_id),
            "title": title_value,
            "theme_order": next_order,
            "files": uploaded_files,
            "file_count": len(uploaded_files),
        },
    )


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
        if not theme_result.mappings().first():
            return JSONResponse(status_code=404, content={"error": "Theme not found"})

        added_files = []
        for prepared in prepared_files:
            file_id = uuid4()
            await _upload_to_s3(s3_client, prepared)
            await session.execute(
                text("INSERT INTO file (file_id, filename) VALUES (:file_id, :filename)"),
                {"file_id": file_id, "filename": prepared["filename"]},
            )
            await session.execute(
                text(
                    """
                    INSERT INTO theme_file (theme_id, file_id)
                    VALUES (:theme_id, :file_id)
                    """
                ),
                {"theme_id": theme_id, "file_id": file_id},
            )
            added_files.append({"file_id": str(file_id), "filename": prepared["filename"]})

    return JSONResponse(status_code=201, content={"added": added_files, "theme_id": str(theme_id)})


@admin_documents_router.delete("/{theme_id}")
@public_admin_documents_router.delete("/{theme_id}")
@inject
async def delete_admin_document_handler(
    theme_id: UUID,
    session: FromDishka[AsyncSession],
    s3_client: FromDishka[AioBaseClient],
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


async def _delete_from_s3(s3_client: AioBaseClient, filename: str) -> None:
    try:
        await s3_client.delete_object(Bucket=config.minio.bucket, Key=filename)
    except ClientError:
        pass


def _to_ascii_filename(filename: str) -> str:
    source = Path(filename or "document")
    ext = source.suffix.lower()
    basename = source.name[: -len(source.suffix)] if source.suffix else source.name
    ascii_name = unidecode(basename).lower()
    safe_name = re.sub(r"[^a-z0-9._-]", "_", ascii_name).strip("_")
    return f"{safe_name or 'document'}{ext}"
