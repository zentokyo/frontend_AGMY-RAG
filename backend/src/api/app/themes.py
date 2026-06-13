from uuid import UUID

from aiobotocore.client import AioBaseClient
from botocore.exceptions import ClientError
from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.commons.internal_auth import require_internal_token
from src.api.commons.public_auth import require_app_auth
from src.config import config

app_themes_router = APIRouter(
    prefix="/internal/app",
    tags=["Internal App Themes"],
    dependencies=[Depends(require_internal_token)],
)
public_app_themes_router = APIRouter(
    prefix="/api/app",
    tags=["App Themes"],
    dependencies=[Depends(require_app_auth)],
)


@app_themes_router.get("/themes")
@public_app_themes_router.get("/themes")
@inject
async def get_themes_handler(
    session: FromDishka[AsyncSession],
) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
              t.theme_id,
              t.title,
              t.theme_order,
              COUNT(tf.file_id)::int AS file_count
            FROM theme t
            LEFT JOIN theme_file tf ON tf.theme_id = t.theme_id
            GROUP BY t.theme_id, t.title, t.theme_order
            ORDER BY t.theme_order ASC
            """
        )
    )

    return [
        {
            "theme_id": _json_uuid(row["theme_id"]),
            "title": row["title"],
            "theme_order": row["theme_order"],
            "file_count": row["file_count"],
        }
        for row in result.mappings().all()
    ]


@app_themes_router.get("/themes/{theme_id}/download")
@public_app_themes_router.get("/themes/{theme_id}/download")
@inject
async def get_theme_download_metadata_handler(
    theme_id: UUID,
    session: FromDishka[AsyncSession],
):
    result = await session.execute(
        text(
            """
            SELECT f.file_id, f.filename
            FROM theme_file tf
            JOIN file f ON f.file_id = tf.file_id
            WHERE tf.theme_id = :theme_id
            ORDER BY f.filename ASC
            """
        ),
        {"theme_id": theme_id},
    )
    files = [
        {
            "file_id": _json_uuid(row["file_id"]),
            "filename": row["filename"],
        }
        for row in result.mappings().all()
    ]
    if not files:
        return JSONResponse(status_code=404, content={"error": "Theme files not found"})

    return {
        "theme_id": str(theme_id),
        "files": files,
        "download_type": "metadata",
        "message": "ZIP streaming will be added in the next iteration",
    }


@public_app_themes_router.get("/files/{filename}")
@inject
async def download_file_handler(
    filename: str,
    s3_client: FromDishka[AioBaseClient],
):
    try:
        response = await s3_client.get_object(Bucket=config.minio.bucket, Key=filename)
        return StreamingResponse(
            response["Body"],
            media_type=response.get("ContentType", "application/octet-stream"),
        )
    except ClientError:
        return JSONResponse(status_code=404, content={"error": "File not found"})


def _json_uuid(value) -> str | None:
    if isinstance(value, UUID):
        return str(value)
    return str(value) if value is not None else None
