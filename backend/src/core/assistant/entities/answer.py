import uuid
from dataclasses import dataclass, field

from src.core.assistant.entities.exam_question import ExamQuestion


@dataclass
class Answer:
    answer_id: uuid.UUID = field(default_factory=uuid.uuid4, kw_only=True)
    exam_question: ExamQuestion
    answer_text: str
    is_correct: bool | None
