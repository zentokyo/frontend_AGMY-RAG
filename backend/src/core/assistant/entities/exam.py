from datetime import datetime
import uuid
from dataclasses import dataclass, field
from enum import Enum

from src.core.commons.mixins.not_given import RaiseNotGivenMixin
from src.core.commons.not_given import NotGiven


class ExamStatus(Enum):
    IN_WORK = "В работе"
    COMPLETED = "Выполнен"


class ExamType(Enum):
    FINAL = "Итоговый экзамен"
    NOT_FINAL = "Не итоговый экзамен"


class ExamRate(Enum):
    ALL_CORRECT = "Отлично!"
    BAD = "Пересдача"


@dataclass
class ExamTheme:
    exam_theme_id: uuid.UUID = field(default_factory=uuid.uuid4, kw_only=True)
    title: str
    exam_theme_order: int


@dataclass
class UserExamTheme:
    exam_theme: ExamTheme
    is_enable: bool


@dataclass
class Exam(RaiseNotGivenMixin):
    exam_id: uuid.UUID = field(default_factory=uuid.uuid4, kw_only=True)
    user_id: int
    theme: ExamTheme | NotGiven = field(default_factory=NotGiven, kw_only=True)
    type: ExamType
    question_count: int
    status: ExamStatus = field(default=ExamStatus.IN_WORK, kw_only=True)
    start_exam: datetime = field(default_factory=datetime.now, kw_only=True)
    end_exam: datetime | None = field(default=None, kw_only=True)
    rate: ExamRate | None = field(default=None, kw_only=True)
