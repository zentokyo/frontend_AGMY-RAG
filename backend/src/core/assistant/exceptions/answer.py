import uuid
from dataclasses import dataclass

from src.core.assistant.exceptions.assistant import AssistantException


@dataclass(frozen=True, eq=False)
class AnswerException(AssistantException):
    @property
    def message(self) -> str:
        return "Ошибка при ответе пользователя!"


@dataclass(frozen=True, eq=False)
class AllQuestionAlreadyAnsweredException(AssistantException):
    exam_id: uuid.UUID

    @property
    def message(self) -> str:
        return f"На все вопросы по экзаменационной сессии с id = '{self.exam_id}' уже получены ответы!"
