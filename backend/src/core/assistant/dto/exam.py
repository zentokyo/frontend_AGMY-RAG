import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class CreateExamDTO:
    user_id: int
    exam_theme_id: uuid.UUID
    question_count: int
