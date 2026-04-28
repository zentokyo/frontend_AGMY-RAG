import uuid
from dataclasses import dataclass

from src.core.assistant.exceptions.assistant import AssistantException


@dataclass(frozen=True, eq=False)
class ExamThemeException(AssistantException):
    @property
    def message(self) -> str:
        return "Ошибка при работе с темами экзамена!"


@dataclass(frozen=True, eq=False)
class ExamThemeNotFoundException(ExamThemeException):
    exam_theme_id: uuid.UUID

    @property
    def message(self) -> str:
        return f"Тема экзамена с id = '{self.exam_theme_id}' не найдена!"


@dataclass(frozen=True, eq=False)
class ExamThemeNotAllowedException(ExamThemeException):
    @property
    def message(self) -> str:
        return f"Эта тема пока недоступна!"