import uuid
from dataclasses import dataclass, field
from enum import Enum

from src.core.assistant.entities.question import Question


class ExamQuestionStatus(Enum):
    ANSWERED = "На вопрос дан ответ"
    UNANSWERED = "На вопрос нет ответа"


@dataclass
class ExamQuestion:
    exam_question_id: uuid.UUID = field(default_factory=uuid.uuid4, kw_only=True)
    exam_id: uuid.UUID
    question: Question
    status: ExamQuestionStatus = field(default=ExamQuestionStatus.UNANSWERED, kw_only=True)
