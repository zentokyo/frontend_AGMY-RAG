from dataclasses import dataclass, field

from src.core.assistant.entities.answer import Answer


@dataclass
class Stat:
    theme_title: str | None = field(default=None, kw_only=True)
    total_answers: int
    correct_answers: int
    _accuracy: float | None = field(default=None, kw_only=True)

    def __post_init__(self):
        self._accuracy = self.correct_answers / self.total_answers

    @property
    def accuracy(self) -> float:
        return round(self._accuracy, 2)


@dataclass
class TotalStat(Stat):
    stat_by_theme: list[Stat]


@dataclass
class UserAnswerModelAnswer:
    user_answer: str
    question_text: str
    is_correct: bool
    model_answer: str | None = field(default=None, kw_only=True)


@dataclass
class StatWithAnswerList(Stat):
    answer_list: list[UserAnswerModelAnswer]
