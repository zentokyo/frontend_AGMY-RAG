from uuid import UUID

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.commons.internal_auth import require_internal_token
from src.api.commons.public_auth import require_admin_auth

COMPLETED_STATUS = "Выполнен"
IN_PROGRESS_STATUS = "В работе"
PASSING_STATUS = "passed"
PENDING_EVALUATION_STATUSES = ("pending", "evaluating")

admin_progress_router = APIRouter(
    prefix="/internal/admin/progress",
    tags=["Internal Admin Progress"],
    dependencies=[Depends(require_internal_token)],
)
public_admin_progress_router = APIRouter(
    prefix="/api/progress",
    tags=["Admin Progress"],
    dependencies=[Depends(require_admin_auth)],
)


@admin_progress_router.get("/overview")
@public_admin_progress_router.get("/overview")
@inject
async def get_admin_progress_overview_handler(
    session: FromDishka[AsyncSession],
) -> dict:
    summary_result = await session.execute(
        text(
            """
            SELECT
              (SELECT COUNT(*)::int FROM app_users) AS total_users,
              (SELECT COUNT(DISTINCT user_id)::int FROM exam) AS users_with_exams,
              (SELECT COUNT(*)::int FROM course_block) AS total_blocks,
              (SELECT COUNT(*)::int FROM block_topic WHERE theme_id IS NOT NULL) AS total_topics,
              (SELECT COUNT(*)::int FROM exam) AS total_exams,
              (SELECT COUNT(*)::int FROM exam WHERE status = :completed_status) AS completed_exams,
              (SELECT COUNT(*)::int FROM exam WHERE status = :in_progress_status) AS in_progress_exams,
              (SELECT COUNT(*)::int FROM answer) AS total_answers,
              (SELECT COUNT(*)::int FROM answer WHERE is_correct IS TRUE) AS correct_answers,
              (SELECT COUNT(*)::int FROM answer WHERE evaluation_status = ANY(:pending_statuses)) AS pending_evaluations,
              (SELECT COUNT(*)::int FROM answer WHERE evaluation_status = 'failed') AS failed_evaluations,
              (SELECT COUNT(*)::int FROM user_topic_progress WHERE status = :passing_status) AS passed_topic_records,
              (SELECT COUNT(*)::int FROM user_block_progress WHERE status = :passing_status) AS passed_block_records,
              (SELECT COUNT(*)::int FROM user_course_progress WHERE status = :passing_status) AS course_passed_users
            """
        ),
        _base_params(),
    )
    summary = dict(summary_result.mappings().first())
    summary["accuracy"] = _ratio(summary["correct_answers"], summary["total_answers"])

    activity_result = await session.execute(
        text(
            """
            WITH exam_scores AS (
              SELECT
                e.exam_id,
                DATE_TRUNC('day', COALESCE(e.end_exam, e.start_exam))::date AS day,
                e.status,
                COUNT(a.answer_id)::int AS total_answers,
                COALESCE(SUM(CASE WHEN a.is_correct THEN 1 ELSE 0 END), 0)::int AS correct_answers
              FROM exam e
              LEFT JOIN exam_question eq ON eq.exam_id = e.exam_id
              LEFT JOIN answer a ON a.exam_question_id = eq.exam_question_id
              WHERE COALESCE(e.end_exam, e.start_exam) >= NOW() - INTERVAL '14 days'
              GROUP BY e.exam_id, day, e.status
            )
            SELECT
              day,
              COUNT(*)::int AS total_exams,
              COUNT(*) FILTER (WHERE status = :completed_status)::int AS completed_exams,
              AVG(CASE WHEN total_answers > 0 THEN correct_answers::float / total_answers ELSE NULL END) AS average_score
            FROM exam_scores
            GROUP BY day
            ORDER BY day ASC
            """
        ),
        _base_params(),
    )

    by_scope_result = await session.execute(
        text(
            """
            WITH exam_scores AS (
              SELECT
                e.exam_id,
                COALESCE(e.exam_scope, 'standalone') AS exam_scope,
                e.status,
                COUNT(a.answer_id)::int AS total_answers,
                COALESCE(SUM(CASE WHEN a.is_correct THEN 1 ELSE 0 END), 0)::int AS correct_answers
              FROM exam e
              LEFT JOIN exam_question eq ON eq.exam_id = e.exam_id
              LEFT JOIN answer a ON a.exam_question_id = eq.exam_question_id
              GROUP BY e.exam_id, e.exam_scope, e.status
            )
            SELECT
              exam_scope,
              COUNT(*)::int AS total_exams,
              COUNT(*) FILTER (WHERE status = :completed_status)::int AS completed_exams,
              AVG(CASE WHEN total_answers > 0 THEN correct_answers::float / total_answers ELSE NULL END) AS average_score
            FROM exam_scores
            GROUP BY exam_scope
            ORDER BY total_exams DESC, exam_scope ASC
            """
        ),
        _base_params(),
    )

    return {
        "summary": summary,
        "activity": [_activity_row(row) for row in activity_result.mappings().all()],
        "by_scope": [_score_row(row) for row in by_scope_result.mappings().all()],
    }


@admin_progress_router.get("/blocks")
@public_admin_progress_router.get("/blocks")
@inject
async def get_admin_progress_blocks_handler(
    session: FromDishka[AsyncSession],
) -> list[dict]:
    block_result = await session.execute(
        text(
            """
            WITH
            block_stats AS (
              SELECT
                block_id,
                COUNT(DISTINCT user_id)::int AS users_with_block_progress,
                COUNT(DISTINCT CASE WHEN status = :passing_status THEN user_id END)::int AS users_passed_block,
                COALESCE(SUM(attempts), 0)::int AS block_attempts,
                AVG(best_score) AS average_block_score
              FROM user_block_progress
              GROUP BY block_id
            ),
            topic_stats AS (
              SELECT
                bt.block_id,
                COUNT(DISTINCT utp.user_id)::int AS users_with_topic_progress,
                COUNT(DISTINCT CASE WHEN utp.status = :passing_status THEN utp.user_id END)::int AS users_passed_any_topic
              FROM block_topic bt
              JOIN user_topic_progress utp ON utp.topic_id = bt.id
              WHERE bt.theme_id IS NOT NULL
              GROUP BY bt.block_id
            )
            SELECT
              cb.id,
              cb.title,
              cb.block_order,
              COUNT(DISTINCT bt.id) FILTER (WHERE bt.theme_id IS NOT NULL)::int AS total_topics,
              COALESCE(bs.users_with_block_progress, 0)::int AS users_with_block_progress,
              COALESCE(bs.users_passed_block, 0)::int AS users_passed_block,
              COALESCE(bs.block_attempts, 0)::int AS block_attempts,
              bs.average_block_score,
              COALESCE(ts.users_with_topic_progress, 0)::int AS users_with_topic_progress,
              COALESCE(ts.users_passed_any_topic, 0)::int AS users_passed_any_topic
            FROM course_block cb
            LEFT JOIN block_topic bt ON bt.block_id = cb.id
            LEFT JOIN block_stats bs ON bs.block_id = cb.id
            LEFT JOIN topic_stats ts ON ts.block_id = cb.id
            GROUP BY
              cb.id,
              cb.title,
              cb.block_order,
              bs.users_with_block_progress,
              bs.users_passed_block,
              bs.block_attempts,
              bs.average_block_score,
              ts.users_with_topic_progress,
              ts.users_passed_any_topic
            ORDER BY cb.block_order ASC, cb.id ASC
            """
        ),
        _base_params(),
    )

    topic_result = await session.execute(
        text(
            """
            SELECT
              cb.id AS block_id,
              bt.id,
              bt.title,
              bt.topic_order,
              COUNT(utp.user_id)::int AS users_started,
              COUNT(*) FILTER (WHERE utp.status = :passing_status)::int AS users_passed,
              COUNT(*) FILTER (WHERE utp.status = 'failed')::int AS users_failed,
              COALESCE(SUM(utp.attempts), 0)::int AS attempts,
              AVG(utp.best_score) AS average_score,
              MAX(utp.updated_at) AS last_activity_at
            FROM course_block cb
            JOIN block_topic bt ON bt.block_id = cb.id
            LEFT JOIN user_topic_progress utp ON utp.topic_id = bt.id
            WHERE bt.theme_id IS NOT NULL
            GROUP BY cb.id, bt.id, bt.title, bt.topic_order
            ORDER BY cb.block_order ASC, bt.topic_order ASC, bt.id ASC
            """
        ),
        _base_params(),
    )

    topics_by_block: dict[int, list[dict]] = {}
    for row in topic_result.mappings().all():
        item = _topic_row(row)
        topics_by_block.setdefault(row["block_id"], []).append(item)

    blocks = []
    for row in block_result.mappings().all():
        block = dict(row)
        block["average_block_score"] = _float(block["average_block_score"])
        block["topics"] = topics_by_block.get(block["id"], [])
        blocks.append(block)
    return blocks


@admin_progress_router.get("/users")
@public_admin_progress_router.get("/users")
@inject
async def get_admin_progress_users_handler(
    session: FromDishka[AsyncSession],
    page: int = Query(default=1),
    limit: int = Query(default=20),
    search: str = Query(default=""),
) -> dict:
    page = max(int(page or 1), 1)
    limit = min(max(int(limit or 20), 1), 100)
    offset = (page - 1) * limit
    search_value = search.strip()
    where = ""
    params: dict = {"limit": limit, "offset": offset}
    if search_value:
        where = "WHERE u.email ILIKE :search OR COALESCE(u.username, '') ILIKE :search"
        params["search"] = f"%{search_value}%"

    total_result = await session.execute(text(f"SELECT COUNT(*)::int AS count FROM app_users u {where}"), params)
    total = int(total_result.mappings().first()["count"])

    data_result = await session.execute(
        text(
            f"""
            WITH
            exam_stats AS (
              SELECT
                e.user_id,
                COUNT(*)::int AS total_exams,
                COUNT(*) FILTER (WHERE e.status = :completed_status)::int AS completed_exams,
                COUNT(*) FILTER (WHERE e.status = :in_progress_status)::int AS in_progress_exams,
                MAX(COALESCE(e.end_exam, e.start_exam)) AS last_activity_at
              FROM exam e
              GROUP BY e.user_id
            ),
            answer_stats AS (
              SELECT
                e.user_id,
                COUNT(a.answer_id)::int AS total_answers,
                COUNT(a.answer_id) FILTER (WHERE a.is_correct IS TRUE)::int AS correct_answers,
                COUNT(a.answer_id) FILTER (WHERE a.evaluation_status = ANY(:pending_statuses))::int AS pending_evaluations
              FROM exam e
              JOIN exam_question eq ON eq.exam_id = e.exam_id
              JOIN answer a ON a.exam_question_id = eq.exam_question_id
              GROUP BY e.user_id
            ),
            topic_stats AS (
              SELECT
                user_id,
                COUNT(*) FILTER (WHERE status = :passing_status)::int AS passed_topics,
                COUNT(*)::int AS touched_topics,
                COALESCE(SUM(attempts), 0)::int AS topic_attempts,
                AVG(best_score) AS average_topic_score
              FROM user_topic_progress
              GROUP BY user_id
            ),
            block_stats AS (
              SELECT
                user_id,
                COUNT(*) FILTER (WHERE status = :passing_status)::int AS passed_blocks,
                COUNT(*)::int AS touched_blocks,
                COALESCE(SUM(attempts), 0)::int AS block_attempts,
                AVG(best_score) AS average_block_score
              FROM user_block_progress
              GROUP BY user_id
            ),
            course_totals AS (
              SELECT
                (SELECT COUNT(*)::int FROM block_topic WHERE theme_id IS NOT NULL) AS total_topics,
                (SELECT COUNT(*)::int FROM course_block) AS total_blocks
            )
            SELECT
              u.id,
              u.email,
              u.username,
              u.created_at,
              COALESCE(es.total_exams, 0)::int AS total_exams,
              COALESCE(es.completed_exams, 0)::int AS completed_exams,
              COALESCE(es.in_progress_exams, 0)::int AS in_progress_exams,
              es.last_activity_at,
              COALESCE(ans.total_answers, 0)::int AS total_answers,
              COALESCE(ans.correct_answers, 0)::int AS correct_answers,
              COALESCE(ans.pending_evaluations, 0)::int AS pending_evaluations,
              COALESCE(ts.passed_topics, 0)::int AS passed_topics,
              COALESCE(ts.touched_topics, 0)::int AS touched_topics,
              COALESCE(ts.topic_attempts, 0)::int AS topic_attempts,
              ts.average_topic_score,
              COALESCE(bs.passed_blocks, 0)::int AS passed_blocks,
              COALESCE(bs.touched_blocks, 0)::int AS touched_blocks,
              COALESCE(bs.block_attempts, 0)::int AS block_attempts,
              bs.average_block_score,
              ucp.status AS course_status,
              ucp.best_score AS course_best_score,
              ucp.attempts AS course_attempts,
              ucp.completed_at,
              ct.total_topics,
              ct.total_blocks
            FROM app_users u
            CROSS JOIN course_totals ct
            LEFT JOIN exam_stats es ON es.user_id = u.id
            LEFT JOIN answer_stats ans ON ans.user_id = u.id
            LEFT JOIN topic_stats ts ON ts.user_id = u.id
            LEFT JOIN block_stats bs ON bs.user_id = u.id
            LEFT JOIN user_course_progress ucp ON ucp.user_id = u.id
            {where}
            ORDER BY es.last_activity_at DESC NULLS LAST, u.created_at DESC, u.id DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        {**_base_params(), **params},
    )

    return {
        "items": [_user_row(row) for row in data_result.mappings().all()],
        "total": total,
        "page": page,
        "limit": limit,
    }


@admin_progress_router.get("/users/{user_id}")
@public_admin_progress_router.get("/users/{user_id}")
@inject
async def get_admin_progress_user_detail_handler(
    user_id: int,
    session: FromDishka[AsyncSession],
) -> dict:
    user_result = await session.execute(
        text(
            """
            SELECT id, email, username, created_at, updated_at
            FROM app_users
            WHERE id = :user_id
            """
        ),
        {"user_id": user_id},
    )
    user = user_result.mappings().first()
    if not user:
        return JSONResponse(status_code=404, content={"error": "User not found"})

    summary_result = await session.execute(
        text(
            """
            SELECT
              COUNT(DISTINCT e.exam_id)::int AS total_exams,
              COUNT(DISTINCT e.exam_id) FILTER (WHERE e.status = :completed_status)::int AS completed_exams,
              COUNT(DISTINCT e.exam_id) FILTER (WHERE e.status = :in_progress_status)::int AS in_progress_exams,
              COUNT(a.answer_id)::int AS total_answers,
              COUNT(a.answer_id) FILTER (WHERE a.is_correct IS TRUE)::int AS correct_answers,
              COUNT(a.answer_id) FILTER (WHERE a.evaluation_status = ANY(:pending_statuses))::int AS pending_evaluations,
              MAX(COALESCE(e.end_exam, e.start_exam)) AS last_activity_at
            FROM app_users u
            LEFT JOIN exam e ON e.user_id = u.id
            LEFT JOIN exam_question eq ON eq.exam_id = e.exam_id
            LEFT JOIN answer a ON a.exam_question_id = eq.exam_question_id
            WHERE u.id = :user_id
            GROUP BY u.id
            """
        ),
        {**_base_params(), "user_id": user_id},
    )
    summary = dict(summary_result.mappings().first())
    summary["accuracy"] = _ratio(summary["correct_answers"], summary["total_answers"])

    course_result = await session.execute(
        text(
            """
            SELECT status, attempts, best_score, last_exam_id, completed_at
            FROM user_course_progress
            WHERE user_id = :user_id
            """
        ),
        {"user_id": user_id},
    )
    course_progress = course_result.mappings().first()

    blocks_result = await session.execute(
        text(
            """
            SELECT
              cb.id,
              cb.title,
              cb.block_order,
              ubp.status,
              ubp.attempts,
              ubp.best_score,
              ubp.last_exam_id,
              ubp.updated_at
            FROM course_block cb
            LEFT JOIN user_block_progress ubp ON ubp.block_id = cb.id AND ubp.user_id = :user_id
            ORDER BY cb.block_order ASC, cb.id ASC
            """
        ),
        {"user_id": user_id},
    )

    topics_result = await session.execute(
        text(
            """
            SELECT
              bt.block_id,
              bt.id,
              bt.title,
              bt.topic_order,
              utp.status,
              utp.attempts,
              utp.best_score,
              utp.last_exam_id,
              utp.updated_at
            FROM block_topic bt
            LEFT JOIN user_topic_progress utp ON utp.topic_id = bt.id AND utp.user_id = :user_id
            WHERE bt.theme_id IS NOT NULL
            ORDER BY bt.block_id ASC, bt.topic_order ASC, bt.id ASC
            """
        ),
        {"user_id": user_id},
    )
    topics_by_block: dict[int, list[dict]] = {}
    for row in topics_result.mappings().all():
        topics_by_block.setdefault(row["block_id"], []).append(_user_topic_row(row))

    blocks = []
    for row in blocks_result.mappings().all():
        block = _user_block_row(row)
        block["topics"] = topics_by_block.get(row["id"], [])
        blocks.append(block)

    exams = await _get_exam_rows(session, user_id=user_id, limit=20)

    return {
        "user": _plain_row(user),
        "summary": _plain_row(summary),
        "course_progress": _course_progress_row(course_progress),
        "blocks": blocks,
        "recent_exams": exams,
    }


@admin_progress_router.get("/exams")
@public_admin_progress_router.get("/exams")
@inject
async def get_admin_progress_exams_handler(
    session: FromDishka[AsyncSession],
    user_id: int | None = Query(default=None),
    limit: int = Query(default=20),
) -> list[dict]:
    limit = min(max(int(limit or 20), 1), 100)
    return await _get_exam_rows(session, user_id=user_id, limit=limit)


async def _get_exam_rows(session: AsyncSession, *, user_id: int | None, limit: int) -> list[dict]:
    where = "WHERE e.user_id = :user_id" if user_id is not None else ""
    params = {**_base_params(), "limit": limit}
    if user_id is not None:
        params["user_id"] = user_id

    result = await session.execute(
        text(
            f"""
            SELECT
              e.exam_id,
              e.user_id,
              u.email,
              u.username,
              e.status,
              COALESCE(e.exam_scope, 'standalone') AS exam_scope,
              e.question_count,
              e.start_exam,
              e.end_exam,
              et.title AS theme_title,
              cb.title AS block_title,
              bt.title AS topic_title,
              COUNT(a.answer_id)::int AS total_answers,
              COUNT(a.answer_id) FILTER (WHERE a.is_correct IS TRUE)::int AS correct_answers,
              COUNT(a.answer_id) FILTER (WHERE a.evaluation_status = ANY(:pending_statuses))::int AS pending_evaluations,
              COUNT(a.answer_id) FILTER (WHERE a.evaluation_status = 'failed')::int AS failed_evaluations
            FROM exam e
            JOIN app_users u ON u.id = e.user_id
            LEFT JOIN exam_theme et ON et.exam_theme_id = e.exam_theme_id
            LEFT JOIN course_block cb ON cb.id = e.course_block_id
            LEFT JOIN block_topic bt ON bt.id = e.block_topic_id
            LEFT JOIN exam_question eq ON eq.exam_id = e.exam_id
            LEFT JOIN answer a ON a.exam_question_id = eq.exam_question_id
            {where}
            GROUP BY
              e.exam_id,
              e.user_id,
              u.email,
              u.username,
              e.status,
              e.exam_scope,
              e.question_count,
              e.start_exam,
              e.end_exam,
              et.title,
              cb.title,
              bt.title
            ORDER BY COALESCE(e.end_exam, e.start_exam) DESC NULLS LAST, e.start_exam DESC
            LIMIT :limit
            """
        ),
        params,
    )
    return [_exam_row(row) for row in result.mappings().all()]


def _base_params() -> dict:
    return {
        "completed_status": COMPLETED_STATUS,
        "in_progress_status": IN_PROGRESS_STATUS,
        "passing_status": PASSING_STATUS,
        "pending_statuses": list(PENDING_EVALUATION_STATUSES),
    }


def _activity_row(row) -> dict:
    item = _plain_row(row)
    item["average_score"] = _float(item["average_score"])
    return item


def _score_row(row) -> dict:
    item = _plain_row(row)
    item["average_score"] = _float(item["average_score"])
    return item


def _topic_row(row) -> dict:
    item = _plain_row(row)
    item["average_score"] = _float(item["average_score"])
    return item


def _user_row(row) -> dict:
    item = _plain_row(row)
    item["accuracy"] = _ratio(item["correct_answers"], item["total_answers"])
    item["topic_progress"] = _ratio(item["passed_topics"], item["total_topics"])
    item["block_progress"] = _ratio(item["passed_blocks"], item["total_blocks"])
    item["average_topic_score"] = _float(item["average_topic_score"])
    item["average_block_score"] = _float(item["average_block_score"])
    item["course_best_score"] = _float(item["course_best_score"])
    item["course_status"] = item["course_status"] or "not_started"
    item["course_attempts"] = int(item["course_attempts"] or 0)
    return item


def _user_block_row(row) -> dict:
    item = _plain_row(row)
    item["status"] = item["status"] or "not_started"
    item["attempts"] = int(item["attempts"] or 0)
    item["best_score"] = _float(item["best_score"])
    item["last_exam_id"] = _json_uuid(item["last_exam_id"])
    return item


def _user_topic_row(row) -> dict:
    item = _plain_row(row)
    item["status"] = item["status"] or "not_started"
    item["attempts"] = int(item["attempts"] or 0)
    item["best_score"] = _float(item["best_score"])
    item["last_exam_id"] = _json_uuid(item["last_exam_id"])
    return item


def _course_progress_row(row) -> dict:
    if not row:
        return {
            "status": "not_started",
            "attempts": 0,
            "best_score": 0,
            "last_exam_id": None,
            "completed_at": None,
        }
    item = _plain_row(row)
    item["best_score"] = _float(item["best_score"])
    item["last_exam_id"] = _json_uuid(item["last_exam_id"])
    return item


def _exam_row(row) -> dict:
    item = _plain_row(row)
    item["exam_id"] = _json_uuid(item["exam_id"])
    item["accuracy"] = _ratio(item["correct_answers"], item["total_answers"])
    item["context_title"] = item["topic_title"] or item["block_title"] or item["theme_title"]
    return item


def _plain_row(row) -> dict:
    item = dict(row)
    for key, value in list(item.items()):
        if isinstance(value, UUID):
            item[key] = str(value)
        elif hasattr(value, "isoformat"):
            item[key] = value.isoformat()
    return item


def _ratio(part: int | float | None, total: int | float | None) -> float:
    total_value = float(total or 0)
    if total_value <= 0:
        return 0
    return float(part or 0) / total_value


def _float(value) -> float:
    return float(value) if value is not None else 0


def _json_uuid(value) -> str | None:
    if isinstance(value, UUID):
        return str(value)
    return str(value) if value is not None else None
