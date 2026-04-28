import uuid
from datetime import datetime
from typing import Self

from pydantic import BaseModel

from src.api.exam_theme.schemas import ExamThemeResponseSchema
from src.api.question.schemas import QuestionResponseSchema
from src.core.assistant.entities.exam import Exam, ExamStatus, ExamType
from src.core.assistant.entities.exam_question import ExamQuestionStatus, ExamQuestion


class ExamResponseSchema(BaseModel):
    exam_id: uuid.UUID
    user_id: int
    exam_theme: ExamThemeResponseSchema
    question_count: int
    status: ExamStatus
    start_exam: datetime
    end_exam: datetime | None

    @classmethod
    def from_entity(cls, exam: Exam) -> Self:
        return cls(
            exam_id=exam.exam_id,
            user_id=exam.user_id,
            exam_theme=ExamThemeResponseSchema.from_entity(exam.theme),
            question_count=exam.question_count,
            status=exam.status,
            start_exam=exam.start_exam,
            end_exam=exam.end_exam,
        )


class CreateExamQuestionResponseSchema(BaseModel):
    exam_id: uuid.UUID
    question: QuestionResponseSchema

    @classmethod
    def from_entity(cls, exam_question: ExamQuestion) -> Self:
        return cls(
            exam_id=exam_question.exam_id,
            question=QuestionResponseSchema.from_entity(exam_question.question),
        )


class ExamQuestionResponseSchema(BaseModel):
    question: QuestionResponseSchema
    status: ExamQuestionStatus

    @classmethod
    def from_entity(cls, exam_question: ExamQuestion) -> Self:
        return cls(
            question=QuestionResponseSchema.from_entity(exam_question.question),
            status=exam_question.status,
        )


class ExamQuestionListResponseSchema(BaseModel):
    exam_id: uuid.UUID
    question_list: list[ExamQuestionResponseSchema]

    @classmethod
    def from_entity(cls, exam_question_list: list[ExamQuestion]) -> Self:
        return cls(
            exam_id=exam_question_list[0].exam_id,
            question_list=[
                ExamQuestionResponseSchema.from_entity(exam_question)
                for exam_question in exam_question_list
            ]
        )


class CreateExamSchema(BaseModel):
    user_id: int
    question_count: int
    exam_theme_id: uuid.UUID
