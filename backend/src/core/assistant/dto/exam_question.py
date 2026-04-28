from dataclasses import dataclass


@dataclass(frozen=True)
class AskExamQuestionDTO:
    user_id: int
