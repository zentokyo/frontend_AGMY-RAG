import uuid

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.core.assistant.entities.exam import Exam, ExamStatus, ExamRate
from src.core.assistant.exceptions.exam import ExamNotFoundException, UserInWorkExamNotFoundException, \
    UserHaveNotCompletedExamsException
from src.core.assistant.interfaces.repositories.exam import ExamRepository
from src.core.assistant.models.exam import ExamSQLModel, ExamThemeSQLModel


class SQLAlchemyExamRepository(ExamRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add_exam(self, exam: Exam) -> None:
        model = ExamSQLModel.from_entity(exam)
        self._session.add(model)
        await self._session.commit()

    async def get_exam_by_id(self, exam_id: uuid.UUID) -> Exam:
        query = (
            select(ExamSQLModel)
            .options(
                joinedload(ExamSQLModel.exam_theme)
            )
            .where(ExamSQLModel.exam_id == exam_id)
        )

        model = await self._session.scalar(query)
        if model is None:
            raise ExamNotFoundException(exam_id)

        return model.to_entity_w_theme_load()

    async def check_user_exam_in_work(self, user_id: int) -> bool:
        query = (
            select(ExamSQLModel)
            .where(
                and_(
                    ExamSQLModel.user_id == user_id,
                    ExamSQLModel.status == ExamStatus.IN_WORK.value
                )
            )
        )

        model = await self._session.scalar(query)

        return bool(model)

    async def get_user_exam_list(self, user_id: int) -> list[Exam]:
        query = (
            select(ExamSQLModel)
            .options(
                joinedload(ExamSQLModel.exam_theme)
            )
            .where(ExamSQLModel.user_id == user_id)
        )

        model_list = await self._session.scalars(query)

        return [model.to_entity_w_theme_load() for model in model_list.all()]

    async def get_user_in_work_exam(self, user_id: int) -> Exam:
        query = (
            select(ExamSQLModel)
            .options(
                joinedload(ExamSQLModel.exam_theme)
            )
            .where(
                and_(
                    ExamSQLModel.user_id == user_id,
                    ExamSQLModel.status == ExamStatus.IN_WORK.value,
                )
            )
        )

        model = await self._session.scalar(query)
        if model is None:
            raise UserInWorkExamNotFoundException(user_id)

        return model.to_entity_w_theme_load()

    async def check_exam_exists(self, exam_id: uuid.UUID) -> bool:
        query = select(ExamSQLModel).where(ExamSQLModel.exam_id == exam_id)

        model = await self._session.scalar(query)

        return bool(model)

    async def update_exam(self, exam: Exam, autocommit: bool = False) -> None:
        model = ExamSQLModel.from_entity(exam)
        await self._session.merge(model)

        if autocommit:
            await self._session.commit()

    async def check_exam_completed(self, exam_id: uuid.UUID) -> bool:
        query = (
            select(ExamSQLModel)
            .where(
                and_(
                    ExamSQLModel.exam_id == exam_id,
                    ExamSQLModel.status == ExamStatus.COMPLETED.value,
                )
            )
        )

        model = await self._session.scalar(query)

        return bool(model)

    async def check_user_have_completed_exams(self, user_id: int) -> bool:
        query = (
            select(ExamSQLModel)
            .where(
                and_(
                    ExamSQLModel.user_id == user_id,
                    ExamSQLModel.status == ExamStatus.COMPLETED.value,
                )
            )
        )

        model_list = await self._session.scalars(query)

        return bool(model_list.all())

    async def get_last_user_completed_exam(self, user_id: int) -> Exam:
        query = (
            select(ExamSQLModel)
            .where(
                and_(
                    ExamSQLModel.user_id == user_id,
                    ExamSQLModel.status == ExamStatus.COMPLETED.value,
                    ExamSQLModel.end_exam.is_not(None),
                )
            )
            .order_by(ExamSQLModel.end_exam.desc())
            .limit(1)
        )

        model = await self._session.scalar(query)

        if model is None:
            raise UserHaveNotCompletedExamsException(user_id=user_id)

        return model.to_entity()

    async def get_user_max_exam_order_value(self, user_id: int) -> int:
        query = (
            select(
                func.max(ExamThemeSQLModel.exam_theme_order)
            )
            .join(
                ExamSQLModel,
                ExamSQLModel.exam_theme_id == ExamThemeSQLModel.exam_theme_id
            )
            .where(
                and_(
                    ExamSQLModel.user_id == user_id,
                    ExamSQLModel.rate == ExamRate.ALL_CORRECT.value,
                )
            )
        )

        query_result = await self._session.execute(query)

        max_user_order = query_result.scalar_one_or_none()
        if max_user_order is None:
            max_user_order = 0

        return max_user_order
