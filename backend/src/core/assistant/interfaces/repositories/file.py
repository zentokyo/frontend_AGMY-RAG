from abc import ABC, abstractmethod

from src.core.assistant.entities.file import File


class FileRepository(ABC):
    @abstractmethod
    async def add_file(self, file: File) -> None:
        pass
