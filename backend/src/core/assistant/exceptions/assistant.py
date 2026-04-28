from dataclasses import dataclass

from src.core.commons.exception import BaseAppException


@dataclass(frozen=True, eq=False)
class AssistantException(BaseAppException):
    @property
    def message(self) -> str:
        return "Ошибка при работе с ассистентом!"
