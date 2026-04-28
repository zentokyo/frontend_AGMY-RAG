import uuid
from dataclasses import dataclass, field

from src.core.assistant.entities.theme import Theme
from src.core.commons.mixins.not_given import RaiseNotGivenMixin
from src.core.commons.not_given import NotGiven


@dataclass
class Question(RaiseNotGivenMixin):
    question_id: uuid.UUID = field(default_factory=uuid.uuid4, kw_only=True)
    text: str
    answer_text: str
    theme: Theme | NotGiven = field(default_factory=NotGiven, kw_only=True)
