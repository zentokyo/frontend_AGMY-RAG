from sqlalchemy.ext.asyncio import AsyncSession

from src.core.assistant.entities.file import File
from src.core.assistant.interfaces.repositories.file import FileRepository
from src.core.assistant.models.file import FileSQLModel


class SQLAlchemyFileRepository(FileRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add_file(self, file: File) -> None:
        model = FileSQLModel.from_entity(file)
        self._session.add(model)
        await self._session.flush()
