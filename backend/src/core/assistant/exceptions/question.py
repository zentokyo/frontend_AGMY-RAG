import uuid
from dataclasses import dataclass

from src.core.assistant.exceptions.assistant import AssistantException


@dataclass(frozen=True, eq=False)
class QuestionException(AssistantException):
    @property
    def message(self) -> str:
        return "Ошибка при работе с вопросами!"


@dataclass(frozen=True, eq=False)
class QuestionNotFoundException(QuestionException):
    question_id: uuid.UUID

    @property
    def message(self) -> str:
        return f"Вопрос с id = '{self.question_id}' не найден!"
