import uuid
from dataclasses import dataclass

from src.core.assistant.exceptions.assistant import AssistantException


@dataclass(frozen=True, eq=False)
class ExamException(AssistantException):
    @property
    def message(self) -> str:
        return "Ошибка при работе к экзаменационными сессиями!"


@dataclass(frozen=True, eq=False)
class ExamNotFoundException(ExamException):
    exam_id: uuid.UUID

    @property
    def message(self) -> str:
        return f"Экзаменационная сессия с id = '{self.exam_id}' не найдена!"


@dataclass(frozen=True, eq=False)
class UserAlreadyTakingExamException(ExamException):
    user_id: int

    @property
    def message(self) -> str:
        return f"Пользователь с id = '{self.user_id}' уже проходит экзамен!"


@dataclass(frozen=True, eq=False)
class ExamQuestionCountException(ExamException):
    question_count: int

    @property
    def message(self) -> str:
        return f"Экзамен должен содержать от 1 до 10 вопросов, вы ввели: {self.question_count}!"


@dataclass(frozen=True, eq=False)
class UserInWorkExamNotFoundException(ExamException):
    user_id: int

    @property
    def message(self) -> str:
        return f"Для пользователя с id = '{self.user_id}' экзаменационная сессия, находящаяся в работе, не найдена!"


@dataclass(frozen=True, eq=False)
class ExamNotCompletedException(ExamException):
    exam_id: uuid.UUID

    @property
    def message(self) -> str:
        return f"Экзаменационная сессия с id='{self.exam_id}' не завершена!"


@dataclass(frozen=True, eq=False)
class UserHaveNotCompletedExamsException(ExamException):
    user_id: int

    @property
    def message(self) -> str:
        return f"Пользователь с id = '{self.user_id}' не имеет завершенных экзаменационных сессий!"


@dataclass(frozen=True, eq=False)
class ExamWithoutQuestionException(ExamException):
    exam_id: uuid.UUID

    @property
    def message(self) -> str:
        return f"Экзаменационная сессия с id = '{self.exam_id}' не имеет вопросов!"
