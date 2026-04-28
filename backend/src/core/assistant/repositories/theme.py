import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from src.core.assistant.entities.theme import Theme, ThemeFile
from src.core.assistant.exceptions.theme import ThemeNotFoundException
from src.core.assistant.interfaces.repositories.theme import ThemeRepository, ThemeFileRepository
from src.core.assistant.models.theme import ThemeSQLModel, ThemeFileSQLModel


class SQLAlchemyThemeRepository(ThemeRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add_theme(self, theme: Theme) -> None:
        model = ThemeSQLModel.from_entity(theme)
        self._session.add(model)
        await self._session.flush()

    async def get_theme_by_id(self, theme_id: uuid.UUID) -> Theme:
        query = (
            select(ThemeSQLModel)
            .options(
                joinedload(
                    ThemeSQLModel.file_list
                )
            )
            .where(
                ThemeSQLModel.theme_id == theme_id
            )
        )

        model = await self._session.scalar(query)
        if model is None:
            raise ThemeNotFoundException(theme_id)

        return model.to_entity()

    async def get_theme_list(self) -> list[Theme]:
        query = select(ThemeSQLModel).options(selectinload(ThemeSQLModel.file_list))

        model_list = await self._session.scalars(query)
        return [model.to_entity() for model in model_list]

    async def title_is_unique(self, title: str) -> bool:
        query = select(ThemeSQLModel).where(ThemeSQLModel.title == title)

        model = await self._session.scalar(query)

        return not bool(model)

    async def get_theme_by_title(self, title: str) -> Theme | None:
        query = (
            select(ThemeSQLModel)
            .options(
                joinedload(
                    ThemeSQLModel.file_list
                )
            )
            .where(
                ThemeSQLModel.title == title
            )
        )

        model = await self._session.scalar(query)

        if model is None:
            return None

        return model.to_entity()

    async def get_max_order(self) -> int:
        query = (
            select(func.max(ThemeSQLModel.theme_order))
        )

        query_result = await self._session.execute(query)

        max_order = query_result.scalar_one_or_none()
        if max_order is None:
            max_order = 0

        return max_order


class SQLAlchemyThemeFileRepository(ThemeFileRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add_theme_file(self, theme_file: ThemeFile) -> None:
        model = ThemeFileSQLModel.from_entity(theme_file)
        self._session.add(model)
