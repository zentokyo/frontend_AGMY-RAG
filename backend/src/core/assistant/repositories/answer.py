import uuid

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.core.assistant.entities.answer import Answer
from src.core.assistant.interfaces.repositories.answer import AnswerRepository
from src.core.assistant.models.answer import AnswerSQLModel
from src.core.assistant.models.exam import ExamSQLModel
from src.core.assistant.models.exam_question import ExamQuestionSQLModel


class SQLAlchemyAnswerRepository(AnswerRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add_answer(self, answer: Answer) -> None:
        model = AnswerSQLModel.from_entity(answer)
        self._session.add(model)
        await self._session.flush()

    async def get_answer_list_by_exam_id(self, exam_id: uuid.UUID) -> list[Answer]:
        query = (
            select(AnswerSQLModel)
            .options(
                joinedload(
                    AnswerSQLModel.exam_question
                )
                .joinedload(ExamQuestionSQLModel.question)
            )
            .join(
                ExamQuestionSQLModel,
                ExamQuestionSQLModel.exam_question_id == AnswerSQLModel.exam_question_id,
            )
            .where(ExamQuestionSQLModel.exam_id == exam_id)
        )

        model_list = await self._session.scalars(query)

        return [model.to_entity() for model in model_list.all()]

    async def get_answer_list_by_user_id(self, user_id: int) -> list[Answer]:
        query = (
            select(AnswerSQLModel)
            .options(
                joinedload(
                    AnswerSQLModel.exam_question
                )
                .joinedload(
                    ExamQuestionSQLModel.question
                )
            )
            .join(
                ExamQuestionSQLModel,
                ExamQuestionSQLModel.exam_question_id == AnswerSQLModel.exam_question_id,
            )
            .join(
                ExamSQLModel,
                ExamSQLModel.exam_id == ExamQuestionSQLModel.exam_id,
            )
            .where(
                ExamSQLModel.user_id == user_id
            )
        )

        model_list = await self._session.scalars(query)

        return [model.to_entity() for model in model_list.all()]

    async def get_correct_answers_count(self, exam_id: uuid.UUID) -> int:
        query = (
            select(
                func.count(
                    AnswerSQLModel.answer_id
                ),
            )
            .join(
                ExamQuestionSQLModel,
                ExamQuestionSQLModel.exam_question_id == AnswerSQLModel.exam_question_id
            )
            .join(
                ExamSQLModel,
                ExamSQLModel.exam_id == ExamQuestionSQLModel.exam_id,
            )
            .where(
                and_(
                    AnswerSQLModel.is_correct == True,
                    ExamSQLModel.exam_id == exam_id
                )
            )
        )

        correct_answer_count = await self._session.execute(query)

        return correct_answer_count.scalar()
