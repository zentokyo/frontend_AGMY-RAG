from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from src.core.commons.uow.base import UnitOfWork


class SQLAlchemyUnitOfWork(UnitOfWork):
    def __init__(self, session_maker: async_sessionmaker[AsyncSession]):
        self._session_maker = session_maker

    async def __aenter__(self):
        self._session = self._session_maker()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.rollback()
        await self._session.close()

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()
