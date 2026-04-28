from dataclasses import dataclass

from src.core.commons.exception import NotGivenException
from src.core.commons.not_given import NotGiven


@dataclass
class RaiseNotGivenMixin:
    def __getattribute__(self, name):
        value = super().__getattribute__(name)
        if isinstance(value, NotGiven):
            raise NotGivenException(field_name=name)
        return value
