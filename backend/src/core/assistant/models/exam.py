from datetime import datetime
import uuid
from typing import Self

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.assistant.entities.exam import Exam, ExamStatus, ExamTheme, ExamType, ExamRate
from src.core.commons.model import SQLBaseModel


class ExamThemeSQLModel(SQLBaseModel):
    __tablename__ = 'exam_theme'

    exam_theme_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    title: Mapped[str]
    exam_theme_order: Mapped[int]

    @classmethod
    def from_entity(cls, exam_theme: ExamTheme) -> Self:
        return cls(
            exam_theme_id=exam_theme.exam_theme_id,
            title=exam_theme.title,
            exam_theme_order=exam_theme.exam_theme_order,
        )

    def to_entity(self) -> ExamTheme:
        return ExamTheme(
            exam_theme_id=self.exam_theme_id,
            title=self.title,
            exam_theme_order=self.exam_theme_order,
        )


class ExamSQLModel(SQLBaseModel):
    __tablename__ = 'exam'

    exam_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    user_id: Mapped[int]
    exam_theme_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(ExamThemeSQLModel.exam_theme_id))
    type: Mapped[str]
    question_count: Mapped[int]
    status: Mapped[str]
    start_exam: Mapped[datetime]
    end_exam: Mapped[datetime] = mapped_column(nullable=True)
    rate: Mapped[str] = mapped_column(nullable=True)

    exam_theme: Mapped[ExamThemeSQLModel] = relationship()

    @classmethod
    def from_entity(cls, exam: Exam) -> Self:
        return cls(
            exam_id=exam.exam_id,
            user_id=exam.user_id,
            exam_theme_id=exam.theme.exam_theme_id,
            type=exam.type.value,
            question_count=exam.question_count,
            status=exam.status.value,
            start_exam=exam.start_exam,
            end_exam=exam.end_exam,
            rate=exam.rate.value if exam.rate is not None else None,
        )

    def to_entity(self) -> Exam:
        return Exam(
            exam_id=self.exam_id,
            user_id=self.user_id,
            type=ExamType(self.type),
            question_count=self.question_count,
            status=ExamStatus(self.status),
            start_exam=self.start_exam,
            end_exam=self.end_exam,
            rate=ExamRate(self.rate) if self.rate is not None else None,
        )

    def to_entity_w_theme_load(self) -> Exam:
        return Exam(
            exam_id=self.exam_id,
            user_id=self.user_id,
            theme=self.exam_theme.to_entity(),
            type=ExamType(self.type),
            question_count=self.question_count,
            status=ExamStatus(self.status),
            start_exam=self.start_exam,
            end_exam=self.end_exam,
            rate=ExamRate(self.rate) if self.rate is not None else None,
        )
