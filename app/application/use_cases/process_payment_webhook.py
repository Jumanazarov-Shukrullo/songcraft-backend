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
    
    async def execute(self, payload: bytes, signature: str, request_headers: dict = None) -> bool:
        """Process payment webhook from Stripe"""
        # Verify webhook signature (sync method, don't await)
        is_valid = self.payment_service.verify_webhook(payload, signature, request_headers or {})
        if not is_valid:
            print("❌ Webhook signature verification failed")
            return False
        
        try:
            # Parse webhook data
            data = json.loads(payload.decode())
            print(f"📨 Received webhook data: {json.dumps(data, indent=2)}")
            
            event_type = data.get("type")
            
            # Only process checkout session completed events for payments
            if event_type == "checkout.session.completed":
                return await self._handle_checkout_completed(data)
            else:
                print(f"⚠️ Ignoring webhook event: {event_type}")
                return True  # Return True to acknowledge receipt but ignore the event
            
        except Exception as e:
            print(f"❌ Error processing webhook: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def _handle_checkout_completed(self, data: dict) -> bool:
        """Handle Stripe checkout.session.completed event"""
        try:
            # Extract order information from Stripe checkout session
            session_data = data.get("data", {}).get("object", {})
            metadata = session_data.get("metadata", {})
            
            user_id = metadata.get("user_id")
            order_id = metadata.get("order_id")
            payment_id = session_data.get("id")  # Stripe session ID
            customer_email = session_data.get("customer_details", {}).get("email") or session_data.get("customer_email")
            amount_total = session_data.get("amount_total", 0)
            
            print(f"📋 Extracted: user_id={user_id}, order_id={order_id}, payment_id={payment_id}")
            print(f"💰 Amount: ${amount_total/100:.2f}, Customer: {customer_email}")
            
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
                
                # Add credits to user for paid orders
                print(f"💳 Adding 5 song credits to user {user_id} for paid order {order_id}")
                
                user_repo = self.unit_of_work.users
                user = await user_repo.get_by_id(UserId.from_str(user_id))
                if user:
                    old_credits = user.song_credits
                    user.add_song_credits(5)  # Add 5 credits for payment
                    await user_repo.update(user)
                    print(f"✅ Added 5 credits to user {user_id}. Credits: {old_credits} → {user.song_credits}")
                else:
                    print(f"❌ User {user_id} not found for credit addition")
                    # Don't fail the webhook for this - order was still processed
                
                await self.unit_of_work.commit()
                
                print(f"✅ Order {order_id} marked as paid with payment_id: {payment_id}")
                return True
        except Exception as e:
            print(f"❌ Error processing checkout completion: {e}")
            import traceback
            traceback.print_exc()
            return False 