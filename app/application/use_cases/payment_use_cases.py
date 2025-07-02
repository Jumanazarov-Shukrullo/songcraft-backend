"""Payment use cases"""

from ...domain.repositories.unit_of_work import IUnitOfWork
from ...infrastructure.external_services.payment_service import PaymentService
from ..dtos.order_dtos import PaymentWebhookData


class ProcessPaymentUseCase:
    
    def __init__(
        self,
        unit_of_work: IUnitOfWork,
        payment_service: PaymentService
    ):
        self.unit_of_work = unit_of_work
        self.payment_service = payment_service
    
    async def process_webhook(self, payload: bytes, signature: str) -> bool:
        """Process payment webhook"""
        # Verify webhook signature
        is_valid = await self.payment_service.verify_webhook(payload, signature)
        if not is_valid:
            return False
        
        # Parse webhook data
        import json
        data = json.loads(payload.decode())
        
        # Extract order information
        custom_data = data.get("meta", {}).get("custom_data", {})
        user_id = custom_data.get("user_id")
        payment_id = data.get("data", {}).get("id")
        
        if not user_id or not payment_id:
            return False
        
        async with self.unit_of_work:
            # Find pending order for user
            from ...domain.value_objects.entity_ids import UserId
            from ...domain.enums import OrderStatus
            
            orders = await self.unit_of_work.orders.get_by_user_id(UserId(int(user_id)))
            pending_order = next(
                (o for o in orders if o.status == OrderStatus.PENDING),
                None
            )
            
            if not pending_order:
                return False
            
            # Mark order as paid
            pending_order.mark_as_paid(payment_id)
            await self.unit_of_work.orders.update(pending_order)
            await self.unit_of_work.commit()
            
            return True 