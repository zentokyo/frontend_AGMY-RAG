import uuid

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter

from src.api.question.schemas import CreateQuestionSchema, CreateQuestionListSchema, \
    QuestionWithThemeResponseSchema
from src.core.assistant.dto.question import CreateQuestionDTO, CreateQuestionListDTO
from src.core.assistant.use_cases.question import CreateQuestionUseCase, GetQuestionListUseCase, GetQuestionUseCase, \
    CreateQuestionListUseCase

question_router = APIRouter(prefix="/questions", tags=["Questions"])


@question_router.post("/")
@inject
async def create_question_handler(
        schema: CreateQuestionSchema,
        use_case: FromDishka[CreateQuestionUseCase],
) -> QuestionWithThemeResponseSchema:
    """Создать новый вопрос"""

    dto = CreateQuestionDTO(
        text=schema.text,
        theme_id=schema.theme_id,
        answer_text=schema.answer_text,
    )

    question = await use_case(create_question_dto=dto)

    return QuestionWithThemeResponseSchema.from_entity(question)


@question_router.post("/bulk/")
@inject
async def create_question_list_handler(
        schema: CreateQuestionListSchema,
        use_case: FromDishka[CreateQuestionListUseCase],
) -> list[QuestionWithThemeResponseSchema]:
    """Массовое создание вопросов"""

    dto = CreateQuestionListDTO(
        [
            CreateQuestionDTO(text=question.text, theme_id=question.theme_id, answer_text=question.answer_text)
            for question in schema.question_list
        ]
    )

    question_list = await use_case(create_question_list_dto=dto)

    return [QuestionWithThemeResponseSchema.from_entity(question) for question in question_list]


@question_router.get("/")
@inject
async def get_question_list_handler(
        use_case: FromDishka[GetQuestionListUseCase],
) -> list[QuestionWithThemeResponseSchema]:
    """Получить список имеющихся вопросов"""

    question_list = await use_case()

    return [QuestionWithThemeResponseSchema.from_entity(question) for question in question_list]


@question_router.get("/{question_id}/")
@inject
async def get_question_handler(
        question_id: uuid.UUID,
        use_case: FromDishka[GetQuestionUseCase],
) -> QuestionWithThemeResponseSchema:
    """Получить один вопрос по его id"""

    question = await use_case(question_id=question_id)

    return QuestionWithThemeResponseSchema.from_entity(question)
