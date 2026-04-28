from src.core.assistant.interfaces.repositories.exam_theme import ExamThemeRepository
from src.core.assistant.interfaces.repositories.file import FileRepository
from src.core.assistant.interfaces.repositories.theme import ThemeRepository, ThemeFileRepository
from src.core.assistant.interfaces.uow.theme import ThemeUnitOfWork
from src.core.assistant.repositories.exam_theme import SQLAlchemyExamThemeRepository
from src.core.assistant.repositories.file import SQLAlchemyFileRepository
from src.core.assistant.repositories.theme import SQLAlchemyThemeRepository, SQLAlchemyThemeFileRepository
from src.core.commons.uow.sql import SQLAlchemyUnitOfWork


class SQLAlchemyThemeUnitOfWork(ThemeUnitOfWork, SQLAlchemyUnitOfWork):
    async def __aenter__(self):
        await super().__aenter__()
        self._theme_repository = SQLAlchemyThemeRepository(self._session)
        self._exam_theme_repository = SQLAlchemyExamThemeRepository(self._session)
        self._file_repository = SQLAlchemyFileRepository(self._session)
        self._theme_file_repository = SQLAlchemyThemeFileRepository(self._session)

    @property
    def theme_repository(self) -> ThemeRepository:
        return self._theme_repository

    @property
    def exam_theme_repository(self) -> ExamThemeRepository:
        return self._exam_theme_repository

    @property
    def file_repository(self) -> FileRepository:
        return self._file_repository

    @property
    def theme_file_repository(self) -> ThemeFileRepository:
        return self._theme_file_repository
