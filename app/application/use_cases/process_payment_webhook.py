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
        # Verify webhook signature (sync method, don't await)
        is_valid = self.payment_service.verify_webhook(payload, signature)
        if not is_valid:
            print("❌ Webhook signature verification failed")
            return False
        
        try:
            # Parse webhook data
            data = json.loads(payload.decode())
            print(f"📨 Received webhook data: {json.dumps(data, indent=2)}")
            
            # Extract order information from Dodo Payments webhook
            payment_data = data.get("data", {})
            custom_data = payment_data.get("custom_data", {})
            user_id = custom_data.get("user_id")
            order_id = custom_data.get("order_id")
            payment_id = payment_data.get("id")
            
            print(f"📋 Extracted: user_id={user_id}, order_id={order_id}, payment_id={payment_id}")
            
            if not user_id or not order_id or not payment_id:
                print(f"❌ Missing required data in webhook: user_id={user_id}, order_id={order_id}, payment_id={payment_id}")
                return False
            
            async with self.unit_of_work:
                # Find specific pending order by ID
                from ...domain.value_objects.entity_ids import OrderId
                
                print(f"🔍 Looking for order: {order_id}")
                pending_order = await self.unit_of_work.orders.get_by_id(OrderId.from_str(order_id))
                
                if not pending_order:
                    print(f"❌ Order {order_id} not found")
                    return False
                    
                if pending_order.status != OrderStatus.PENDING:
                    print(f"❌ Order {order_id} is not pending (status: {pending_order.status})")
                    return False
                
                print(f"✅ Found pending order {order_id}, marking as paid")
                
                # Mark order as paid
                pending_order.mark_as_paid(payment_id)
                await self.unit_of_work.orders.update(pending_order)
                await self.unit_of_work.commit()
                
                print(f"✅ Order {order_id} marked as paid with payment_id: {payment_id}")
                return True
        except Exception as e:
            print(f"❌ Error processing webhook: {e}")
            import traceback
            traceback.print_exc()
            return False 