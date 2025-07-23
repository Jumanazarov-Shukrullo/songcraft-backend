"""Order repository interface"""

from abc import ABC, abstractmethod
from typing import Optional, List

from ..entities.order import Order
from ..value_objects.entity_ids import OrderId, UserId


class IOrderRepository(ABC):
    
    @abstractmethod
    async def get_by_id(self, order_id: OrderId) -> Optional[Order]:
        pass
    
    @abstractmethod
    async def get_by_user_id(self, user_id: UserId) -> List[Order]:
        pass
    
    @abstractmethod
    async def add(self, order: Order) -> Order:
        pass
    
    @abstractmethod
    async def update(self, order: Order) -> Order:
        pass
    
    @abstractmethod
    async def get_by_payment_provider_id(self, provider_id: str) -> Optional[Order]:
        pass
    
    @abstractmethod
    async def count(self) -> int:
        pass
    
    @abstractmethod
    async def get_paid_orders(self) -> List[Order]:
        pass
