import uuid
from typing import Self

from pydantic import BaseModel

from src.api.theme.schema import ThemeShortResponse
from src.core.assistant.entities.question import Question


class QuestionResponseSchema(BaseModel):
    question_id: uuid.UUID
    text: str

    @classmethod
    def from_entity(cls, question: Question) -> Self:
        return cls(
            question_id=question.question_id,
            text=question.text,
        )


class QuestionWithThemeResponseSchema(QuestionResponseSchema):
    theme: ThemeShortResponse

    @classmethod
    def from_entity(cls, question: Question) -> Self:
        return cls(
            question_id=question.question_id,
            text=question.text,
            theme=ThemeShortResponse.from_entity(question.theme),
        )


class CreateQuestionSchema(BaseModel):
    text: str
    theme_id: uuid.UUID
    answer_text: str


class CreateQuestionListSchema(BaseModel):
    question_list: list[CreateQuestionSchema]
