import uuid

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter

from src.api.stat.schema import StatResponseSchema, StatWithAnswerListShortResponseSchema, TotalStatResponseSchema
from src.core.assistant.use_cases.stat import GetStatByExamIdUseCase, GetAllUsersStatUseCase, GetUserStatForLastExam

stat_router = APIRouter(prefix="/stats", tags=["Stats"])


@stat_router.get("/exams/{exam_id}/")
@inject
async def get_exam_stat_by_exam_id_use_case(
        exam_id: uuid.UUID,
        use_case: FromDishka[GetStatByExamIdUseCase],
) -> StatResponseSchema:
    """Получить статистику по экзаменационной сессии"""
    stat = await use_case(exam_id)

    return StatResponseSchema.from_entity(stat)


@stat_router.get("/users/{user_id}/all/")
@inject
async def get_all_user_stat(
        user_id: int,
        use_case: FromDishka[GetAllUsersStatUseCase],
) -> TotalStatResponseSchema:
    """Получить полную статистику пользователя"""
    total_stat = await use_case(user_id)

    return TotalStatResponseSchema.from_entity(total_stat)


@stat_router.get("/users/{user_id}/last/")
@inject
async def get_last_user_exam_stat(
        user_id: int,
        use_case: FromDishka[GetUserStatForLastExam],
) -> StatWithAnswerListShortResponseSchema:
    """Получить статистику пользователя по последней экзаменационной сессии со списком ответов"""
    stat = await use_case(user_id)

    return StatWithAnswerListShortResponseSchema.from_entity(stat)
