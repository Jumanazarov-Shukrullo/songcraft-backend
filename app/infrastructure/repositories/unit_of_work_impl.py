"""Unit of Work implementation with proper async support"""

from sqlalchemy.orm import Session

from ...domain.repositories.unit_of_work import IUnitOfWork
from .user_repository_impl import UserRepositoryImpl
from .order_repository_impl import OrderRepositoryImpl
from .song_repository_impl import SongRepositoryImpl


class UnitOfWorkImpl(IUnitOfWork):

    def __init__(self, session: Session):
        self.session = session
        self.users = UserRepositoryImpl(session)
        self.orders = OrderRepositoryImpl(session)
        self.songs = SongRepositoryImpl(session)
        self._committed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.rollback()
        elif not self._committed:
            await self.commit()

    async def commit(self) -> None:
        """Commit transaction"""
        try:
            self.session.commit()
            self._committed = True
        except Exception as e:
            self.rollback_sync()
            raise e

    async def rollback(self) -> None:
        """Rollback transaction"""
        self.rollback_sync()
        
    def rollback_sync(self) -> None:
        """Synchronous rollback helper"""
        self.session.rollback()
