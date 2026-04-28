import uuid
from abc import ABC, abstractmethod

from src.core.assistant.entities.stat import Stat, StatWithAnswerList


class StatRepository(ABC):
    @abstractmethod
    async def get_all_user_stat_by_theme(self, user_id: int) -> list[Stat]:
        pass

    @abstractmethod
    async def get_all_user_stat(self, user_id: int) -> Stat:
        pass

    @abstractmethod
    async def get_stat_by_exam_id(self, exam_id: uuid.UUID) -> Stat:
        pass

    @abstractmethod
    async def get_exam_stat_w_answer_list(self, exam_id: uuid.UUID) -> StatWithAnswerList:
        pass

    @abstractmethod
    async def get_exam_stat_w_answer_and_model_list(self, exam_id: uuid.UUID) -> StatWithAnswerList:
        pass
