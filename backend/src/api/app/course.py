from uuid import UUID, uuid4

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.commons.internal_auth import require_internal_token
from src.api.commons.public_auth import get_app_user_id, require_app_auth

PASS_THRESHOLD = 0.7
TOPIC_QUESTION_COUNT = 3
BLOCK_QUESTION_COUNT = 10
FINAL_QUESTION_COUNT = 10

app_course_router = APIRouter(
    prefix="/internal/app",
    tags=["Internal App Course"],
    dependencies=[Depends(require_internal_token)],
)
public_app_course_router = APIRouter(
    prefix="/api/app",
    tags=["App Course"],
    dependencies=[Depends(require_app_auth)],
)


@app_course_router.get("/users/{user_id}/course/blocks")
@public_app_course_router.get("/course/blocks")
@inject
async def get_course_blocks_handler(
    request: Request,
    session: FromDishka[AsyncSession],
):
    user_id = get_app_user_id(request)
    blocks_result = await session.execute(
        text(
            """
            SELECT
              cb.id,
              cb.title,
              cb.description,
              cb.block_order,
              COALESCE(ubp.status, 'not_started') AS user_status,
              COALESCE(ubp.best_score, 0)::float AS best_score,
              COALESCE(ubp.attempts, 0)::int AS attempts,
              COUNT(bt.id)::int AS topics_total,
              COUNT(CASE WHEN COALESCE(utp.status, 'not_started') = 'passed' THEN 1 END)::int AS topics_passed
            FROM course_block cb
            LEFT JOIN block_topic bt ON bt.block_id = cb.id
            LEFT JOIN user_topic_progress utp ON utp.topic_id = bt.id AND utp.user_id = :user_id
            LEFT JOIN user_block_progress ubp ON ubp.block_id = cb.id AND ubp.user_id = :user_id
            GROUP BY cb.id, cb.title, cb.description, cb.block_order, ubp.status, ubp.best_score, ubp.attempts
            ORDER BY cb.block_order ASC
            """
        ),
        {"user_id": user_id},
    )
    blocks = [dict(row) for row in blocks_result.mappings().all()]
    result = [
        {
            **block,
            "is_unlocked": index == 0 or blocks[index - 1]["user_status"] == "passed",
        }
        for index, block in enumerate(blocks)
    ]

    progress_result = await session.execute(
        text(
            """
            SELECT status, best_score::float, attempts, completed_at, last_exam_id
            FROM user_course_progress
            WHERE user_id = :user_id
            """
        ),
        {"user_id": user_id},
    )
    course_progress = progress_result.mappings().first()
    all_blocks_passed = bool(result) and all(block["user_status"] == "passed" for block in result)

    return {
        "blocks": result,
        "course_progress": dict(course_progress)
        if course_progress
        else {"status": "not_started", "best_score": 0, "attempts": 0},
        "final_exam_unlocked": all_blocks_passed,
    }


@app_course_router.get("/users/{user_id}/course/blocks/{block_id}")
@public_app_course_router.get("/course/blocks/{block_id}")
@inject
async def get_course_block_handler(
    request: Request,
    block_id: int,
    session: FromDishka[AsyncSession],
):
    user_id = get_app_user_id(request)
    block_result = await session.execute(
        text(
            """
            SELECT
              cb.id,
              cb.title,
              cb.description,
              cb.block_order,
              COALESCE(ubp.status, 'not_started') AS user_status,
              COALESCE(ubp.best_score, 0)::float AS best_score,
              COALESCE(ubp.attempts, 0)::int AS attempts,
              ubp.last_exam_id
            FROM course_block cb
            LEFT JOIN user_block_progress ubp ON ubp.block_id = cb.id AND ubp.user_id = :user_id
            WHERE cb.id = :block_id
            """
        ),
        {"user_id": user_id, "block_id": block_id},
    )
    block = block_result.mappings().first()
    if not block:
        return JSONResponse(status_code=404, content={"error": "Block not found"})

    block_data = dict(block)
    block_unlocked = await _is_block_unlocked(session, user_id, block_data["block_order"])

    topics_result = await session.execute(
        text(
            """
            SELECT
              bt.id,
              bt.title,
              bt.topic_order,
              bt.exam_theme_id,
              bt.theme_id,
              COALESCE(utp.status, 'not_started') AS user_status,
              COALESCE(utp.best_score, 0)::float AS best_score,
              COALESCE(utp.attempts, 0)::int AS attempts,
              utp.last_exam_id
            FROM block_topic bt
            LEFT JOIN user_topic_progress utp ON utp.topic_id = bt.id AND utp.user_id = :user_id
            WHERE bt.block_id = :block_id
            ORDER BY bt.topic_order ASC
            """
        ),
        {"user_id": user_id, "block_id": block_id},
    )
    topics = [dict(row) for row in topics_result.mappings().all()]
    topics_with_unlock = [
        {
            **topic,
            "is_unlocked": block_unlocked and (index == 0 or topics[index - 1]["user_status"] == "passed"),
        }
        for index, topic in enumerate(topics)
    ]
    all_topics_passed = bool(topics) and all(topic["user_status"] == "passed" for topic in topics)

    return {
        "block": {**block_data, "is_unlocked": block_unlocked},
        "topics": topics_with_unlock,
        "block_test_unlocked": all_topics_passed,
    }


@app_course_router.get("/users/{user_id}/course/blocks/{block_id}/topics/{topic_id}")
@public_app_course_router.get("/course/blocks/{block_id}/topics/{topic_id}")
@inject
async def get_course_topic_handler(
    request: Request,
    block_id: int,
    topic_id: int,
    session: FromDishka[AsyncSession],
):
    user_id = get_app_user_id(request)
    topic_result = await session.execute(
        text(
            """
            SELECT
              bt.id,
              bt.title,
              bt.topic_order,
              bt.exam_theme_id,
              bt.theme_id,
              bt.block_id,
              COALESCE(utp.status, 'not_started') AS user_status,
              COALESCE(utp.best_score, 0)::float AS best_score,
              COALESCE(utp.attempts, 0)::int AS attempts,
              utp.last_exam_id
            FROM block_topic bt
            LEFT JOIN user_topic_progress utp ON utp.topic_id = bt.id AND utp.user_id = :user_id
            WHERE bt.id = :topic_id AND bt.block_id = :block_id
            """
        ),
        {"user_id": user_id, "topic_id": topic_id, "block_id": block_id},
    )
    topic = topic_result.mappings().first()
    if not topic:
        return JSONResponse(status_code=404, content={"error": "Topic not found"})
    topic_data = dict(topic)

    block_result = await session.execute(
        text("SELECT block_order FROM course_block WHERE id = :block_id"),
        {"block_id": block_id},
    )
    block = block_result.mappings().first()
    block_unlocked = await _is_block_unlocked(session, user_id, block["block_order"]) if block else False
    topic_unlocked = await _is_topic_unlocked(
        session,
        user_id,
        topic_data["topic_order"],
        block_id,
        block_unlocked,
    )

    materials = []
    if topic_unlocked and topic_data["theme_id"]:
        materials_result = await session.execute(
            text(
                """
                SELECT f.file_id, f.filename
                FROM theme_file tf
                JOIN file f ON f.file_id = tf.file_id
                WHERE tf.theme_id = :theme_id
                ORDER BY f.filename ASC
                """
            ),
            {"theme_id": topic_data["theme_id"]},
        )
        materials = [dict(row) for row in materials_result.mappings().all()]

    question_count = 0
    if topic_data["theme_id"]:
        count_result = await session.execute(
            text("SELECT COUNT(*)::int AS cnt FROM question WHERE theme_id = :theme_id"),
            {"theme_id": topic_data["theme_id"]},
        )
        question_count = count_result.mappings().first()["cnt"]

    return {
        "topic": {**topic_data, "is_unlocked": topic_unlocked},
        "materials": materials,
        "question_count": question_count,
    }


@app_course_router.post("/users/{user_id}/course/topics/{topic_id}/exam")
@public_app_course_router.post("/course/topics/{topic_id}/exam")
@inject
async def create_topic_exam_handler(
    request: Request,
    topic_id: int,
    session: FromDishka[AsyncSession],
):
    user_id = get_app_user_id(request)
    async with session.begin():
        topic_result = await session.execute(
            text(
                """
                SELECT
                  bt.id, bt.title, bt.topic_order, bt.exam_theme_id, bt.theme_id, bt.block_id,
                  cb.block_order
                FROM block_topic bt
                JOIN course_block cb ON cb.id = bt.block_id
                WHERE bt.id = :topic_id
                """
            ),
            {"topic_id": topic_id},
        )
        topic = topic_result.mappings().first()
        if not topic:
            return JSONResponse(status_code=404, content={"error": "Topic not found"})

        block_unlocked = await _is_block_unlocked(session, user_id, topic["block_order"])
        topic_unlocked = await _is_topic_unlocked(
            session,
            user_id,
            topic["topic_order"],
            topic["block_id"],
            block_unlocked,
        )
        if not topic_unlocked:
            return JSONResponse(
                status_code=403,
                content={"error": "Topic is locked. Complete the previous topic first."},
            )

        active_exam = await _get_active_exam(session, user_id)
        if active_exam:
            return JSONResponse(
                status_code=409,
                content={"error": "You have an active exam", "exam_id": _json_uuid(active_exam["exam_id"])},
            )

        question_theme_ids = []
        if topic["theme_id"]:
            question_theme_ids = [topic["theme_id"]]
        elif topic["exam_theme_id"]:
            theme_result = await session.execute(
                text(
                    """
                    SELECT t.theme_id
                    FROM exam_theme et
                    JOIN theme t ON t.title = et.title
                    WHERE et.exam_theme_id = :exam_theme_id
                    LIMIT 1
                    """
                ),
                {"exam_theme_id": topic["exam_theme_id"]},
            )
            theme = theme_result.mappings().first()
            if theme:
                question_theme_ids = [theme["theme_id"]]

        exam_id = await _create_exam_with_questions(
            session,
            user_id=user_id,
            exam_theme_id=topic["exam_theme_id"],
            question_count=TOPIC_QUESTION_COUNT,
            exam_scope="topic",
            block_topic_id=topic_id,
            course_block_id=None,
            question_theme_ids=question_theme_ids,
        )
        if isinstance(exam_id, JSONResponse):
            return exam_id

    return JSONResponse(status_code=201, content={"exam_id": _json_uuid(exam_id)})


@app_course_router.post("/users/{user_id}/course/blocks/{block_id}/exam")
@public_app_course_router.post("/course/blocks/{block_id}/exam")
@inject
async def create_block_exam_handler(
    request: Request,
    block_id: int,
    session: FromDishka[AsyncSession],
):
    user_id = get_app_user_id(request)
    async with session.begin():
        block_result = await session.execute(
            text("SELECT id, block_order FROM course_block WHERE id = :block_id"),
            {"block_id": block_id},
        )
        block = block_result.mappings().first()
        if not block:
            return JSONResponse(status_code=404, content={"error": "Block not found"})

        block_unlocked = await _is_block_unlocked(session, user_id, block["block_order"])
        if not block_unlocked:
            return JSONResponse(
                status_code=403,
                content={"error": "Block is locked. Complete the previous block first."},
            )

        topic_status_result = await session.execute(
            text(
                """
                SELECT
                  COUNT(bt.id)::int AS total,
                  COUNT(CASE WHEN COALESCE(utp.status, 'not_started') = 'passed' THEN 1 END)::int AS passed
                FROM block_topic bt
                LEFT JOIN user_topic_progress utp ON utp.topic_id = bt.id AND utp.user_id = :user_id
                WHERE bt.block_id = :block_id
                """
            ),
            {"user_id": user_id, "block_id": block_id},
        )
        topic_status = topic_status_result.mappings().first()
        if topic_status["total"] == 0:
            return JSONResponse(status_code=400, content={"error": "No topics in this block"})
        if topic_status["passed"] < topic_status["total"]:
            return JSONResponse(
                status_code=403,
                content={
                    "error": "Complete all topics in this block first.",
                    "topics_passed": topic_status["passed"],
                    "topics_total": topic_status["total"],
                },
            )

        active_exam = await _get_active_exam(session, user_id)
        if active_exam:
            return JSONResponse(
                status_code=409,
                content={"error": "You have an active exam", "exam_id": _json_uuid(active_exam["exam_id"])},
            )

        theme_result = await session.execute(
            text(
                """
                SELECT DISTINCT theme_id
                FROM block_topic
                WHERE block_id = :block_id AND theme_id IS NOT NULL
                """
            ),
            {"block_id": block_id},
        )
        question_theme_ids = [row["theme_id"] for row in theme_result.mappings().all()]

        exam_theme_result = await session.execute(
            text(
                """
                SELECT exam_theme_id
                FROM block_topic
                WHERE block_id = :block_id AND exam_theme_id IS NOT NULL
                ORDER BY topic_order ASC
                LIMIT 1
                """
            ),
            {"block_id": block_id},
        )
        exam_theme = exam_theme_result.mappings().first()

        exam_id = await _create_exam_with_questions(
            session,
            user_id=user_id,
            exam_theme_id=exam_theme["exam_theme_id"] if exam_theme else None,
            question_count=BLOCK_QUESTION_COUNT,
            exam_scope="block",
            block_topic_id=None,
            course_block_id=block_id,
            question_theme_ids=question_theme_ids,
        )
        if isinstance(exam_id, JSONResponse):
            return exam_id

    return JSONResponse(status_code=201, content={"exam_id": _json_uuid(exam_id)})


@app_course_router.post("/users/{user_id}/course/final-exam")
@public_app_course_router.post("/course/final-exam")
@inject
async def create_final_exam_handler(
    request: Request,
    session: FromDishka[AsyncSession],
):
    user_id = get_app_user_id(request)
    async with session.begin():
        block_status_result = await session.execute(
            text(
                """
                SELECT
                  COUNT(cb.id)::int AS total,
                  COUNT(CASE WHEN COALESCE(ubp.status, 'not_started') = 'passed' THEN 1 END)::int AS passed
                FROM course_block cb
                LEFT JOIN user_block_progress ubp ON ubp.block_id = cb.id AND ubp.user_id = :user_id
                """
            ),
            {"user_id": user_id},
        )
        block_status = block_status_result.mappings().first()
        if block_status["total"] == 0:
            return JSONResponse(status_code=400, content={"error": "No blocks in course"})
        if block_status["passed"] < block_status["total"]:
            return JSONResponse(
                status_code=403,
                content={
                    "error": "Complete all blocks first.",
                    "blocks_passed": block_status["passed"],
                    "blocks_total": block_status["total"],
                },
            )

        active_exam = await _get_active_exam(session, user_id)
        if active_exam:
            return JSONResponse(
                status_code=409,
                content={"error": "You have an active exam", "exam_id": _json_uuid(active_exam["exam_id"])},
            )

        exam_id = await _create_exam_with_questions(
            session,
            user_id=user_id,
            exam_theme_id=None,
            question_count=FINAL_QUESTION_COUNT,
            exam_scope="final",
            block_topic_id=None,
            course_block_id=None,
            question_theme_ids=[],
        )
        if isinstance(exam_id, JSONResponse):
            return exam_id

    return JSONResponse(status_code=201, content={"exam_id": _json_uuid(exam_id)})


@app_course_router.get("/users/{user_id}/course/exams/{exam_id}/result")
@public_app_course_router.get("/course/exams/{exam_id}/result")
@inject
async def get_course_exam_result_handler(
    request: Request,
    exam_id: UUID,
    session: FromDishka[AsyncSession],
):
    user_id = get_app_user_id(request)
    exam_result = await session.execute(
        text(
            """
            SELECT
              e.exam_id, e.status, e.exam_scope, e.block_topic_id, e.course_block_id, e.exam_theme_id,
              et.title AS theme_title
            FROM exam e
            JOIN exam_theme et ON et.exam_theme_id = e.exam_theme_id
            WHERE e.exam_id = :exam_id AND e.user_id = :user_id
            """
        ),
        {"exam_id": exam_id, "user_id": user_id},
    )
    exam = exam_result.mappings().first()
    if not exam:
        return JSONResponse(status_code=404, content={"error": "Exam not found"})

    stat_result = await session.execute(
        text(
            """
            SELECT
              COUNT(*)::int AS total_answers,
              COALESCE(SUM(CASE WHEN a.is_correct THEN 1 ELSE 0 END), 0)::int AS correct_answers,
              COALESCE(SUM(CASE
                WHEN a.evaluation_status IN ('pending', 'evaluating') THEN 1
                ELSE 0
              END), 0)::int AS pending_evaluations,
              COALESCE(SUM(CASE WHEN a.evaluation_status = 'failed' THEN 1 ELSE 0 END), 0)::int AS failed_evaluations
            FROM answer a
            JOIN exam_question eq ON eq.exam_question_id = a.exam_question_id
            WHERE eq.exam_id = :exam_id
            """
        ),
        {"exam_id": exam_id},
    )
    totals = stat_result.mappings().first()

    answer_result = await session.execute(
        text(
            """
            SELECT
              q.text AS question_text,
              a.answer_text AS user_answer,
              q.answer_text AS model_answer,
              a.is_correct,
              a.evaluation_status,
              a.evaluation_method,
              a.evaluation_error
            FROM answer a
            JOIN exam_question eq ON eq.exam_question_id = a.exam_question_id
            JOIN question q ON q.question_id = eq.question_id
            WHERE eq.exam_id = :exam_id
            ORDER BY eq.exam_question_id ASC
            """
        ),
        {"exam_id": exam_id},
    )
    answer_list = [dict(row) for row in answer_result.mappings().all()]

    total_answers = totals["total_answers"]
    correct_answers = totals["correct_answers"]
    pending_evaluations = totals["pending_evaluations"]
    score = correct_answers / total_answers if total_answers else 0

    context = {}
    if exam["block_topic_id"]:
        topic_result = await session.execute(
            text("SELECT block_id, topic_order FROM block_topic WHERE id = :topic_id"),
            {"topic_id": exam["block_topic_id"]},
        )
        topic = topic_result.mappings().first()
        context = {
            "block_id": topic["block_id"] if topic else None,
            "topic_id": exam["block_topic_id"],
            "topic_order": topic["topic_order"] if topic else None,
        }
    elif exam["course_block_id"]:
        block_result = await session.execute(
            text("SELECT block_order FROM course_block WHERE id = :block_id"),
            {"block_id": exam["course_block_id"]},
        )
        block = block_result.mappings().first()
        context = {
            "block_id": exam["course_block_id"],
            "block_order": block["block_order"] if block else None,
        }

    return {
        "exam_id": _json_uuid(exam_id),
        "exam_scope": exam["exam_scope"] or "standalone",
        "status": exam["status"],
        "theme_title": exam["theme_title"],
        "total_answers": total_answers,
        "correct_answers": correct_answers,
        "pending_evaluations": pending_evaluations,
        "failed_evaluations": totals["failed_evaluations"],
        "result_ready": exam["status"] == "Выполнен" and pending_evaluations == 0,
        "score": score,
        "is_passed": score >= PASS_THRESHOLD,
        "pass_threshold": PASS_THRESHOLD,
        "answer_list": answer_list,
        "context": context,
    }


async def _get_active_exam(session: AsyncSession, user_id: int):
    result = await session.execute(
        text(
            """
            SELECT exam_id
            FROM exam
            WHERE user_id = :user_id AND status = 'В работе'
            LIMIT 1
            """
        ),
        {"user_id": user_id},
    )
    return result.mappings().first()


async def _is_block_unlocked(session: AsyncSession, user_id: int, block_order: int) -> bool:
    min_result = await session.execute(text("SELECT MIN(block_order) AS min_order FROM course_block"))
    min_order = min_result.mappings().first()["min_order"]
    if not min_order or block_order == min_order:
        return True

    prev_result = await session.execute(
        text(
            """
            SELECT block_order
            FROM course_block
            WHERE block_order < :block_order
            ORDER BY block_order DESC
            LIMIT 1
            """
        ),
        {"block_order": block_order},
    )
    previous = prev_result.mappings().first()
    if not previous:
        return True

    progress_result = await session.execute(
        text(
            """
            SELECT ubp.status
            FROM user_block_progress ubp
            JOIN course_block cb ON cb.id = ubp.block_id
            WHERE ubp.user_id = :user_id AND cb.block_order = :block_order
            """
        ),
        {"user_id": user_id, "block_order": previous["block_order"]},
    )
    progress = progress_result.mappings().first()
    return progress["status"] == "passed" if progress else False


async def _is_topic_unlocked(
    session: AsyncSession,
    user_id: int,
    topic_order: int,
    block_id: int,
    block_unlocked: bool,
) -> bool:
    if not block_unlocked:
        return False

    min_result = await session.execute(
        text("SELECT MIN(topic_order) AS min_order FROM block_topic WHERE block_id = :block_id"),
        {"block_id": block_id},
    )
    min_order = min_result.mappings().first()["min_order"]
    if not min_order or topic_order == min_order:
        return True

    prev_result = await session.execute(
        text(
            """
            SELECT topic_order
            FROM block_topic
            WHERE block_id = :block_id AND topic_order < :topic_order
            ORDER BY topic_order DESC
            LIMIT 1
            """
        ),
        {"block_id": block_id, "topic_order": topic_order},
    )
    previous = prev_result.mappings().first()
    if not previous:
        return True

    progress_result = await session.execute(
        text(
            """
            SELECT utp.status
            FROM user_topic_progress utp
            JOIN block_topic bt ON bt.id = utp.topic_id
            WHERE utp.user_id = :user_id
              AND bt.block_id = :block_id
              AND bt.topic_order = :topic_order
            """
        ),
        {"user_id": user_id, "block_id": block_id, "topic_order": previous["topic_order"]},
    )
    progress = progress_result.mappings().first()
    return progress["status"] == "passed" if progress else False


async def _create_exam_with_questions(
    session: AsyncSession,
    *,
    user_id: int,
    exam_theme_id,
    question_count: int,
    exam_scope: str,
    block_topic_id: int | None,
    course_block_id: int | None,
    question_theme_ids: list,
):
    if question_theme_ids:
        question_result = await session.execute(
            text(
                """
                SELECT question_id
                FROM question
                WHERE theme_id = ANY(:question_theme_ids)
                ORDER BY RANDOM()
                LIMIT :question_count
                """
            ),
            {"question_theme_ids": question_theme_ids, "question_count": question_count},
        )
    else:
        question_result = await session.execute(
            text(
                """
                SELECT question_id
                FROM question
                ORDER BY RANDOM()
                LIMIT :question_count
                """
            ),
            {"question_count": question_count},
        )
    question_rows = question_result.mappings().all()
    if not question_rows:
        return JSONResponse(status_code=400, content={"error": "No questions available for this exam"})

    actual_theme_id = exam_theme_id
    if not actual_theme_id:
        theme_result = await session.execute(
            text("SELECT exam_theme_id FROM exam_theme ORDER BY exam_theme_order ASC LIMIT 1")
        )
        theme = theme_result.mappings().first()
        actual_theme_id = theme["exam_theme_id"] if theme else None
    if not actual_theme_id:
        return JSONResponse(status_code=400, content={"error": "No exam theme available"})

    exam_id = uuid4()
    exam_type = "Итоговый экзамен" if exam_scope == "final" else "Не итоговый экзамен"
    await session.execute(
        text(
            """
            INSERT INTO exam (
              exam_id, user_id, exam_theme_id, type, question_count, status,
              start_exam, end_exam, rate, exam_scope, block_topic_id, course_block_id
            )
            VALUES (
              :exam_id, :user_id, :exam_theme_id, :type, :question_count, 'В работе',
              NOW(), NULL, NULL, :exam_scope, :block_topic_id, :course_block_id
            )
            """
        ),
        {
            "exam_id": exam_id,
            "user_id": user_id,
            "exam_theme_id": actual_theme_id,
            "type": exam_type,
            "question_count": len(question_rows),
            "exam_scope": exam_scope,
            "block_topic_id": block_topic_id,
            "course_block_id": course_block_id,
        },
    )

    for question in question_rows:
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

    return exam_id


def _json_uuid(value) -> str | None:
    if isinstance(value, UUID):
        return str(value)
    return str(value) if value is not None else None
