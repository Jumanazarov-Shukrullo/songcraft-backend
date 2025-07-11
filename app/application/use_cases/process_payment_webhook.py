"""Process payment webhook use case"""

import json

from ...domain.repositories.unit_of_work import IUnitOfWork
from ...infrastructure.external_services.payment_service import PaymentService
from ...domain.value_objects.entity_ids import UserId
from ...domain.enums import OrderStatus


class ProcessPaymentWebhookUseCase:
    
    def __init__(self, unit_of_work: IUnitOfWork, payment_service: PaymentService):
        self.unit_of_work = unit_of_work
        self.payment_service = payment_service
    
    async def execute(self, payload: bytes, signature: str) -> bool:
        """Process payment webhook from payment provider"""
        # Verify webhook signature
        is_valid = await self.payment_service.verify_webhook(payload, signature)
        if not is_valid:
            return False
        
        try:
            # Parse webhook data
            data = json.loads(payload.decode())
            
            # Extract order information from Dodo Payments webhook
            payment_data = data.get("data", {})
            custom_data = payment_data.get("custom_data", {})
            user_id = custom_data.get("user_id")
            order_id = custom_data.get("order_id")
            payment_id = payment_data.get("id")
            
            if not user_id or not order_id or not payment_id:
                return False
            
            async with self.unit_of_work:
                # Find specific pending order by ID
                from ...domain.value_objects.entity_ids import OrderId
                
                pending_order = await self.unit_of_work.orders.get_by_id(OrderId.from_str(order_id))
                
                if not pending_order or pending_order.status != OrderStatus.PENDING:
                    return False
                
                # Mark order as paid
                pending_order.mark_as_paid(payment_id)
                await self.unit_of_work.orders.update(pending_order)
                await self.unit_of_work.commit()
                
                return True
        except Exception:
            return False 