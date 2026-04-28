import uuid

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.core.assistant.entities.question import Question
from src.core.assistant.entities.theme import Theme
from src.core.assistant.exceptions.exam_question import ExamQuestionNotFoundException
from src.core.assistant.exceptions.question import QuestionNotFoundException
from src.core.assistant.interfaces.repositories.question import QuestionRepository
from src.core.assistant.models.question import QuestionSQLModel


class SQLAlchemyQuestionRepository(QuestionRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add_question(self, question: Question) -> None:
        model = QuestionSQLModel.from_entity(question)
        self._session.add(model)
        await self._session.commit()

    async def add_bulk_questions(self, question_list: list[Question]) -> None:
        model_list = [QuestionSQLModel.from_entity(question) for question in question_list]
        self._session.add_all(model_list)
        await self._session.commit()

    async def get_question(self, question_id: uuid.UUID) -> Question:
        query = select(QuestionSQLModel).where(QuestionSQLModel.question_id == question_id)

        model = await self._session.scalar(query)
        if model is None:
            raise QuestionNotFoundException(question_id)

        return model.to_entity()

    async def get_question_list(self) -> list[Question]:
        query = select(QuestionSQLModel)

        model_list = await self._session.scalars(query)

        return [model.to_entity() for model in model_list.all()]

    async def get_random_question(self, exclude: list[Question] | None) -> Question:
        if exclude is None:
            exclude = []

        question_ids = [question.question_id for question in exclude]

        query = (
            select(QuestionSQLModel)
            .where(
                QuestionSQLModel.question_id.notin_(question_ids)
            )
            .order_by(
                func.random()
            )
            .limit(1)
        )

        model = await self._session.scalar(query)

        if model is None:
            raise ExamQuestionNotFoundException

        return model.to_entity()

    async def get_random_question_for_theme(self, theme: Theme, exclude: list[Question] | None):
        if exclude is None:
            exclude = []

        question_ids = [question.question_id for question in exclude]

        query = (
            select(QuestionSQLModel)
            .where(
                and_(
                    QuestionSQLModel.question_id.notin_(question_ids),
                    QuestionSQLModel.theme_id == theme.theme_id,
                )
            )
            .order_by(
                func.random()
            )
            .limit(1)
        )

        model = await self._session.scalar(query)

        if model is None:
            raise ExamQuestionNotFoundException

        return model.to_entity()

    async def get_question_w_theme(self, question_id: uuid.UUID) -> Question:
        query = (
            select(QuestionSQLModel)
            .options(
                joinedload(QuestionSQLModel.theme)
            )
            .where(QuestionSQLModel.question_id == question_id)
        )

        model = await self._session.scalar(query)

        if model is None:
            raise QuestionNotFoundException(question_id)

        return model.to_entity_w_theme_load()

    async def get_question_list_w_theme(self) -> list[Question]:
        query = (
            select(QuestionSQLModel)
            .options(
                joinedload(QuestionSQLModel.theme)
            )
        )

        model_list = await self._session.scalars(query)

        return [model.to_entity_w_theme_load() for model in model_list.all()]

    async def get_question_count(self, theme_id: uuid.UUID) -> int:
        query = (
            select(
                func.count(QuestionSQLModel.question_id)
            )
            .where(QuestionSQLModel.theme_id == theme_id)
        )

        question_count = await self._session.execute(query)

        return question_count.scalar()
