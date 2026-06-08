from datetime import datetime, timezone
from uuid import UUID, uuid4

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.commons.internal_auth import require_internal_token
from src.api.commons.public_auth import get_app_user_id, require_app_auth

app_exams_router = APIRouter(
    prefix="/internal/app",
    tags=["Internal App Exams"],
    dependencies=[Depends(require_internal_token)],
)
public_app_exams_router = APIRouter(
    prefix="/api/app",
    tags=["App Exams"],
    dependencies=[Depends(require_app_auth)],
)


class CreateAppExamRequest(BaseModel):
    question_count: int = 10
    exam_theme_id: UUID | None = None


@app_exams_router.get("/exam-themes")
@public_app_exams_router.get("/exam-themes")
@inject
async def get_exam_themes_handler(
    session: FromDishka[AsyncSession],
) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT exam_theme_id, title, exam_theme_order
            FROM exam_theme
            ORDER BY exam_theme_order ASC
            """
        )
    )

    return [
        {
            "exam_theme_id": str(row["exam_theme_id"]),
            "title": row["title"],
            "exam_theme_order": row["exam_theme_order"],
            "is_enable": True,
        }
        for row in result.mappings().all()
    ]


@app_exams_router.post("/users/{user_id}/exams")
@public_app_exams_router.post("/exams")
@inject
async def create_exam_handler(
    request: Request,
    schema: CreateAppExamRequest,
    session: FromDishka[AsyncSession],
):
    user_id = get_app_user_id(request)
    count = max(1, min(int(schema.question_count or 10), 10))

    async with session.begin():
        in_work_result = await session.execute(
            text(
                """
                SELECT exam_id, exam_theme_id, question_count, status, start_exam
                FROM exam
                WHERE user_id = :user_id AND status = :status
                ORDER BY start_exam DESC
                LIMIT 1
                """
            ),
            {"user_id": user_id, "status": "В работе"},
        )
        in_work = in_work_result.mappings().first()
        if in_work:
            return JSONResponse(
                status_code=409,
                content={"error": "User already has active exam", "exam": _exam_row(in_work)},
            )

        chosen_theme_id = schema.exam_theme_id
        if chosen_theme_id is None:
            theme_result = await session.execute(
                text(
                    """
                    SELECT exam_theme_id
                    FROM exam_theme
                    ORDER BY exam_theme_order ASC
                    LIMIT 1
                    """
                )
            )
            theme = theme_result.mappings().first()
            chosen_theme_id = theme["exam_theme_id"] if theme else None

        if not chosen_theme_id:
            return JSONResponse(status_code=400, content={"error": "No exam themes available"})

        exam_id = uuid4()
        await session.execute(
            text(
                """
                INSERT INTO exam (exam_id, user_id, exam_theme_id, type, question_count, status, start_exam, end_exam, rate)
                VALUES (:exam_id, :user_id, :exam_theme_id, :type, :question_count, :status, NOW(), NULL, NULL)
                """
            ),
            {
                "exam_id": exam_id,
                "user_id": user_id,
                "exam_theme_id": chosen_theme_id,
                "type": "Итоговый экзамен",
                "question_count": count,
                "status": "В работе",
            },
        )

        await _get_or_create_exam_questions(session, exam_id, chosen_theme_id, count)

        exam_result = await session.execute(
            text(
                """
                SELECT exam_id, exam_theme_id, question_count, status, start_exam
                FROM exam
                WHERE exam_id = :exam_id
                """
            ),
            {"exam_id": exam_id},
        )
        exam = exam_result.mappings().first()

    return JSONResponse(status_code=201, content=_exam_row(exam))


@app_exams_router.get("/users/{user_id}/exams/in-progress")
@public_app_exams_router.get("/exams/in-progress")
@inject
async def get_in_progress_exam_handler(
    request: Request,
    session: FromDishka[AsyncSession],
):
    user_id = get_app_user_id(request)
    exam_result = await session.execute(
        text(
            """
            SELECT exam_id, exam_theme_id, question_count, status, start_exam
            FROM exam
            WHERE user_id = :user_id AND status = :status
            ORDER BY start_exam DESC
            LIMIT 1
            """
        ),
        {"user_id": user_id, "status": "В работе"},
    )
    exam = exam_result.mappings().first()
    if not exam:
        return JSONResponse(status_code=404, content={"error": "No active exam"})

    return _exam_row(exam)


@app_exams_router.post("/users/{user_id}/exams/{exam_id}/questions/ask")
@public_app_exams_router.post("/exams/{exam_id}/questions/ask")
@inject
async def ask_exam_question_handler(
    request: Request,
    exam_id: UUID,
    session: FromDishka[AsyncSession],
):
    user_id = get_app_user_id(request)
    async with session.begin():
        exam_result = await session.execute(
            text(
                """
                SELECT exam_id, exam_theme_id, question_count, status
                FROM exam
                WHERE exam_id = :exam_id AND user_id = :user_id
                """
            ),
            {"exam_id": exam_id, "user_id": user_id},
        )
        exam = exam_result.mappings().first()
        if not exam:
            return JSONResponse(status_code=404, content={"error": "Exam not found"})
        if exam["status"] != "В работе":
            return JSONResponse(status_code=400, content={"error": "Exam already completed"})

        question_list = await _get_or_create_exam_questions(
            session,
            exam_id,
            exam["exam_theme_id"],
            exam["question_count"],
        )

    next_question = next(
        (question for question in question_list if question["status"] == "На вопрос нет ответа"),
        None,
    )
    if not next_question:
        return JSONResponse(status_code=404, content={"error": "No unanswered questions left"})

    return {
        "exam_id": str(exam_id),
        "question": _question_row(next_question),
    }


@app_exams_router.get("/users/{user_id}/exams/{exam_id}/questions/unanswered")
@public_app_exams_router.get("/exams/{exam_id}/questions/unanswered")
@inject
async def get_unanswered_exam_question_handler(
    request: Request,
    exam_id: UUID,
    session: FromDishka[AsyncSession],
):
    user_id = get_app_user_id(request)
    question_result = await session.execute(
        text(
            """
            SELECT eq.exam_question_id, q.question_id, q.text
            FROM exam_question eq
            JOIN exam e ON e.exam_id = eq.exam_id
            JOIN question q ON q.question_id = eq.question_id
            WHERE e.exam_id = :exam_id
              AND e.user_id = :user_id
              AND eq.status = :status
            ORDER BY eq.exam_question_id ASC
            LIMIT 1
            """
        ),
        {"exam_id": exam_id, "user_id": user_id, "status": "На вопрос нет ответа"},
    )
    question = question_result.mappings().first()
    if not question:
        return JSONResponse(status_code=404, content={"error": "No unanswered question"})

    return {"question": _question_row(question)}


async def _get_or_create_exam_questions(
    session: AsyncSession,
    exam_id,
    exam_theme_id,
    question_count: int,
) -> list[dict]:
    existing_result = await session.execute(
        text(
            """
            SELECT eq.exam_question_id, eq.status, q.question_id, q.text, q.answer_text
            FROM exam_question eq
            JOIN question q ON q.question_id = eq.question_id
            WHERE eq.exam_id = :exam_id
            ORDER BY eq.exam_question_id ASC
            """
        ),
        {"exam_id": exam_id},
    )
    existing = [dict(row) for row in existing_result.mappings().all()]
    if existing:
        return existing

    question_result = await session.execute(
        text(
            """
            SELECT q.question_id, q.text, q.answer_text
            FROM question q
            WHERE q.theme_id = (
              SELECT t.theme_id
              FROM exam_theme et
              JOIN theme t ON t.title = et.title
              WHERE et.exam_theme_id = :exam_theme_id
              LIMIT 1
            )
            ORDER BY q.question_id ASC
            LIMIT :question_count
            """
        ),
        {"exam_theme_id": exam_theme_id, "question_count": question_count},
    )
    picked = [dict(row) for row in question_result.mappings().all()]
    if not picked:
        fallback_result = await session.execute(
            text(
                """
                SELECT question_id, text, answer_text
                FROM question
                ORDER BY question_id ASC
                LIMIT :question_count
                """
            ),
            {"question_count": question_count},
        )
        picked = [dict(row) for row in fallback_result.mappings().all()]

    for question in picked:
        await session.execute(
            text(
                """
                INSERT INTO exam_question (exam_question_id, exam_id, question_id, status)
                VALUES (:exam_question_id, :exam_id, :question_id, :status)
                """
            ),
            {
                "exam_question_id": uuid4(),
                "exam_id": exam_id,
                "question_id": question["question_id"],
                "status": "На вопрос нет ответа",
            },
        )

    created_result = await session.execute(
        text(
            """
            SELECT eq.exam_question_id, eq.status, q.question_id, q.text, q.answer_text
            FROM exam_question eq
            JOIN question q ON q.question_id = eq.question_id
            WHERE eq.exam_id = :exam_id
            ORDER BY eq.exam_question_id ASC
            """
        ),
        {"exam_id": exam_id},
    )
    return [dict(row) for row in created_result.mappings().all()]


def _exam_row(row) -> dict:
    return {
        "exam_id": _json_uuid(row["exam_id"]),
        "exam_theme_id": _json_uuid(row["exam_theme_id"]),
        "question_count": row["question_count"],
        "status": row["status"],
        "start_exam": _json_datetime(row["start_exam"]),
    }


def _question_row(row) -> dict:
    return {
        "exam_question_id": _json_uuid(row["exam_question_id"]),
        "question_id": _json_uuid(row["question_id"]),
        "text": row["text"],
    }


def _json_uuid(value) -> str | None:
    if isinstance(value, UUID):
        return str(value)
    return str(value) if value is not None else None


def _json_datetime(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat().replace("+00:00", "Z")
    return str(value)
