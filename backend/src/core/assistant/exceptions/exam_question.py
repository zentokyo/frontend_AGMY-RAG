import uuid
from dataclasses import dataclass

from src.core.assistant.exceptions.assistant import AssistantException


@dataclass(frozen=True, eq=False)
class ExamQuestionException(AssistantException):
    @property
    def message(self) -> str:
        return f"Ошибка при работе с экзаменационными вопросами!"


@dataclass(frozen=True, eq=False)
class UserHaveUnansweredQuestionException(ExamQuestionException):
    exam_id: uuid.UUID

    @property
    def message(self) -> str:
        return f"Пользователь еще не дал ответ на все заданные вопросы экзаменационной сессии с id = '{self.exam_id}'"


@dataclass(frozen=True, eq=False)
class ExamQuestionNotFoundException(ExamQuestionException):
    @property
    def message(self) -> str:
        return "Экзаменационный вопрос не найден!"
