import uuid
from typing import Self

from pydantic import BaseModel

from src.api.exam.schemas import ExamQuestionResponseSchema
from src.core.assistant.entities.answer import Answer


class AnswerShortResponseSchema(BaseModel):
    answer_id: uuid.UUID
    question_text: str
    answer_text: str
    is_correct: bool

    @classmethod
    def from_entity(cls, answer: Answer) -> Self:
        return cls(
            answer_id=answer.answer_id,
            question_text=answer.exam_question.question.text,
            answer_text=answer.answer_text,
            is_correct=answer.is_correct,
        )


class AnswerResponseSchema(BaseModel):
    answer_id: uuid.UUID
    exam_question: ExamQuestionResponseSchema
    answer_text: str
    is_correct: bool

    @classmethod
    def from_entity(cls, answer: Answer) -> Self:
        return cls(
            answer_id=answer.answer_id,
            exam_question=ExamQuestionResponseSchema.from_entity(answer.exam_question),
            answer_text=answer.answer_text,
            is_correct=answer.is_correct,
        )


class CreateAnswerSchema(BaseModel):
    user_id: int
    answer_text: str
