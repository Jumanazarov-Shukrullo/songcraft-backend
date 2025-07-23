"""Song repository interface"""

from abc import ABC, abstractmethod
from typing import Optional, List

from ..entities.song import Song
from ..value_objects.entity_ids import SongId, UserId, OrderId


class ISongRepository(ABC):
    
    @abstractmethod
    async def get_by_id(self, song_id: SongId) -> Optional[Song]:
        pass
    
    @abstractmethod
    async def get_by_user_id(self, user_id: UserId) -> List[Song]:
        pass
    
    @abstractmethod
    async def get_by_order_id(self, order_id: OrderId) -> Optional[Song]:
        pass
    
    @abstractmethod
    async def add(self, song: Song) -> Song:
        pass
    
    @abstractmethod
    async def update(self, song: Song) -> Song:
        pass
    
    @abstractmethod
    async def delete(self, song_id: SongId) -> None:
        pass
    
    @abstractmethod
    async def count(self) -> int:
        pass
