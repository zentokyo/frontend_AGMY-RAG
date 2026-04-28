from abc import ABC, abstractmethod

from src.core.assistant.interfaces.repositories.answer import AnswerRepository
from src.core.assistant.interfaces.repositories.exam import ExamRepository
from src.core.assistant.interfaces.repositories.exam_question import ExamQuestionRepository
from src.core.commons.uow.base import UnitOfWork


class AnswerUnitOfWork(UnitOfWork, ABC):
    @property
    @abstractmethod
    def answer_repository(self) -> AnswerRepository:
        pass

    @property
    @abstractmethod
    def exam_question_repository(self) -> ExamQuestionRepository:
        pass

    @property
    @abstractmethod
    def exam_repository(self) -> ExamRepository:
        pass
