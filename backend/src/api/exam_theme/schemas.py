import uuid
from typing import Self

from pydantic import BaseModel

from src.core.assistant.entities.exam import ExamTheme, UserExamTheme


class ExamThemeResponseSchema(BaseModel):
    exam_theme_id: uuid.UUID
    title: str

    @classmethod
    def from_entity(cls, exam_theme: ExamTheme) -> Self:
        return cls(
            exam_theme_id=exam_theme.exam_theme_id,
            title=exam_theme.title,
        )


class CreateExamThemeSchema(BaseModel):
    title: str


class UserExamThemeResponseSchema(ExamThemeResponseSchema):
    is_enable: bool

    @classmethod
    def from_entity(cls, user_exam_theme: UserExamTheme) -> Self:
        return cls(
            exam_theme_id=user_exam_theme.exam_theme.exam_theme_id,
            title=user_exam_theme.exam_theme.title,
            is_enable=user_exam_theme.is_enable,
        )
