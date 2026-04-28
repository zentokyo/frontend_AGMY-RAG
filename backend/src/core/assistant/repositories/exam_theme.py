import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.assistant.entities.exam import ExamTheme
from src.core.assistant.exceptions.exam_theme import ExamThemeNotFoundException
from src.core.assistant.interfaces.repositories.exam_theme import ExamThemeRepository
from src.core.assistant.models.exam import ExamThemeSQLModel
from src.core.assistant.models.theme import ThemeSQLModel


class SQLAlchemyExamThemeRepository(ExamThemeRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add_exam_theme(self, exam_theme: ExamTheme, autocommit: bool = False) -> None:
        model = ExamThemeSQLModel.from_entity(exam_theme)
        self._session.add(model)

        if autocommit:
            await self._session.commit()

    async def get_exam_theme_by_id(self, exam_theme_id: uuid.UUID) -> ExamTheme:
        query = select(ExamThemeSQLModel).where(ExamThemeSQLModel.exam_theme_id == exam_theme_id)

        model = await self._session.scalar(query)
        if model is None:
            raise ExamThemeNotFoundException(exam_theme_id)

        return model.to_entity()

    async def get_exam_theme_by_theme_id(self, theme_id: uuid.UUID) -> ExamTheme:
        query = (
            select(ExamThemeSQLModel)
            .join(ThemeSQLModel, ThemeSQLModel.title == ExamThemeSQLModel.title)
            .where(ThemeSQLModel.theme_id == theme_id)
        )

        model = await self._session.scalar(query)
        if model is None:
            raise ExamThemeNotFoundException(theme_id)

        return model.to_entity()

    async def get_exam_theme_list(self) -> list[ExamTheme]:
        query = select(ExamThemeSQLModel)

        model_list = await self._session.scalars(query)

        return [model.to_entity() for model in model_list]

    async def get_max_order(self) -> int:
        query = (
            select(func.max(ExamThemeSQLModel.exam_theme_order))
        )

        query_result = await self._session.execute(query)

        max_order = query_result.scalar_one_or_none()
        if max_order is None:
            max_order = 0

        return max_order
