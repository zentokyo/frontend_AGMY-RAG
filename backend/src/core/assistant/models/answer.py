import uuid
from typing import Self

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.assistant.entities.answer import Answer
from src.core.assistant.models.exam_question import ExamQuestionSQLModel
from src.core.commons.model import SQLBaseModel


class AnswerSQLModel(SQLBaseModel):
    __tablename__ = "answer"

    answer_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    exam_question_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(ExamQuestionSQLModel.exam_question_id))
    answer_text: Mapped[str]
    is_correct: Mapped[bool]

    exam_question: Mapped[ExamQuestionSQLModel] = relationship()

    @classmethod
    def from_entity(cls, answer: Answer) -> Self:
        return cls(
            answer_id=answer.answer_id,
            exam_question_id=answer.exam_question.exam_question_id,
            answer_text=answer.answer_text,
            is_correct=answer.is_correct,
        )

    def to_entity(self) -> Answer:
        return Answer(
            answer_id=self.answer_id,
            exam_question=self.exam_question.to_entity(),
            answer_text=self.answer_text,
            is_correct=self.is_correct,
        )
