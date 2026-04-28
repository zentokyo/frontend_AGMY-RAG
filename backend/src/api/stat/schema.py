from typing import Self

from pydantic import BaseModel

from src.api.answer.schemas import AnswerResponseSchema, AnswerShortResponseSchema
from src.core.assistant.entities.stat import Stat, StatWithAnswerList, TotalStat, UserAnswerModelAnswer


class StatResponseSchema(BaseModel):
    theme_title: str
    total_answers: int
    correct_answers: int
    accuracy: float

    @classmethod
    def from_entity(cls, stat: Stat) -> Self:
        return cls(
            theme_title=stat.theme_title,
            total_answers=stat.total_answers,
            correct_answers=stat.correct_answers,
            accuracy=stat.accuracy,
        )


class TotalStatResponseSchema(BaseModel):
    total_answers: int
    correct_answers: int
    accuracy: float
    stat_by_theme: list[StatResponseSchema]

    @classmethod
    def from_entity(cls, total_stat: TotalStat) -> Self:
        return cls(
            total_answers=total_stat.total_answers,
            correct_answers=total_stat.correct_answers,
            accuracy=total_stat.accuracy,
            stat_by_theme=[StatResponseSchema.from_entity(stat) for stat in total_stat.stat_by_theme]
        )


class UserAnswerModelAnswerResponseSchema(BaseModel):
    user_answer: str
    is_correct: bool
    question_text: str
    model_answer: str | None

    @classmethod
    def from_entity(cls, answer: UserAnswerModelAnswer) -> Self:
        return cls(
            user_answer=answer.user_answer,
            model_answer=answer.model_answer,
            is_correct=answer.is_correct,
            question_text=answer.question_text,
        )


class StatWithAnswerListShortResponseSchema(StatResponseSchema):
    answer_list: list[UserAnswerModelAnswerResponseSchema]

    @classmethod
    def from_entity(cls, stat: StatWithAnswerList) -> Self:
        return cls(
            theme_title=stat.theme_title,
            total_answers=stat.total_answers,
            correct_answers=stat.correct_answers,
            answer_list=[UserAnswerModelAnswerResponseSchema.from_entity(answer) for answer in stat.answer_list],
            accuracy=stat.accuracy,
        )


class StatWithAnswerListResponseSchema(StatResponseSchema):
    answer_list: list[UserAnswerModelAnswerResponseSchema]

    @classmethod
    def from_entity(cls, stat: StatWithAnswerList) -> Self:
        return cls(
            theme_title=stat.theme_title,
            total_answers=stat.total_answers,
            correct_answers=stat.correct_answers,
            answer_list=[UserAnswerModelAnswerResponseSchema.from_entity(answer) for answer in stat.answer_list],
            accuracy=stat.accuracy,
        )
