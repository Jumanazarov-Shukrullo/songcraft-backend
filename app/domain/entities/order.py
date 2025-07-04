"""Order entity with business logic"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List

from ..value_objects.money import Money
from ..value_objects.entity_ids import OrderId, UserId
from ..enums import OrderStatus, ProductType
from ..events.order_events import OrderPaid, OrderCompleted, OrderCancelled


@dataclass
class Order:
    id: OrderId
    user_id: UserId
    product_type: ProductType
    amount: Money
    status: OrderStatus = OrderStatus.PENDING
    
    # Payment provider fields
    payment_provider_id: Optional[str] = None
    lemon_squeezy_order_id: Optional[str] = None
    lemon_squeezy_payment_id: Optional[str] = None
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    # Domain events
    _events: List = field(default_factory=list, init=False)
    
    def mark_as_paid(self, payment_provider_id: str) -> None:
        """Business logic: mark order as paid"""
        if self.status != OrderStatus.PENDING:
            raise ValueError(f"Cannot pay order with status: {self.status}")
        
        self.status = OrderStatus.PAID
        self.payment_provider_id = payment_provider_id
        # For Lemon Squeezy, use the same ID for both fields
        self.lemon_squeezy_order_id = payment_provider_id
        self.lemon_squeezy_payment_id = payment_provider_id
        self.updated_at = datetime.utcnow()
        
        self._events.append(OrderPaid(
            order_id=self.id,
            user_id=self.user_id,
            amount=self.amount,
            payment_provider_id=payment_provider_id
        ))
    
    def start_processing(self) -> None:
        """Business logic: start processing order"""
        if self.status != OrderStatus.PAID:
            raise ValueError("Can only process paid orders")
        
        self.status = OrderStatus.PROCESSING
        self.updated_at = datetime.utcnow()
    
    def complete(self) -> None:
        """Business logic: complete order"""
        if self.status != OrderStatus.PROCESSING:
            raise ValueError("Can only complete processing orders")
        
        self.status = OrderStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        
        self._events.append(OrderCompleted(
            order_id=self.id,
            user_id=self.user_id,
            completed_at=self.completed_at
        ))
    
    def cancel(self, reason: str) -> None:
        """Business logic: cancel order"""
        if self.status in [OrderStatus.COMPLETED, OrderStatus.CANCELLED]:
            raise ValueError(f"Cannot cancel order with status: {self.status}")
        
        self.status = OrderStatus.CANCELLED
        self.updated_at = datetime.utcnow()
        
        self._events.append(OrderCancelled(
            order_id=self.id,
            user_id=self.user_id,
            reason=reason
        ))
    
    @property
    def is_paid(self) -> bool:
        return self.status in [
            OrderStatus.PAID, 
            OrderStatus.PROCESSING, 
            OrderStatus.COMPLETED
        ]
    
    @property
    def requires_video(self) -> bool:
        return self.product_type == ProductType.AUDIO_VIDEO
    
    def get_events(self) -> List:
        """Get and clear domain events"""
        events = self._events.copy()
        self._events.clear()
        return events 