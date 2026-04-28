import uuid
from abc import ABC, abstractmethod

from src.core.assistant.entities.exam import ExamTheme


class ExamThemeRepository(ABC):
    @abstractmethod
    async def add_exam_theme(self, exam_theme: ExamTheme, autocommit: bool = False) -> None:
        pass

    @abstractmethod
    async def get_exam_theme_by_id(self, exam_theme_id: uuid.UUID) -> ExamTheme:
        pass

    @abstractmethod
    async def get_exam_theme_by_theme_id(self, theme_id: uuid.UUID) -> ExamTheme:
        pass

    @abstractmethod
    async def get_exam_theme_list(self) -> list[ExamTheme]:
        pass

    @abstractmethod
    async def get_max_order(self) -> int:
        pass
