from dataclasses import dataclass


@dataclass(frozen=True)
class CreateAnswerDTO:
    user_id: int
    answer_text: str
