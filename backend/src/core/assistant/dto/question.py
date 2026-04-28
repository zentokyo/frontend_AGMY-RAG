import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class CreateQuestionDTO:
    text: str
    theme_id: uuid.UUID
    answer_text: str


@dataclass(frozen=True)
class CreateQuestionListDTO:
    question_list: list[CreateQuestionDTO]
