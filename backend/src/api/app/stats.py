from uuid import UUID

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.commons.internal_auth import require_internal_token
from src.api.commons.public_auth import get_app_user_id, require_app_auth

app_stats_router = APIRouter(
    prefix="/internal/app",
    tags=["Internal App Stats"],
    dependencies=[Depends(require_internal_token)],
)
public_app_stats_router = APIRouter(
    prefix="/api/app",
    tags=["App Stats"],
    dependencies=[Depends(require_app_auth)],
)


@app_stats_router.get("/users/{user_id}/stats/all")
@public_app_stats_router.get("/stats/all")
@inject
async def get_all_stats_handler(
    request: Request,
    session: FromDishka[AsyncSession],
) -> dict:
    user_id = get_app_user_id(request)
    total_result = await session.execute(
        text(
            """
            SELECT
              COUNT(*)::int AS total_answers,
              COALESCE(SUM(CASE WHEN a.is_correct THEN 1 ELSE 0 END), 0)::int AS correct_answers
            FROM answer a
            JOIN exam_question eq ON eq.exam_question_id = a.exam_question_id
            JOIN exam e ON e.exam_id = eq.exam_id
            WHERE e.user_id = :user_id
            """
        ),
        {"user_id": user_id},
    )
    total = dict(total_result.mappings().first() or {"total_answers": 0, "correct_answers": 0})

    by_theme_result = await session.execute(
        text(
            """
            SELECT
              et.title AS theme_title,
              COUNT(*)::int AS total_answers,
              COALESCE(SUM(CASE WHEN a.is_correct THEN 1 ELSE 0 END), 0)::int AS correct_answers
            FROM answer a
            JOIN exam_question eq ON eq.exam_question_id = a.exam_question_id
            JOIN exam e ON e.exam_id = eq.exam_id
            JOIN exam_theme et ON et.exam_theme_id = e.exam_theme_id
            WHERE e.user_id = :user_id
            GROUP BY et.title
            ORDER BY et.title ASC
            """
        ),
        {"user_id": user_id},
    )

    stat_by_theme = []
    for row in by_theme_result.mappings().all():
        item = dict(row)
        item["accuracy"] = _accuracy(item["total_answers"], item["correct_answers"])
        stat_by_theme.append(item)

    return {
        "total_answers": total["total_answers"],
        "correct_answers": total["correct_answers"],
        "accuracy": _accuracy(total["total_answers"], total["correct_answers"]),
        "stat_by_theme": stat_by_theme,
    }


@app_stats_router.get("/users/{user_id}/stats/last")
@public_app_stats_router.get("/stats/last")
@inject
async def get_last_stats_handler(
    request: Request,
    session: FromDishka[AsyncSession],
):
    user_id = get_app_user_id(request)
    exam_result = await session.execute(
        text(
            """
            SELECT exam_id, exam_theme_id
            FROM exam
            WHERE user_id = :user_id AND status = :status
            ORDER BY end_exam DESC NULLS LAST, start_exam DESC
            LIMIT 1
            """
        ),
        {"user_id": user_id, "status": "Выполнен"},
    )
    exam = exam_result.mappings().first()
    if not exam:
        return JSONResponse(status_code=404, content={"error": "No completed exams"})

    stat_result = await session.execute(
        text(
            """
            SELECT
              COUNT(*)::int AS total_answers,
              COALESCE(SUM(CASE WHEN a.is_correct THEN 1 ELSE 0 END), 0)::int AS correct_answers
            FROM answer a
            JOIN exam_question eq ON eq.exam_question_id = a.exam_question_id
            WHERE eq.exam_id = :exam_id
            """
        ),
        {"exam_id": exam["exam_id"]},
    )
    totals = dict(stat_result.mappings().first() or {"total_answers": 0, "correct_answers": 0})

    answer_result = await session.execute(
        text(
            """
            SELECT
              q.text AS question_text,
              a.answer_text AS user_answer,
              q.answer_text AS model_answer,
              a.is_correct
            FROM answer a
            JOIN exam_question eq ON eq.exam_question_id = a.exam_question_id
            JOIN question q ON q.question_id = eq.question_id
            WHERE eq.exam_id = :exam_id
            ORDER BY eq.exam_question_id ASC
            """
        ),
        {"exam_id": exam["exam_id"]},
    )
    answer_list = [dict(row) for row in answer_result.mappings().all()]

    theme_result = await session.execute(
        text("SELECT title FROM exam_theme WHERE exam_theme_id = :exam_theme_id"),
        {"exam_theme_id": exam["exam_theme_id"]},
    )
    theme = theme_result.mappings().first()

    return {
        "exam_id": _json_uuid(exam["exam_id"]),
        "theme_title": theme["title"] if theme else None,
        "total_answers": totals["total_answers"],
        "correct_answers": totals["correct_answers"],
        "accuracy": _accuracy(totals["total_answers"], totals["correct_answers"]),
        "answer_list": answer_list,
    }


def _accuracy(total_answers: int, correct_answers: int) -> float:
    return correct_answers / total_answers if total_answers else 0


def _json_uuid(value) -> str | None:
    if isinstance(value, UUID):
        return str(value)
    return str(value) if value is not None else None
