import uuid

from src.core.assistant.dto.question import CreateQuestionDTO, CreateQuestionListDTO
from src.core.assistant.entities.question import Question
from src.core.assistant.interfaces.repositories.question import QuestionRepository
from src.core.assistant.interfaces.repositories.theme import ThemeRepository


class BaseQuestionUseCase:
    def __init__(
            self,
            question_repository: QuestionRepository,
    ):
        self._question_repository = question_repository


class CreateQuestionUseCase(BaseQuestionUseCase):
    def __init__(
            self,
            question_repository: QuestionRepository,
            theme_repository: ThemeRepository,
    ):
        super().__init__(question_repository)
        self._theme_repository = theme_repository

    async def __call__(self, create_question_dto: CreateQuestionDTO) -> Question:
        theme = await self._theme_repository.get_theme_by_id(create_question_dto.theme_id)

        question = Question(
            text=create_question_dto.text,
            theme=theme,
            answer_text=create_question_dto.answer_text
        )

        await self._question_repository.add_question(question)

        return question


class GetQuestionUseCase(BaseQuestionUseCase):
    async def __call__(self, question_id: uuid.UUID) -> Question:
        return await self._question_repository.get_question_w_theme(question_id)


class GetQuestionListUseCase(BaseQuestionUseCase):
    async def __call__(self) -> list[Question]:
        return await self._question_repository.get_question_list_w_theme()


class CreateQuestionListUseCase(BaseQuestionUseCase):
    def __init__(
            self,
            question_repository: QuestionRepository,
            theme_repository: ThemeRepository,
    ):
        super().__init__(question_repository)
        self._theme_repository = theme_repository

    async def __call__(self, create_question_list_dto: CreateQuestionListDTO) -> list[Question]:
        theme_hash = {}
        question_list = []

        for created_question in create_question_list_dto.question_list:
            if created_question.theme_id not in theme_hash:
                theme = await self._theme_repository.get_theme_by_id(created_question.theme_id)
                theme_hash[created_question.theme_id] = theme

            theme = theme_hash[created_question.theme_id]
            question_list.append(
                Question(
                    text=created_question.text,
                    theme=theme,
                    answer_text=created_question.answer_text,
                )
            )

        await self._question_repository.add_bulk_questions(question_list)

        return question_list
