from dataclasses import dataclass


@dataclass(frozen=True)
class CreateExamThemeDTO:
    title: str
