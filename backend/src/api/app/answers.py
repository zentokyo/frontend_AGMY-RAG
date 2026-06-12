import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID, uuid4

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, BackgroundTasks, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.api.commons.internal_auth import require_internal_token
from src.api.commons.public_auth import get_app_user_id, require_app_auth
from src.core.rag import DeepSeekFlashLLM, QdrantKnowledgeStore, answer_question, check_response_against_expected

logger = logging.getLogger(__name__)

PASS_THRESHOLD = 0.7
ANSWERED_STATUS = "На вопрос дан ответ"
UNANSWERED_STATUS = "На вопрос нет ответа"
COMPLETED_STATUS = "Выполнен"
EVALUATION_PENDING = "pending"
EVALUATION_EVALUATING = "evaluating"
EVALUATION_DONE = "done"
EVALUATION_FAILED = "failed"

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
    background_tasks: BackgroundTasks,
    session: FromDishka[AsyncSession],
    session_maker: FromDishka[async_sessionmaker[AsyncSession]],
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
              q.theme_id,
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

    answer_id = uuid4()
    left_count = 0

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
                INSERT INTO answer (
                  answer_id,
                  exam_question_id,
                  answer_text,
                  is_correct,
                  evaluation_status,
                  evaluation_method,
                  evaluation_error
                )
                VALUES (
                  :answer_id,
                  :exam_question_id,
                  :answer_text,
                  NULL,
                  :evaluation_status,
                  NULL,
                  NULL
                )
                """
            ),
            {
                "answer_id": answer_id,
                "exam_question_id": schema.exam_question_id,
                "answer_text": answer_text,
                "evaluation_status": EVALUATION_PENDING,
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
    background_tasks.add_task(
        _evaluate_answer_background,
        session_maker,
        model,
        db,
        answer_id,
    )

    response = {
        "exam_id": _json_uuid(item["exam_id"]),
        "exam_question_id": str(schema.exam_question_id),
        "answer_recorded": True,
        "evaluation_status": EVALUATION_PENDING,
        "method": "queued_background_evaluation",
        "completed": completed,
        "result_ready": False,
        "left_count": left_count,
    }
    return response


async def _evaluate_answer_background(
    session_maker: async_sessionmaker[AsyncSession],
    model: DeepSeekFlashLLM,
    db: QdrantKnowledgeStore,
    answer_id: UUID,
) -> None:
    item = None
    try:
        async with session_maker() as session:
            item = await _get_answer_for_evaluation(session, answer_id)
            if not item:
                logger.warning("Answer %s not found for background evaluation", answer_id)
                return
            await session.execute(
                text(
                    """
                    UPDATE answer
                    SET evaluation_status = :status,
                        evaluation_error = NULL
                    WHERE answer_id = :answer_id
                    """
                ),
                {"answer_id": answer_id, "status": EVALUATION_EVALUATING},
            )
            await session.commit()

        rag_result = await _evaluate_answer(
            question=item["question_text"],
            answer=item["user_answer"],
            expected_answer=item["expected_answer"],
            theme_id=str(item["theme_id"]) if item["theme_id"] else None,
            theme_title=item["theme_title"],
            model=model,
            db=db,
        )
        is_correct = rag_result["is_correct"]
        method = rag_result["method"]
        if is_correct is None:
            is_correct = _normalize(item["user_answer"]) == _normalize(str(item["expected_answer"] or ""))
            method = "expected_exact_fallback" if is_correct else "python_qdrant_rag_unknown"

        async with session_maker() as session:
            async with session.begin():
                await session.execute(
                    text(
                        """
                        UPDATE answer
                        SET is_correct = :is_correct,
                            evaluation_status = :status,
                            evaluation_method = :method,
                            evaluation_error = NULL
                        WHERE answer_id = :answer_id
                        """
                    ),
                    {
                        "answer_id": answer_id,
                        "is_correct": is_correct,
                        "status": EVALUATION_DONE,
                        "method": method,
                    },
                )
                await _complete_exam_if_ready(session, item["exam_id"])
    except Exception as exc:
        logger.exception("Background answer evaluation failed for answer %s", answer_id)
        if item:
            async with session_maker() as session:
                async with session.begin():
                    await session.execute(
                        text(
                            """
                            UPDATE answer
                            SET is_correct = FALSE,
                                evaluation_status = :status,
                                evaluation_method = :method,
                                evaluation_error = :error
                            WHERE answer_id = :answer_id
                            """
                        ),
                        {
                            "answer_id": answer_id,
                            "status": EVALUATION_FAILED,
                            "method": "background_error",
                            "error": str(exc)[:2000],
                        },
                    )
                    await _complete_exam_if_ready(session, item["exam_id"])


async def _get_answer_for_evaluation(session: AsyncSession, answer_id: UUID):
    result = await session.execute(
        text(
            """
            SELECT
              a.answer_id,
              a.answer_text AS user_answer,
              eq.exam_question_id,
              eq.exam_id,
              q.text AS question_text,
              q.answer_text AS expected_answer,
              q.theme_id,
              e.user_id,
              e.exam_scope,
              e.block_topic_id,
              e.course_block_id,
              et.title AS theme_title
            FROM answer a
            JOIN exam_question eq ON eq.exam_question_id = a.exam_question_id
            JOIN exam e ON e.exam_id = eq.exam_id
            JOIN question q ON q.question_id = eq.question_id
            LEFT JOIN exam_theme et ON et.exam_theme_id = e.exam_theme_id
            WHERE a.answer_id = :answer_id
            """
        ),
        {"answer_id": answer_id},
    )
    return result.mappings().first()


async def _complete_exam_if_ready(session: AsyncSession, exam_id) -> None:
    exam_result = await session.execute(
        text(
            """
            SELECT
              exam_id,
              user_id,
              status,
              exam_scope,
              block_topic_id,
              course_block_id
            FROM exam
            WHERE exam_id = :exam_id
            """
        ),
        {"exam_id": exam_id},
    )
    exam = exam_result.mappings().first()
    if not exam or exam["status"] == COMPLETED_STATUS:
        return

    status_result = await session.execute(
        text(
            """
            SELECT
              COALESCE(SUM(CASE WHEN eq.status = :unanswered_status THEN 1 ELSE 0 END), 0)::int AS unanswered,
              COALESCE(SUM(CASE
                WHEN a.evaluation_status IN (:pending_status, :evaluating_status) THEN 1
                ELSE 0
              END), 0)::int AS pending_evaluations
            FROM exam_question eq
            LEFT JOIN answer a ON a.exam_question_id = eq.exam_question_id
            WHERE eq.exam_id = :exam_id
            """
        ),
        {
            "exam_id": exam_id,
            "unanswered_status": UNANSWERED_STATUS,
            "pending_status": EVALUATION_PENDING,
            "evaluating_status": EVALUATION_EVALUATING,
        },
    )
    status = status_result.mappings().first()
    if status["unanswered"] > 0 or status["pending_evaluations"] > 0:
        return

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
        {"exam_id": exam_id},
    )
    totals = score_result.mappings().first()
    score = totals["correct"] / totals["total"] if totals["total"] else 0
    is_passed = score >= PASS_THRESHOLD
    progress_status = "passed" if is_passed else "failed"

    await session.execute(
        text(
            """
            UPDATE exam
            SET status = :completed_status, end_exam = NOW()
            WHERE exam_id = :exam_id
            """
        ),
        {"exam_id": exam_id, "completed_status": COMPLETED_STATUS},
    )

    await _update_course_progress(
        session=session,
        user_id=exam["user_id"],
        exam_id=exam_id,
        exam_scope=exam["exam_scope"],
        block_topic_id=exam["block_topic_id"],
        course_block_id=exam["course_block_id"],
        progress_status=progress_status,
        score=score,
        is_passed=is_passed,
    )


async def _evaluate_answer(
    *,
    question: str,
    answer: str,
    expected_answer: str | None,
    theme_id: str | None,
    theme_title: str | None,
    model: DeepSeekFlashLLM,
    db: QdrantKnowledgeStore,
) -> dict:
    if expected_answer and _normalize(answer) == _normalize(expected_answer):
        return {"is_correct": True, "method": "python_expected_exact"}

    if expected_answer:
        expected_verdict, expected_explanation = check_response_against_expected(
            question=question,
            response_text=answer,
            expected_answer=expected_answer,
            model=model,
        )
        if expected_verdict is not None:
            return {
                "is_correct": expected_verdict,
                "method": "python_expected_semantic",
                "explanation": expected_explanation,
            }

    try:
        result = await asyncio.to_thread(
            answer_question,
            question,
            answer,
            model,
            db=db,
            theme_id=theme_id,
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
