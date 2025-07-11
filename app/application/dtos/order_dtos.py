"""Order DTOs for API requests and responses"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from ...domain.enums import OrderStatus, ProductType


class OrderCreateDTO(BaseModel):
    """Request DTO for creating an order"""
    product_type: ProductType
    amount: float = Field(..., ge=0)
    currency: str = Field(default="USD")

    class Config:
        use_enum_values = True


class OrderResponseDTO(BaseModel):
    """Response DTO for order data"""
    id: UUID
    user_id: UUID
    amount: float
    currency: str
    product_type: str
    status: str
    payment_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

    @classmethod
    def from_entity(cls, order):
        """Convert domain entity to DTO"""
        return cls(
            id=order.id.value,
            user_id=order.user_id.value,
            amount=float(order.amount.amount),
            currency=order.amount.currency,
            product_type=order.product_type.value,
            status=order.status.value,
            payment_id=getattr(order, "payment_id", getattr(order, "payment_provider_id", None)),
            created_at=order.created_at,
            updated_at=order.updated_at
        )


class OrderUpdateDTO(BaseModel):
    """Request DTO for updating an order"""
    status: Optional[OrderStatus] = None
    payment_id: Optional[str] = None

    class Config:
        use_enum_values = True


class PaymentWebhookData(BaseModel):
    """DTO for payment webhook data"""
    payload: bytes
    signature: str
    payment_id: str
    custom_data: Dict[str, Any] 