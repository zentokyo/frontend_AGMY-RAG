import uuid

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter

from src.api.exam_theme.schemas import CreateExamThemeSchema, ExamThemeResponseSchema, UserExamThemeResponseSchema
from src.core.assistant.dto.exam_theme import CreateExamThemeDTO
from src.core.assistant.use_cases.exam_theme import CreateExamThemeUseCase, GetExamThemeListUseCase, \
    GetExamThemeUseCase, GetUserExamListUseCase

exam_theme_router = APIRouter(prefix="/exams/themes", tags=["Exams Themes"])


@exam_theme_router.post("/")
@inject
async def create_exam_theme_handler(
        schema: CreateExamThemeSchema,
        use_case: FromDishka[CreateExamThemeUseCase],
) -> ExamThemeResponseSchema:
    """
    Создать тему экзамена
    """

    dto = CreateExamThemeDTO(
        title=schema.title,
    )

    theme = await use_case(dto)

    return ExamThemeResponseSchema.from_entity(theme)


@exam_theme_router.get("/")
@inject
async def get_exam_theme_list_handler(
        use_case: FromDishka[GetExamThemeListUseCase],
) -> list[ExamThemeResponseSchema]:
    """
    Получить список экзаменационных тем
    """

    exam_theme_list = await use_case()

    return [ExamThemeResponseSchema.from_entity(exam_theme) for exam_theme in exam_theme_list]


@exam_theme_router.get("/{exam_theme_id}/")
@inject
async def get_exam_theme_handler(
        exam_theme_id: uuid.UUID,
        use_case: FromDishka[GetExamThemeUseCase]
) -> ExamThemeResponseSchema:
    """
    Получить экзаменационную тему по id
    """

    exam_theme = await use_case(exam_theme_id)

    return ExamThemeResponseSchema.from_entity(exam_theme)


@exam_theme_router.get("/users/{user_id}")
@inject
async def get_user_exam_theme_list_handler(
        user_id: int,
        use_case: FromDishka[GetUserExamListUseCase],
) -> list[UserExamThemeResponseSchema]:
    user_exam_theme_list = await use_case(user_id)

    return [UserExamThemeResponseSchema.from_entity(user_exam_theme) for user_exam_theme in user_exam_theme_list]
