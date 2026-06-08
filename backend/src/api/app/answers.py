import asyncio
import logging
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
from src.core.rag import DeepSeekFlashLLM, QdrantKnowledgeStore, answer_question

logger = logging.getLogger(__name__)

PASS_THRESHOLD = 0.7
ANSWERED_STATUS = "На вопрос дан ответ"
UNANSWERED_STATUS = "На вопрос нет ответа"
COMPLETED_STATUS = "Выполнен"

app_answers_router = APIRouter(
    prefix="/internal/app",
    tags=["Internal App Answers"],
    dependencies=[Depends(require_internal_token)],
)
public_app_answers_router = APIRouter(
    prefix="/api/app",
    tags=["App Answers"],
    dependencies=[Depends(require_app_auth)],
)


class CreateAppAnswerRequest(BaseModel):
    exam_question_id: UUID
    answer_text: str


@app_answers_router.post("/users/{user_id}/answers")
@public_app_answers_router.post("/answers")
@inject
async def create_app_answer_handler(
    request: Request,
    schema: CreateAppAnswerRequest,
    session: FromDishka[AsyncSession],
    model: FromDishka[DeepSeekFlashLLM],
    db: FromDishka[QdrantKnowledgeStore],
):
    user_id = get_app_user_id(request)
    answer_text = schema.answer_text.strip()
    if not answer_text:
        return JSONResponse(
            status_code=400,
            content={"error": "exam_question_id and answer_text are required"},
        )

    item_result = await session.execute(
        text(
            """
            SELECT
              eq.exam_question_id,
              eq.exam_id,
              eq.status,
              q.answer_text,
              q.text,
              e.exam_theme_id,
              e.exam_scope,
              e.block_topic_id,
              e.course_block_id,
              et.title AS theme_title
            FROM exam_question eq
            JOIN exam e ON e.exam_id = eq.exam_id
            JOIN question q ON q.question_id = eq.question_id
            LEFT JOIN exam_theme et ON et.exam_theme_id = e.exam_theme_id
            WHERE eq.exam_question_id = :exam_question_id AND e.user_id = :user_id
            """
        ),
        {"exam_question_id": schema.exam_question_id, "user_id": user_id},
    )
    item = item_result.mappings().first()
    if not item:
        return JSONResponse(status_code=404, content={"error": "Question not found"})
    if item["status"] != UNANSWERED_STATUS:
        return JSONResponse(status_code=409, content={"error": "Question already answered"})

    await session.commit()

    rag_result = await _evaluate_answer(
        question=item["text"],
        answer=answer_text,
        expected_answer=item["answer_text"],
        theme_title=item["theme_title"],
        model=model,
        db=db,
    )
    is_correct = rag_result["is_correct"]
    if is_correct is None:
        is_correct = _normalize(answer_text) == _normalize(str(item["answer_text"] or ""))

    completed = False
    left_count = 0
    is_passed = None
    score = None

    async with session.begin():
        updated_result = await session.execute(
            text(
                """
                UPDATE exam_question
                SET status = :answered_status
                WHERE exam_question_id = :exam_question_id AND status = :unanswered_status
                RETURNING exam_question_id
                """
            ),
            {
                "exam_question_id": schema.exam_question_id,
                "answered_status": ANSWERED_STATUS,
                "unanswered_status": UNANSWERED_STATUS,
            },
        )
        if not updated_result.mappings().first():
            return JSONResponse(status_code=409, content={"error": "Question already answered"})

        await session.execute(
            text(
                """
                INSERT INTO answer (answer_id, exam_question_id, answer_text, is_correct)
                VALUES (:answer_id, :exam_question_id, :answer_text, :is_correct)
                """
            ),
            {
                "answer_id": uuid4(),
                "exam_question_id": schema.exam_question_id,
                "answer_text": answer_text,
                "is_correct": is_correct,
            },
        )

        pending_result = await session.execute(
            text(
                """
                SELECT COUNT(*)::int AS left_count
                FROM exam_question
                WHERE exam_id = :exam_id AND status = :unanswered_status
                """
            ),
            {"exam_id": item["exam_id"], "unanswered_status": UNANSWERED_STATUS},
        )
        left_count = pending_result.mappings().first()["left_count"]
        completed = left_count == 0

        if completed:
            await session.execute(
                text(
                    """
                    UPDATE exam
                    SET status = :completed_status, end_exam = NOW()
                    WHERE exam_id = :exam_id
                    """
                ),
                {"exam_id": item["exam_id"], "completed_status": COMPLETED_STATUS},
            )

            score_result = await session.execute(
                text(
                    """
                    SELECT
                      COUNT(*)::int AS total,
                      COALESCE(SUM(CASE WHEN a.is_correct THEN 1 ELSE 0 END), 0)::int AS correct
                    FROM answer a
                    JOIN exam_question eq ON eq.exam_question_id = a.exam_question_id
                    WHERE eq.exam_id = :exam_id
                    """
                ),
                {"exam_id": item["exam_id"]},
            )
            totals = score_result.mappings().first()
            score = totals["correct"] / totals["total"] if totals["total"] else 0
            is_passed = score >= PASS_THRESHOLD
            progress_status = "passed" if is_passed else "failed"

            await _update_course_progress(
                session=session,
                user_id=user_id,
                exam_id=item["exam_id"],
                exam_scope=item["exam_scope"],
                block_topic_id=item["block_topic_id"],
                course_block_id=item["course_block_id"],
                progress_status=progress_status,
                score=score,
                is_passed=is_passed,
            )

    response = {
        "exam_id": _json_uuid(item["exam_id"]),
        "exam_question_id": str(schema.exam_question_id),
        "is_correct": is_correct,
        "method": rag_result["method"],
        "completed": completed,
        "left_count": left_count,
    }
    if completed:
        response.update({"is_passed": is_passed, "score": score})
    return response


async def _evaluate_answer(
    *,
    question: str,
    answer: str,
    expected_answer: str | None,
    theme_title: str | None,
    model: DeepSeekFlashLLM,
    db: QdrantKnowledgeStore,
) -> dict:
    if expected_answer and _normalize(answer) == _normalize(expected_answer):
        return {"is_correct": True, "method": "python_expected_exact"}

    try:
        result = await asyncio.to_thread(
            answer_question,
            question,
            answer,
            model,
            db=db,
            theme_title=theme_title,
            use_assertion_splitting=True,
            use_query_decomposition=True,
            use_reranking=False,
        )
    except Exception as exc:
        logger.warning("Python RAG failed for app answer: %s", exc)
        result = None

    if result is None:
        return {"is_correct": None, "method": "python_qdrant_rag_unknown"}

    return {"is_correct": result, "method": "python_qdrant_rag"}


async def _update_course_progress(
    *,
    session: AsyncSession,
    user_id: int,
    exam_id,
    exam_scope: str | None,
    block_topic_id: int | None,
    course_block_id: int | None,
    progress_status: str,
    score: float,
    is_passed: bool,
) -> None:
    if exam_scope == "topic" and block_topic_id:
        await session.execute(
            text(
                """
                INSERT INTO user_topic_progress (user_id, topic_id, status, attempts, best_score, last_exam_id, updated_at)
                VALUES (:user_id, :topic_id, :status, 1, CAST(:score AS numeric), :exam_id, NOW())
                ON CONFLICT (user_id, topic_id) DO UPDATE SET
                  status = :status,
                  attempts = user_topic_progress.attempts + 1,
                  best_score = GREATEST(user_topic_progress.best_score, CAST(:score AS numeric)),
                  last_exam_id = :exam_id,
                  updated_at = NOW()
                """
            ),
            {
                "user_id": user_id,
                "topic_id": block_topic_id,
                "status": progress_status,
                "score": score,
                "exam_id": exam_id,
            },
        )

    if exam_scope == "block" and course_block_id:
        await session.execute(
            text(
                """
                INSERT INTO user_block_progress (user_id, block_id, status, attempts, best_score, last_exam_id, updated_at)
                VALUES (:user_id, :block_id, :status, 1, CAST(:score AS numeric), :exam_id, NOW())
                ON CONFLICT (user_id, block_id) DO UPDATE SET
                  status = :status,
                  attempts = user_block_progress.attempts + 1,
                  best_score = GREATEST(user_block_progress.best_score, CAST(:score AS numeric)),
                  last_exam_id = :exam_id,
                  updated_at = NOW()
                """
            ),
            {
                "user_id": user_id,
                "block_id": course_block_id,
                "status": progress_status,
                "score": score,
                "exam_id": exam_id,
            },
        )

    if exam_scope == "final":
        await session.execute(
            text(
                """
                INSERT INTO user_course_progress (user_id, status, attempts, best_score, last_exam_id, completed_at)
                VALUES (:user_id, :status, 1, CAST(:score AS numeric), :exam_id, :completed_at)
                ON CONFLICT (user_id) DO UPDATE SET
                  status = :status,
                  attempts = user_course_progress.attempts + 1,
                  best_score = GREATEST(user_course_progress.best_score, CAST(:score AS numeric)),
                  last_exam_id = :exam_id,
                  completed_at = :completed_at
                """
            ),
            {
                "user_id": user_id,
                "status": progress_status,
                "score": score,
                "exam_id": exam_id,
                "completed_at": datetime.now(timezone.utc) if is_passed else None,
            },
        )


def _normalize(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _json_uuid(value) -> str | None:
    if isinstance(value, UUID):
        return str(value)
    return str(value) if value is not None else None
