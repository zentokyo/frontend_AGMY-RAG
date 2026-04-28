from abc import ABC, abstractmethod


class S3Storage(ABC):
    @abstractmethod
    async def upload_file(self, data: bytes, filename: str) -> None:
        pass

    @abstractmethod
    async def download_file(self, filename: str) -> bytes:
        pass

    @abstractmethod
    async def is_file_exists(self, filename: str) -> bool:
        pass
