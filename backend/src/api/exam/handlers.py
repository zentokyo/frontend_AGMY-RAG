import uuid

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter

from src.api.exam.schemas import ExamResponseSchema, CreateExamSchema, CreateExamQuestionResponseSchema, \
    ExamQuestionListResponseSchema, ExamQuestionResponseSchema
from src.core.assistant.dto.exam import CreateExamDTO
from src.core.assistant.dto.exam_question import AskExamQuestionDTO
from src.core.assistant.use_cases.exam import CreateExamUseCase, GetExamUseCase, GetUsersExamUseCase, \
    GetUserInWorkExamUseCase
from src.core.assistant.use_cases.exam_question import AskExamQuestionUseCase, GetExamQuestionListUseCase, \
    GetUserExamQuestionListUseCase, GetUnansweredUserExamQuestion

exam_router = APIRouter(prefix="/exams", tags=["Exams"])


@exam_router.post("/")
@inject
async def create_exam_handler(
        schema: CreateExamSchema,
        use_case: FromDishka[CreateExamUseCase],
) -> ExamResponseSchema:
    """
    Создать экзаменационную сессию. Экзаменационная сессия может быть находящейся в работе и завершенной.
    Каждый пользователь может иметь только одну находящуюся в работе экзаменационную сессию.

    user_id - id пользователя
    question_count - количество вопросов в экзаменационной сессии (от 1 до 10)
    """

    dto = CreateExamDTO(
        user_id=schema.user_id,
        question_count=schema.question_count,
        exam_theme_id=schema.exam_theme_id,
    )

    exam = await use_case(create_exam_dto=dto)

    return ExamResponseSchema.from_entity(exam)


@exam_router.get("/{exam_id}/")
@inject
async def get_exam_handler(
        exam_id: uuid.UUID,
        use_case: FromDishka[GetExamUseCase],
) -> ExamResponseSchema:
    """
    Получить экзаменационную сессию по id
    """
    exam = await use_case(exam_id=exam_id)

    return ExamResponseSchema.from_entity(exam)


@exam_router.get("/{exam_id}/questions/")
@inject
async def get_exam_handler(
        exam_id: uuid.UUID,
        use_case: FromDishka[GetExamQuestionListUseCase],
) -> ExamQuestionListResponseSchema:
    """
    Находит все вопросы для конкретной экзаменационной сессии
    """

    exam_question_list = await use_case(exam_id=exam_id)

    return ExamQuestionListResponseSchema.from_entity(exam_question_list)


@exam_router.get("/users/{user_id}/")
@inject
async def get_users_exam_list_handler(
        user_id: int,
        use_case: FromDishka[GetUsersExamUseCase],
) -> list[ExamResponseSchema]:
    """
    Получить список всех экзаменационных сессий пользователя
    """

    exam_list = await use_case(user_id=user_id)

    return [ExamResponseSchema.from_entity(exam) for exam in exam_list]


@exam_router.get("/users/{user_id}/work/")
@inject
async def get_users_exam_in_work_handler(
        user_id: int,
        use_case: FromDishka[GetUserInWorkExamUseCase],
) -> ExamResponseSchema:
    """
    Получить находящуюся в работе экзаменационную сессию пользователя
    """

    exam = await use_case(user_id=user_id)

    return ExamResponseSchema.from_entity(exam)


@exam_router.post("/users/{user_id}/questions/ask/")
@inject
async def ask_question_handler(
        user_id: int,
        use_case: FromDishka[AskExamQuestionUseCase],
) -> CreateExamQuestionResponseSchema:
    """
    Задать вопрос пользователю.

    Находит актуальную экзаменационную сессию пользователя,
    достает из базы данных вопрос, который еще не был задан пользователю в текущей экзаменационной сессии.
    """

    ask_question_dto = AskExamQuestionDTO(
        user_id=user_id,
    )

    question = await use_case(ask_question_dto)

    return CreateExamQuestionResponseSchema.from_entity(question)


@exam_router.get("/users/{user_id}/questions/")
@inject
async def get_users_question_handler(
        user_id: int,
        use_case: FromDishka[GetUserExamQuestionListUseCase],
) -> ExamQuestionListResponseSchema:
    """
    Находит все вопросы для актуальной экзаменационной сессии пользователя
    """

    exam_question_list = await use_case(user_id=user_id)

    return ExamQuestionListResponseSchema.from_entity(exam_question_list)


@exam_router.get("/users/{user_id}/questions/unanswered/")
@inject
async def get_unanswered_user_question_handler(
        user_id: int,
        use_case: FromDishka[GetUnansweredUserExamQuestion],
) -> ExamQuestionResponseSchema:
    """
    Находит последний вопрос, на который пользователь еще не дал ответа.
    """

    exam_question = await use_case(user_id=user_id)

    return ExamQuestionResponseSchema.from_entity(exam_question)
