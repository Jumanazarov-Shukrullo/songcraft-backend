"""Order domain events"""

from dataclasses import dataclass
from datetime import datetime

from ..value_objects.money import Money
from ..value_objects.entity_ids import OrderId, UserId


@dataclass(frozen=True)
class OrderPaid:
    order_id: OrderId
    user_id: UserId
    amount: Money
    payment_provider_id: str


@dataclass(frozen=True)
class OrderCompleted:
    order_id: OrderId
    user_id: UserId
    completed_at: datetime


@dataclass(frozen=True)
class OrderCancelled:
    order_id: OrderId
    user_id: UserId
    reason: str 