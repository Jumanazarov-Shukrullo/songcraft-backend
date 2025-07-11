"""Order repository implementation using SQLAlchemy ORM"""

from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from ...domain.entities.order import Order
from ...domain.repositories.order_repository import IOrderRepository
from ...domain.value_objects.entity_ids import OrderId, UserId
from ...domain.enums import OrderStatus
from ..orm.order_model import OrderModel  # Fixed import for DDD architecture


class OrderRepositoryImpl(IOrderRepository):
    """Repository implementation for Order aggregate"""

    def __init__(self, session: Session):
        self.session = session

    def save(self, order: Order) -> Order:
        """Save or update order"""
        existing = self.session.query(OrderModel).filter(OrderModel.id == order.id.value).first()
        
        if existing:
            # Update existing order
            self._update_model_from_entity(existing, order)
        else:
            # Create new order
            model = self._create_model_from_entity(order)
            self.session.add(model)
        
        self.session.flush()
        return order

    async def get_by_id(self, order_id: OrderId) -> Optional[Order]:
        """Get order by ID"""
        model = self.session.query(OrderModel).filter(OrderModel.id == order_id.value).first()
        return self._map_to_entity(model) if model else None

    async def get_by_user_id(self, user_id: UserId) -> List[Order]:
        """Get orders by user ID"""
        models = self.session.query(OrderModel).filter(OrderModel.user_id == user_id.value).all()
        return [self._map_to_entity(model) for model in models]

    async def add(self, order: Order) -> Order:
        """Add a new order"""
        # Create model without ID for new orders
        # Handle product_type - it might be an enum or already a string
        product_type_value = order.product_type.value if hasattr(order.product_type, 'value') else str(order.product_type)
        status_value = order.status.value if hasattr(order.status, 'value') else str(order.status)
        
        model_data = {
            'user_id': order.user_id.value,
            'dodo_order_id': order.dodo_order_id,
            'dodo_payment_id': order.dodo_payment_id,
            'product_type': product_type_value,
            'amount': order.amount.amount,
            'currency': order.amount.currency,
            'status': status_value,
            'created_at': order.created_at,
            'updated_at': order.updated_at,
            'completed_at': order.completed_at
        }
        
        model = OrderModel(**model_data)
        self.session.add(model)
        self.session.flush()
        
        # Create a new Order entity with the generated ID
        from ...domain.value_objects.money import Money
        
        order_with_id = Order(
            id=OrderId(model.id),
            user_id=order.user_id,
            dodo_order_id=order.dodo_order_id,
            dodo_payment_id=order.dodo_payment_id,
            product_type=order.product_type,
            amount=order.amount,
            status=order.status,
            created_at=order.created_at,
            updated_at=order.updated_at,
            completed_at=order.completed_at
        )
        
        return order_with_id

    async def update(self, order: Order) -> Order:
        """Update an existing order"""
        existing = self.session.query(OrderModel).filter(OrderModel.id == order.id.value).first()
        if existing:
            self._update_model_from_entity(existing, order)
            self.session.flush()
        return order

    async def get_by_payment_provider_id(self, provider_id: str) -> Optional[Order]:
        """Get order by payment provider ID"""
        model = self.session.query(OrderModel).filter(OrderModel.dodo_order_id == provider_id).first()
        return self._map_to_entity(model) if model else None

    async def count(self) -> int:
        """Count total orders"""
        return self.session.query(OrderModel).count()

    async def get_paid_orders(self) -> List[Order]:
        """Get all paid orders"""
        from ...domain.enums import OrderStatus
        models = self.session.query(OrderModel).filter(OrderModel.status == OrderStatus.COMPLETED.value).all()
        return [self._map_to_entity(model) for model in models]

    def get_all(self, skip: int = 0, limit: int = 100) -> List[Order]:
        """Get all orders (legacy method)"""
        models = self.session.query(OrderModel).offset(skip).limit(limit).all()
        return [self._map_to_entity(model) for model in models]

    def count_total_orders(self) -> int:
        """Count total orders (legacy method)"""
        return self.session.query(OrderModel).count()

    def count_by_status(self, status: OrderStatus) -> int:
        """Count orders by status (legacy method)"""
        return self.session.query(OrderModel).filter(OrderModel.status == status.value).count()

    def delete_legacy(self, order_id: OrderId) -> bool:
        """Delete order (legacy method)"""
        order = self.session.query(OrderModel).filter(OrderModel.id == order_id.value).first()
        if order:
            self.session.delete(order)
            return True
        return False

    def _create_model_from_entity(self, order: Order) -> OrderModel:
        """Create ORM model from domain entity"""
        # Handle product_type and status - they might be enums or already strings
        product_type_value = order.product_type.value if hasattr(order.product_type, 'value') else str(order.product_type)
        status_value = order.status.value if hasattr(order.status, 'value') else str(order.status)
        
        return OrderModel(
            user_id=order.user_id.value,
            dodo_order_id=order.dodo_order_id,
            dodo_payment_id=order.dodo_payment_id,
            product_type=product_type_value,
            amount=order.amount.amount,
            currency=order.amount.currency,
            status=status_value,
            created_at=order.created_at,
            updated_at=order.updated_at,
            completed_at=order.completed_at
        )

    def _update_model_from_entity(self, model: OrderModel, order: Order) -> None:
        """Update ORM model from domain entity"""
        # Handle product_type and status - they might be enums or already strings
        product_type_value = order.product_type.value if hasattr(order.product_type, 'value') else str(order.product_type)
        status_value = order.status.value if hasattr(order.status, 'value') else str(order.status)
        
        model.dodo_order_id = order.dodo_order_id
        model.dodo_payment_id = order.dodo_payment_id
        model.product_type = product_type_value
        model.amount = order.amount.amount
        model.currency = order.amount.currency
        model.status = status_value
        model.updated_at = order.updated_at
        model.completed_at = order.completed_at

    def _map_to_entity(self, model: OrderModel) -> Order:
        """Map ORM model to domain entity"""
        from ...domain.value_objects.money import Money
        from ...domain.enums import ProductType
        
        return Order(
            id=OrderId(model.id),
            user_id=UserId(model.user_id),
            dodo_order_id=model.dodo_order_id,
            dodo_payment_id=model.dodo_payment_id,
            product_type=ProductType(model.product_type),
            amount=Money(model.amount, model.currency),
            status=OrderStatus(model.status),
            created_at=model.created_at,
            updated_at=model.updated_at,
            completed_at=model.completed_at
        ) 