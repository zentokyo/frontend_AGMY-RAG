import uuid

from sqlalchemy import select, func, case, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.core.assistant.entities.exam import ExamStatus
from src.core.assistant.entities.stat import Stat, StatWithAnswerList, UserAnswerModelAnswer
from src.core.assistant.interfaces.repositories.stat import StatRepository
from src.core.assistant.models.answer import AnswerSQLModel
from src.core.assistant.models.exam import ExamSQLModel, ExamThemeSQLModel
from src.core.assistant.models.exam_question import ExamQuestionSQLModel
from src.core.assistant.models.question import QuestionSQLModel


class SQLAlchemyStatRepository(StatRepository):
    def __init__(
            self,
            session: AsyncSession,
    ):
        self._session = session

    async def get_all_user_stat(self, user_id: int) -> Stat:
        query = (
            select(
                func.count(
                    AnswerSQLModel.answer_id
                ).label("total_answers"),
                func.sum(
                    case(
                        (
                            AnswerSQLModel.is_correct == True,
                            1
                        ),
                        else_=0
                    )
                ).label("correct_answers"),
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
                    ExamSQLModel.user_id == user_id,
                    ExamSQLModel.status == ExamStatus.COMPLETED.value,
                )
            )
        )
        query_result = await self._session.execute(query)

        total_answers, correct_answers = query_result.one()
        return Stat(
            total_answers=total_answers,
            correct_answers=correct_answers
        )

    async def get_all_user_stat_by_theme(self, user_id: int) -> list[Stat]:
        query = (
            select(
                func.count(
                    AnswerSQLModel.answer_id
                ).label("total_answers"),
                func.sum(
                    case(
                        (
                            AnswerSQLModel.is_correct == True,
                            1
                        ),
                        else_=0
                    )
                ).label("correct_answers"),
                ExamThemeSQLModel.title,
            )
            .join(
                ExamQuestionSQLModel,
                ExamQuestionSQLModel.exam_question_id == AnswerSQLModel.exam_question_id
            )
            .join(
                ExamSQLModel,
                ExamSQLModel.exam_id == ExamQuestionSQLModel.exam_id,
            )
            .join(
                ExamThemeSQLModel,
                ExamThemeSQLModel.exam_theme_id == ExamSQLModel.exam_theme_id,
            )
            .where(
                and_(
                    ExamSQLModel.user_id == user_id,
                    ExamSQLModel.status == ExamStatus.COMPLETED.value,
                )
            )
            .group_by(ExamThemeSQLModel.title)
        )
        query_result = await self._session.execute(query)

        stat_list = []
        for total_answers, correct_answers, exam_theme_title in query_result.all():
            stat = Stat(
                theme_title=exam_theme_title,
                total_answers=total_answers,
                correct_answers=correct_answers
            )
            stat_list.append(stat)

        return stat_list

    async def get_stat_by_exam_id(self, exam_id: uuid.UUID) -> Stat:
        query = (
            select(
                func.count(
                    AnswerSQLModel.answer_id
                ).label("total_answers"),
                func.sum(
                    case((
                        AnswerSQLModel.is_correct == True,
                        1
                    ),
                        else_=0
                    )
                ).label("correct_answers"),
                ExamThemeSQLModel.title,
            )
            .join(
                ExamQuestionSQLModel,
                ExamQuestionSQLModel.exam_question_id == AnswerSQLModel.exam_question_id
            )
            .join(
                ExamSQLModel,
                ExamSQLModel.exam_id == ExamQuestionSQLModel.exam_id,
            )
            .join(
                ExamThemeSQLModel,
                ExamThemeSQLModel.exam_theme_id == ExamSQLModel.exam_theme_id,
            )
            .where(
                and_(
                    ExamSQLModel.exam_id == exam_id,
                    ExamSQLModel.status == ExamStatus.COMPLETED.value,
                )
            )
            .group_by(ExamThemeSQLModel.title)
        )
        query_result = await self._session.execute(query)
        total_answers, correct_answers, exam_theme_title = query_result.one()

        return Stat(
            total_answers=total_answers,
            correct_answers=correct_answers,
            theme_title=exam_theme_title,
        )

    async def get_exam_stat_w_answer_list(self, exam_id: uuid.UUID) -> StatWithAnswerList:
        stat = await self.get_stat_by_exam_id(exam_id=exam_id)

        query = (
            select(
                AnswerSQLModel.answer_text,
                AnswerSQLModel.is_correct,
                QuestionSQLModel.text,
            )
            .join(
                ExamQuestionSQLModel,
                ExamQuestionSQLModel.exam_question_id == AnswerSQLModel.exam_question_id,
            )
            .join(
                QuestionSQLModel,
                QuestionSQLModel.question_id == ExamQuestionSQLModel.question_id
            )
            .where(ExamQuestionSQLModel.exam_id == exam_id)
        )

        query_result = await self._session.execute(query)
        answer_list = [
            UserAnswerModelAnswer(user_answer=answer_text, is_correct=is_correct, question_text=question_text)
            for answer_text, is_correct, question_text in query_result.all()
        ]

        return StatWithAnswerList(
            theme_title=stat.theme_title,
            total_answers=stat.total_answers,
            correct_answers=stat.correct_answers,
            answer_list=answer_list,
        )

    async def get_exam_stat_w_answer_and_model_list(self, exam_id: uuid.UUID) -> StatWithAnswerList:
        stat = await self.get_stat_by_exam_id(exam_id=exam_id)

        query = (
            select(
                AnswerSQLModel.answer_text,
                AnswerSQLModel.is_correct,
                QuestionSQLModel.text,
                QuestionSQLModel.answer_text,
            )
            .join(
                ExamQuestionSQLModel,
                ExamQuestionSQLModel.exam_question_id == AnswerSQLModel.exam_question_id,
            )
            .join(
                QuestionSQLModel,
                QuestionSQLModel.question_id == ExamQuestionSQLModel.question_id,
            )
            .where(ExamQuestionSQLModel.exam_id == exam_id)
        )

        query_result = await self._session.execute(query)
        answer_list = [
            UserAnswerModelAnswer(
                user_answer=user_answer_text,
                model_answer=model_answer_text,
                is_correct=is_correct,
                question_text=question_text,
            )
            for user_answer_text, is_correct, question_text, model_answer_text in query_result.all()
        ]

        return StatWithAnswerList(
            theme_title=stat.theme_title,
            total_answers=stat.total_answers,
            correct_answers=stat.correct_answers,
            answer_list=answer_list,
        )
