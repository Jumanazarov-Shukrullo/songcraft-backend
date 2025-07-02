"""Unit of Work interface for transaction management"""

from abc import ABC, abstractmethod
from typing import AsyncContextManager

from .user_repository import IUserRepository
from .order_repository import IOrderRepository  
from .song_repository import ISongRepository


class IUnitOfWork(ABC):
    """Unit of Work interface for managing transactions across repositories"""
    
    users: IUserRepository
    orders: IOrderRepository
    songs: ISongRepository
    
    @abstractmethod
    async def __aenter__(self):
        """Enter async context"""
        pass
    
    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context"""
        pass
    
    @abstractmethod
    async def commit(self):
        """Commit transaction"""
        pass
    
    @abstractmethod
    async def rollback(self):
        """Rollback transaction"""
        pass 