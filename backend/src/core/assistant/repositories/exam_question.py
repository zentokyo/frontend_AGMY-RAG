import uuid

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.core.assistant.entities.exam_question import ExamQuestion, ExamQuestionStatus
from src.core.assistant.exceptions.answer import AllQuestionAlreadyAnsweredException
from src.core.assistant.interfaces.repositories.exam_question import ExamQuestionRepository
from src.core.assistant.models.exam_question import ExamQuestionSQLModel


class SQLAlchemyExamQuestionRepository(ExamQuestionRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add_exam_question(self, exam_question: ExamQuestion) -> None:
        model = ExamQuestionSQLModel.from_entity(exam_question)
        self._session.add(model)
        await self._session.commit()

    async def get_exam_question_list(self, exam_id: uuid.UUID) -> list[ExamQuestion]:
        query = (
            select(ExamQuestionSQLModel)
            .options(
                joinedload(
                    ExamQuestionSQLModel.question
                )
            )
            .where(ExamQuestionSQLModel.exam_id == exam_id)
        )

        model_list = await self._session.scalars(query)

        return [model.to_entity() for model in model_list]

    async def check_all_exam_question_answered(self, exam_id: uuid.UUID) -> bool:
        query = (
            select(ExamQuestionSQLModel)
            .where(
                and_(
                    ExamQuestionSQLModel.exam_id == exam_id,
                    ExamQuestionSQLModel.status == ExamQuestionStatus.UNANSWERED.value
                )
            )
        )

        model = await self._session.scalar(query)

        return not bool(model)

    async def get_unanswered_exam_question(self, exam_id: uuid.UUID) -> ExamQuestion:
        query = (
            select(ExamQuestionSQLModel)
            .options(
                joinedload(
                    ExamQuestionSQLModel.question
                )
            )
            .where(
                and_(
                    ExamQuestionSQLModel.exam_id == exam_id,
                    ExamQuestionSQLModel.status == ExamQuestionStatus.UNANSWERED.value,
                )
            )
        )

        model = await self._session.scalar(query)

        if model is None:
            raise AllQuestionAlreadyAnsweredException(exam_id)

        return model.to_entity()

    async def get_answered_exam_question_count(self, exam_id: uuid.UUID) -> int:
        query = (
            select(func.count(ExamQuestionSQLModel.exam_question_id))
            .where(
                and_(
                    ExamQuestionSQLModel.exam_id == exam_id,
                    ExamQuestionSQLModel.status == ExamQuestionStatus.ANSWERED.value,
                )
            )
        )

        count = await self._session.execute(query)

        return count.scalar()

    async def update_exam_question(self, exam_question: ExamQuestion) -> None:
        model = ExamQuestionSQLModel.from_entity(exam_question)
        await self._session.merge(model)
