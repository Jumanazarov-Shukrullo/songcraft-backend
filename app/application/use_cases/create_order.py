"""Create Order Use Case"""

from ...domain.entities.order import Order
from ...domain.value_objects.entity_ids import OrderId, UserId
from ...domain.value_objects.money import Money
from ...domain.enums import OrderStatus
from ...domain.repositories.unit_of_work import IUnitOfWork
from ...infrastructure.external_services.payment_service import PaymentService
from ...application.dtos.order_dtos import OrderCreateDTO, OrderResponseDTO


class CreateOrderUseCase:
    """Use case for creating a new order"""
    
    def __init__(self, unit_of_work: IUnitOfWork, payment_service: PaymentService):
        self.unit_of_work = unit_of_work
        self.payment_service = payment_service
    
    async def execute(self, order_data: OrderCreateDTO, user_id: int) -> OrderResponseDTO:
        """Execute the create order use case"""
        async with self.unit_of_work:
            # Create money value object
            money = Money(amount=order_data.amount, currency=order_data.currency)
            
            # Create order entity
            order = Order(
                id=OrderId.generate(),
                user_id=UserId(user_id),
                amount=money,
                product_type=order_data.product_type,
                status=OrderStatus.PENDING
            )
            
            # Save to repository
            order_repo = self.unit_of_work.order_repository
            saved_order = order_repo.add(order)
            
            # Create payment session with external payment service
            try:
                payment_url = await self.payment_service.create_payment_session(
                    amount=order_data.amount,
                    currency=order_data.currency,
                    product_name=f"{order_data.product_type.value} Song",
                    order_id=saved_order.id.value,
                    user_id=user_id
                )
                
                # Update order with payment information
                saved_order.payment_id = payment_url  # Store payment session info
                
            except Exception as e:
                # If payment creation fails, still save order but mark as failed
                saved_order.status = OrderStatus.FAILED
                
            await self.unit_of_work.commit()
            
            # Convert to response DTO
            return OrderResponseDTO.from_entity(saved_order) 