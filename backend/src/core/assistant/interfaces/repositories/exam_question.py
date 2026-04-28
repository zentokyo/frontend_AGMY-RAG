import uuid
from abc import ABC, abstractmethod

from src.core.assistant.entities.exam_question import ExamQuestion


class ExamQuestionRepository(ABC):
    @abstractmethod
    async def add_exam_question(self, exam_question: ExamQuestion) -> None:
        pass

    @abstractmethod
    async def get_exam_question_list(self, exam_id: uuid.UUID) -> list[ExamQuestion]:
        pass

    @abstractmethod
    async def check_all_exam_question_answered(self, exam_id: uuid.UUID) -> bool:
        pass

    @abstractmethod
    async def get_unanswered_exam_question(self, exam_id: uuid.UUID) -> ExamQuestion:
        pass

    @abstractmethod
    async def get_answered_exam_question_count(self, exam_id: uuid.UUID) -> int:
        pass

    @abstractmethod
    async def update_exam_question(self, exam_question: ExamQuestion) -> None:
        pass
