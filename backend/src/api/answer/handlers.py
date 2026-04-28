import uuid

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter

from src.api.answer.schemas import CreateAnswerSchema, AnswerResponseSchema
from src.core.assistant.dto.answer import CreateAnswerDTO
from src.core.assistant.use_cases.answer import CreateAnswerUseCase, GetUserAnswerListByExamIdUseCase, \
    GetAllUsersAnswerUseCase

answer_router = APIRouter(prefix="/answers", tags=["Answers"])


@answer_router.post("/")
@inject
async def create_answer_handler(
        schema: CreateAnswerSchema,
        use_case: FromDishka[CreateAnswerUseCase],
) -> AnswerResponseSchema:
    """Дать ответ на вопрос"""

    dto = CreateAnswerDTO(
        user_id=schema.user_id,
        answer_text=schema.answer_text,
    )

    answer = await use_case(dto)

    return AnswerResponseSchema.from_entity(answer)


@answer_router.get("/exams/{exam_id}/")
@inject
async def get_answer_list_by_exam_id_handler(
        exam_id: uuid.UUID,
        use_case: FromDishka[GetUserAnswerListByExamIdUseCase],
) -> list[AnswerResponseSchema]:
    """Получить список ответов по id экзаменационной сессии"""
    answer_list = await use_case(exam_id)

    return [AnswerResponseSchema.from_entity(answer) for answer in answer_list]


@answer_router.get("/users/{user_id}/")
@inject
async def get_answer_list_by_user_id_handler(
        user_id: int,
        use_case: FromDishka[GetAllUsersAnswerUseCase],
) -> list[AnswerResponseSchema]:
    """Получить список всех ответов пользователя"""
    answer_list = await use_case(user_id)

    return [AnswerResponseSchema.from_entity(answer) for answer in answer_list]
