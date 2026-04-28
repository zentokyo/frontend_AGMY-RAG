import uuid
from abc import ABC, abstractmethod

from src.core.assistant.entities.exam import Exam
from src.core.assistant.entities.theme import Theme


class ExamRepository(ABC):
    @abstractmethod
    async def add_exam(self, exam: Exam) -> None:
        pass

    @abstractmethod
    async def get_exam_by_id(self, exam_id: uuid.UUID) -> Exam:
        pass

    @abstractmethod
    async def check_user_exam_in_work(self, user_id: int) -> bool:
        pass

    @abstractmethod
    async def get_user_exam_list(self, user_id: int) -> list[Exam]:
        pass

    @abstractmethod
    async def get_user_in_work_exam(self, user_id: int) -> Exam:
        pass

    @abstractmethod
    async def check_exam_exists(self, exam_id: uuid.UUID) -> bool:
        pass

    @abstractmethod
    async def update_exam(self, exam: Exam, autocommit: bool = False) -> None:
        pass

    @abstractmethod
    async def check_exam_completed(self, exam_id: uuid.UUID) -> bool:
        pass

    @abstractmethod
    async def check_user_have_completed_exams(self, user_id: int) -> bool:
        pass

    @abstractmethod
    async def get_last_user_completed_exam(self, user_id: int) -> Exam:
        pass

    @abstractmethod
    async def get_user_max_exam_order_value(self, user_id: int) -> int:
        pass
