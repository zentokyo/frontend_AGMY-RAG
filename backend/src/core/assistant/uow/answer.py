from src.core.assistant.interfaces.repositories.answer import AnswerRepository
from src.core.assistant.interfaces.repositories.exam import ExamRepository
from src.core.assistant.interfaces.repositories.exam_question import ExamQuestionRepository
from src.core.assistant.interfaces.uow.answer import AnswerUnitOfWork
from src.core.assistant.repositories.answer import SQLAlchemyAnswerRepository
from src.core.assistant.repositories.exam import SQLAlchemyExamRepository
from src.core.assistant.repositories.exam_question import SQLAlchemyExamQuestionRepository
from src.core.commons.uow.sql import SQLAlchemyUnitOfWork


class SQLAlchemyAnswerUnitOfWork(AnswerUnitOfWork, SQLAlchemyUnitOfWork):
    async def __aenter__(self):
        await super().__aenter__()
        self._answer_repository = SQLAlchemyAnswerRepository(self._session)
        self._exam_question_repository = SQLAlchemyExamQuestionRepository(self._session)
        self._exam_repository = SQLAlchemyExamRepository(self._session)

    @property
    def answer_repository(self) -> AnswerRepository:
        return self._answer_repository

    @property
    def exam_question_repository(self) -> ExamQuestionRepository:
        return self._exam_question_repository

    @property
    def exam_repository(self) -> ExamRepository:
        return self._exam_repository
