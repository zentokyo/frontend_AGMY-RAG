import uuid
from abc import ABC, abstractmethod

from src.core.assistant.entities.question import Question
from src.core.assistant.entities.theme import Theme


class QuestionRepository(ABC):
    @abstractmethod
    async def add_question(self, question: Question) -> None:
        pass

    @abstractmethod
    async def add_bulk_questions(self, questions: list[Question]) -> None:
        pass

    @abstractmethod
    async def get_question(self, question_id: uuid.UUID) -> Question:
        pass

    @abstractmethod
    async def get_question_list(self) -> list[Question]:
        pass

    @abstractmethod
    async def get_random_question(self, exclude: list[Question] | None) -> Question:
        pass

    @abstractmethod
    async def get_random_question_for_theme(self, theme: Theme, exclude: list[Question] | None):
        pass

    @abstractmethod
    async def get_question_w_theme(self, question_id: uuid.UUID) -> Question:
        pass

    @abstractmethod
    async def get_question_list_w_theme(self) -> list[Question]:
        pass

    @abstractmethod
    async def get_question_count(self, theme_id: uuid.UUID) -> int:
        pass
