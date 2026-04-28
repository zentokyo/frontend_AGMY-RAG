import uuid
from dataclasses import dataclass

from src.core.assistant.exceptions.assistant import AssistantException


@dataclass(frozen=True, eq=False)
class ThemeException(AssistantException):
    @property
    def message(self) -> str:
        return "Ошибка при работа с темами!"


@dataclass(frozen=True, eq=False)
class ThemeNotFoundException(ThemeException):
    theme_id: uuid.UUID

    @property
    def message(self) -> str:
        return f"Тема с id = {self.theme_id} не найдена!"


@dataclass(frozen=True, eq=False)
class ThemeTitleNotUniqueException(ThemeException):
    title: str

    @property
    def message(self) -> str:
        return f"Тема с заголовком = '{self.title}' уже добавлена!"
