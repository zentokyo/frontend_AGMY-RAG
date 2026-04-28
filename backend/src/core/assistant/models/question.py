import uuid
from typing import Self

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.assistant.entities.question import Question
from src.core.assistant.models.theme import ThemeSQLModel
from src.core.commons.model import SQLBaseModel


class QuestionSQLModel(SQLBaseModel):
    __tablename__ = "question"

    question_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    theme_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(ThemeSQLModel.theme_id))
    text: Mapped[str]
    answer_text: Mapped[str]

    theme: Mapped[ThemeSQLModel] = relationship()

    @classmethod
    def from_entity(cls, question: Question) -> Self:
        return cls(
            question_id=question.question_id,
            theme_id=question.theme.theme_id,
            text=question.text,
            answer_text=question.answer_text,
        )

    def to_entity(self) -> Question:
        return Question(
            question_id=self.question_id,
            text=self.text,
            answer_text=self.answer_text,
        )

    def to_entity_w_theme_load(self) -> Question:
        return Question(
            question_id=self.question_id,
            text=self.text,
            theme=self.theme.to_entity(),
            answer_text=self.answer_text,
        )
