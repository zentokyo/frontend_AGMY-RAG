import uuid
from abc import ABC, abstractmethod

from src.core.assistant.entities.answer import Answer


class AnswerRepository(ABC):
    @abstractmethod
    async def add_answer(self, answer: Answer) -> None:
        pass

    @abstractmethod
    async def get_answer_list_by_exam_id(self, exam_id: uuid.UUID) -> list[Answer]:
        pass

    @abstractmethod
    async def get_answer_list_by_user_id(self, user_id: int) -> list[Answer]:
        pass

    @abstractmethod
    async def get_correct_answers_count(self, exam_id: uuid.UUID) -> int:
        pass
