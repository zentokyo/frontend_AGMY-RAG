import uuid
from typing import Self

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.assistant.entities.exam_question import ExamQuestion, ExamQuestionStatus
from src.core.assistant.models.exam import ExamSQLModel
from src.core.assistant.models.question import QuestionSQLModel
from src.core.commons.model import SQLBaseModel


class ExamQuestionSQLModel(SQLBaseModel):
    __tablename__ = 'exam_question'

    exam_question_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    exam_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(ExamSQLModel.exam_id))
    question_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(QuestionSQLModel.question_id))
    status: Mapped[str]

    question: Mapped[QuestionSQLModel] = relationship()

    @classmethod
    def from_entity(cls, exam_question: ExamQuestion) -> Self:
        return cls(
            exam_question_id=exam_question.exam_question_id,
            exam_id=exam_question.exam_id,
            question_id=exam_question.question.question_id,
            status=exam_question.status.value,
        )

    def to_entity(self) -> ExamQuestion:
        return ExamQuestion(
            exam_question_id=self.exam_question_id,
            exam_id=self.exam_id,
            question=self.question.to_entity(),
            status=ExamQuestionStatus(self.status),
        )
