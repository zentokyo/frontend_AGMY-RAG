from abc import ABC, abstractmethod

from src.core.assistant.interfaces.repositories.exam_theme import ExamThemeRepository
from src.core.assistant.interfaces.repositories.file import FileRepository
from src.core.assistant.interfaces.repositories.theme import ThemeRepository, ThemeFileRepository
from src.core.commons.uow.base import UnitOfWork


class ThemeUnitOfWork(UnitOfWork, ABC):
    @property
    @abstractmethod
    def theme_repository(self) -> ThemeRepository:
        pass

    @property
    @abstractmethod
    def exam_theme_repository(self) -> ExamThemeRepository:
        pass

    @property
    @abstractmethod
    def file_repository(self) -> FileRepository:
        pass

    @property
    @abstractmethod
    def theme_file_repository(self) -> ThemeFileRepository:
        pass
