import uuid
from abc import ABC, abstractmethod

from src.core.assistant.entities.theme import Theme, ThemeFile


class ThemeRepository(ABC):
    @abstractmethod
    async def add_theme(self, theme: Theme) -> None:
        pass

    @abstractmethod
    async def get_theme_by_id(self, theme_id: uuid.UUID) -> Theme:
        pass

    @abstractmethod
    async def get_theme_list(self) -> list[Theme]:
        pass

    @abstractmethod
    async def title_is_unique(self, title: str) -> bool:
        pass

    @abstractmethod
    async def get_theme_by_title(self, title: str) -> Theme | None:
        pass

    @abstractmethod
    async def get_max_order(self) -> int:
        pass


class ThemeFileRepository(ABC):
    @abstractmethod
    async def add_theme_file(self, theme_file: ThemeFile) -> None:
        pass
