from uuid import UUID, uuid4

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.commons.internal_auth import require_internal_token
from src.api.commons.public_auth import require_admin_auth

admin_questions_router = APIRouter(
    prefix="/internal/admin/questions",
    tags=["Internal Admin Questions"],
    dependencies=[Depends(require_internal_token)],
)
public_admin_questions_router = APIRouter(
    prefix="/api/questions",
    tags=["Admin Questions"],
    dependencies=[Depends(require_admin_auth)],
)


class UpsertAdminQuestionRequest(BaseModel):
    text: str | None = None
    answer_text: str | None = None
    theme_id: UUID | None = None


@admin_questions_router.get("/stats")
@public_admin_questions_router.get("/stats")
@inject
async def get_admin_question_stats_handler(
    session: FromDishka[AsyncSession],
) -> dict:
    total_result = await session.execute(text("SELECT COUNT(*) AS total FROM question"))
    by_theme_result = await session.execute(
        text(
            """
            SELECT t.title AS theme, COUNT(q.question_id) AS count
            FROM question q
            JOIN theme t ON t.theme_id = q.theme_id
            GROUP BY t.title
            ORDER BY count DESC
            LIMIT 10
            """
        )
    )
    return {
        "total": int(total_result.mappings().first()["total"]),
        "by_theme": [dict(row) for row in by_theme_result.mappings().all()],
    }


@admin_questions_router.get("/themes")
@public_admin_questions_router.get("/themes")
@inject
async def get_admin_question_themes_handler(
    session: FromDishka[AsyncSession],
) -> list[dict]:
    result = await session.execute(
        text("SELECT theme_id AS id, title FROM theme ORDER BY theme_order ASC")
    )
    return [{"id": _json_uuid(row["id"]), "title": row["title"]} for row in result.mappings().all()]


@admin_questions_router.get("")
@public_admin_questions_router.get("")
@inject
async def get_admin_questions_handler(
    session: FromDishka[AsyncSession],
    page: int = Query(default=1),
    limit: int = Query(default=20),
    search: str = Query(default=""),
    theme_id: UUID | None = Query(default=None),
) -> dict:
    page = max(int(page or 1), 1)
    limit = min(max(int(limit or 20), 1), 100)
    offset = (page - 1) * limit

    conditions = []
    params: dict = {}
    if search:
        conditions.append("(q.text ILIKE :search OR q.answer_text ILIKE :search)")
        params["search"] = f"%{search}%"
    if theme_id:
        conditions.append("q.theme_id = :theme_id")
        params["theme_id"] = theme_id

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    count_result = await session.execute(text(f"SELECT COUNT(*) FROM question q {where}"), params)
    total = int(count_result.mappings().first()["count"])

    data_result = await session.execute(
        text(
            f"""
            SELECT
              q.question_id AS id,
              q.text,
              q.answer_text,
              q.theme_id,
              t.title AS theme_title
            FROM question q
            JOIN theme t ON t.theme_id = q.theme_id
            {where}
            ORDER BY t.theme_order ASC, q.text ASC
            LIMIT :limit OFFSET :offset
            """
        ),
        {**params, "limit": limit, "offset": offset},
    )

    return {
        "data": [_question_row(row) for row in data_result.mappings().all()],
        "pagination": {
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit,
        },
    }


@admin_questions_router.post("")
@public_admin_questions_router.post("")
@inject
async def create_admin_question_handler(
    schema: UpsertAdminQuestionRequest,
    session: FromDishka[AsyncSession],
):
    question_text = schema.text.strip() if schema.text else ""
    answer_text = schema.answer_text.strip() if schema.answer_text else ""
    if not question_text:
        return JSONResponse(status_code=400, content={"error": "text is required"})
    if not answer_text:
        return JSONResponse(status_code=400, content={"error": "answer_text is required"})
    if not schema.theme_id:
        return JSONResponse(status_code=400, content={"error": "theme_id is required"})

    async with session.begin():
        theme = await _get_theme(session, schema.theme_id)
        if not theme:
            return JSONResponse(status_code=400, content={"error": "Theme not found"})

        question_id = uuid4()
        await session.execute(
            text(
                """
                INSERT INTO question (question_id, theme_id, text, answer_text)
                VALUES (:question_id, :theme_id, :text, :answer_text)
                """
            ),
            {
                "question_id": question_id,
                "theme_id": schema.theme_id,
                "text": question_text,
                "answer_text": answer_text,
            },
        )

    return JSONResponse(
        status_code=201,
        content={
            "id": str(question_id),
            "text": question_text,
            "answer_text": answer_text,
            "theme_id": str(schema.theme_id),
            "theme_title": theme["title"],
        },
    )


@admin_questions_router.put("/{question_id}")
@public_admin_questions_router.put("/{question_id}")
@inject
async def update_admin_question_handler(
    question_id: UUID,
    schema: UpsertAdminQuestionRequest,
    session: FromDishka[AsyncSession],
):
    text_value = schema.text.strip() if schema.text and schema.text.strip() else None
    answer_value = schema.answer_text.strip() if schema.answer_text and schema.answer_text.strip() else None

    async with session.begin():
        existing_result = await session.execute(
            text("SELECT question_id FROM question WHERE question_id = :question_id"),
            {"question_id": question_id},
        )
        if not existing_result.mappings().first():
            return JSONResponse(status_code=404, content={"error": "Question not found"})

        if schema.theme_id and not await _get_theme(session, schema.theme_id):
            return JSONResponse(status_code=400, content={"error": "Theme not found"})

        await session.execute(
            text(
                """
                UPDATE question
                SET text = COALESCE(:text, text),
                    answer_text = COALESCE(:answer_text, answer_text),
                    theme_id = COALESCE(:theme_id, theme_id)
                WHERE question_id = :question_id
                """
            ),
            {
                "text": text_value,
                "answer_text": answer_value,
                "theme_id": schema.theme_id,
                "question_id": question_id,
            },
        )

        result = await session.execute(
            text(
                """
                SELECT q.question_id AS id, q.text, q.answer_text, q.theme_id, t.title AS theme_title
                FROM question q
                JOIN theme t ON t.theme_id = q.theme_id
                WHERE q.question_id = :question_id
                """
            ),
            {"question_id": question_id},
        )
        row = result.mappings().first()

    return _question_row(row)


@admin_questions_router.delete("/{question_id}")
@public_admin_questions_router.delete("/{question_id}")
@inject
async def delete_admin_question_handler(
    question_id: UUID,
    session: FromDishka[AsyncSession],
):
    async with session.begin():
        result = await session.execute(
            text("DELETE FROM question WHERE question_id = :question_id RETURNING question_id"),
            {"question_id": question_id},
        )
        if not result.mappings().first():
            return JSONResponse(status_code=404, content={"error": "Question not found"})

    return {"message": "Question deleted"}


async def _get_theme(session: AsyncSession, theme_id: UUID):
    result = await session.execute(
        text("SELECT theme_id, title FROM theme WHERE theme_id = :theme_id"),
        {"theme_id": theme_id},
    )
    return result.mappings().first()


def _question_row(row) -> dict:
    return {
        "id": _json_uuid(row["id"]),
        "text": row["text"],
        "answer_text": row["answer_text"],
        "theme_id": _json_uuid(row["theme_id"]),
        "theme_title": row["theme_title"],
    }


def _json_uuid(value) -> str | None:
    if isinstance(value, UUID):
        return str(value)
    return str(value) if value is not None else None
