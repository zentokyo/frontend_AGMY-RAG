import uuid

from src.core.assistant.dto.exam_theme import CreateExamThemeDTO
from src.core.assistant.entities.exam import ExamTheme, UserExamTheme
from src.core.assistant.interfaces.repositories.exam import ExamRepository
from src.core.assistant.interfaces.repositories.exam_theme import ExamThemeRepository


class BaseExamThemeUseCase:
    def __init__(
            self,
            exam_theme_repository: ExamThemeRepository,
    ):
        self._exam_theme_repository = exam_theme_repository


class CreateExamThemeUseCase(BaseExamThemeUseCase):
    async def __call__(self, create_exam_theme_dto: CreateExamThemeDTO) -> ExamTheme:
        current_order = await self._exam_theme_repository.get_max_order()
        further_order = current_order + 1

        exam_theme = ExamTheme(
            title=create_exam_theme_dto.title,
            exam_theme_order=further_order,
        )

        await self._exam_theme_repository.add_exam_theme(exam_theme, autocommit=True)

        return exam_theme


class GetExamThemeUseCase(BaseExamThemeUseCase):
    async def __call__(self, exam_theme_id: uuid.UUID) -> ExamTheme:
        return await self._exam_theme_repository.get_exam_theme_by_id(exam_theme_id)


class GetExamThemeListUseCase(BaseExamThemeUseCase):
    async def __call__(self) -> list[ExamTheme]:
        return await self._exam_theme_repository.get_exam_theme_list()


class GetUserExamListUseCase(BaseExamThemeUseCase):
    def __init__(
            self,
            exam_theme_repository: ExamThemeRepository,
            exam_repository: ExamRepository
    ):
        super().__init__(exam_theme_repository)
        self._exam_repository = exam_repository

    async def __call__(self, user_id: int) -> list[UserExamTheme]:
        theme_list = await self._exam_theme_repository.get_exam_theme_list()
        max_order_theme_completed_user = await self._exam_repository.get_user_max_exam_order_value(user_id)
        max_order_allowed_user_number = max_order_theme_completed_user + 1
        user_theme_list = []

        for theme in theme_list:
            user_theme = UserExamTheme(
                exam_theme=theme,
                is_enable=True if theme.exam_theme_order <= max_order_allowed_user_number else False
            )
            user_theme_list.append(user_theme)

        return user_theme_list
