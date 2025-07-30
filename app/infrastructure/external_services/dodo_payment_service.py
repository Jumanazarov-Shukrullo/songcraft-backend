"""DoDo payment service for processing payments via DoDo API"""

import httpx
import uuid
import hmac
import hashlib
from typing import Dict, Optional
from datetime import datetime, timedelta

from ...core.config import settings


class DodoPaymentService:
    """DoDo payment service implementation"""
    
    def __init__(self):
        self.api_key = settings.DODO_API_KEY
        self.secret_key = settings.DODO_SECRET_KEY
        self.webhook_secret = settings.DODO_WEBHOOK_SECRET
        self.api_url = settings.DODO_API_URL
        
    async def create_checkout_session(self, 
                                    customer_email: str,
                                    product_type: str,  # "audio_only" or "audio_video"
                                    custom_data: Dict = None) -> Dict:
        """Create DoDo checkout session"""
        try:
            print(f"🦤 Creating DoDo checkout session for {product_type}...")
            
            # Determine price based on type
            if product_type == "audio_only":
                amount = settings.AUDIO_PRICE
                product_name = "AI Song Generation - Audio Only"
            elif product_type == "audio_video":
                amount = settings.VIDEO_PRICE
                product_name = "AI Song Generation - Audio + Video"
            else:
                raise ValueError(f"Invalid product type: {product_type}")
            
            # Extract custom data
            user_id = (custom_data or {}).get("user_id")
            order_id = (custom_data or {}).get("order_id")
            
            checkout_id = str(uuid.uuid4())
            
            print(f"🔗 Creating DoDo checkout session for {product_name}")
            print(f"👤 Customer: {customer_email}")
            print(f"💰 Amount: ${amount/100:.2f}")
            
            # Create DoDo payment request
            payment_data = {
                "checkout_id": checkout_id,
                "amount": amount,
                "currency": "USD",
                "customer_email": customer_email,
                "product_name": product_name,
                "product_type": product_type,
                "success_url": f"{settings.FRONTEND_URL}/payment/success?session_id={checkout_id}",
                "cancel_url": f"{settings.FRONTEND_URL}/payment/cancel",
                "webhook_url": f"{settings.BACKEND_URL}/api/v1/payments/dodo-webhook",
                "metadata": {
                    "user_id": user_id or '',
                    "order_id": order_id or '',
                    "product_type": product_type
                }
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.api_url}/checkout",
                    json=payment_data,
                    headers=headers
                )
                
                if response.status_code != 200:
                    raise Exception(f"DoDo API error: {response.status_code} - {response.text}")
                
                dodo_response = response.json()
            
            result = {
                "checkout_id": checkout_id,
                "checkout_url": dodo_response.get("checkout_url", f"https://checkout.dodo.dev/{checkout_id}"),
                "payment_id": checkout_id,
                "expires_at": (datetime.now() + timedelta(hours=24)).isoformat() + "Z",
                "product_type": product_type,
                "currency": "USD"
            }
            
            print(f"✅ DoDo checkout session created successfully")
            print(f"🆔 Session ID: {checkout_id}")
            print(f"🔗 Checkout URL: {result['checkout_url']}")
            return result
                    
        except Exception as e:
            print(f"❌ Error creating DoDo checkout: {e}")
            raise Exception(f"Failed to create DoDo checkout: {e}")
    
    async def get_checkout_status(self, checkout_id: str) -> Dict:
        """Get payment status from DoDo"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.api_url}/checkout/{checkout_id}/status",
                    headers=headers
                )
                
                if response.status_code != 200:
                    return {"status": "error", "error": f"DoDo API error: {response.status_code}"}
                
                dodo_response = response.json()
                
                # Map DoDo status to our status
                dodo_status = dodo_response.get("status", "pending")
                if dodo_status == "completed":
                    status = "completed"
                elif dodo_status == "pending":
                    status = "pending"
                else:
                    status = "failed"
                
                return {
                    "payment_id": checkout_id,
                    "status": status,
                    "currency": "USD"
                }
                    
        except Exception as e:
            print(f"❌ Error getting DoDo checkout status: {e}")
            return {"status": "error", "error": str(e)}
    
    async def process_webhook(self, webhook_data: Dict) -> Dict:
        """Process webhook from DoDo"""
        try:
            event_type = webhook_data.get("event_type")
            payment_data = webhook_data.get("data", {})
            
            print(f"📨 Processing DoDo webhook: {event_type}")
            
            if event_type == "payment.completed":
                return await self._handle_payment_completed(payment_data)
            elif event_type == "payment.failed":
                return await self._handle_payment_failed(payment_data)
            elif event_type == "payment.refunded":
                return await self._handle_payment_refunded(payment_data)
            else:
                print(f"⚠️ Unhandled DoDo webhook event: {event_type}")
                return {"status": "ignored", "event": event_type}
                
        except Exception as e:
            print(f"❌ Error processing DoDo webhook: {e}")
            return {"status": "error", "error": str(e)}
    
    async def _handle_payment_completed(self, payment_data: Dict) -> Dict:
        """Handle completed payment"""
        print(f"✅ DoDo payment completed: {payment_data.get('checkout_id')}")
        return {
            "status": "completed",
            "payment_id": payment_data.get("checkout_id"),
            "amount": payment_data.get("amount"),
            "currency": payment_data.get("currency", "USD"),
            "metadata": payment_data.get("metadata", {})
        }
    
    async def _handle_payment_failed(self, payment_data: Dict) -> Dict:
        """Handle failed payment"""
        print(f"❌ DoDo payment failed: {payment_data.get('checkout_id')}")
        return {
            "status": "failed",
            "payment_id": payment_data.get("checkout_id"),
            "error": payment_data.get("error_message", "Payment failed")
        }
    
    async def _handle_payment_refunded(self, payment_data: Dict) -> Dict:
        """Handle refunded payment"""
        print(f"🔄 DoDo payment refunded: {payment_data.get('checkout_id')}")
        return {
            "status": "refunded",
            "payment_id": payment_data.get("checkout_id"),
            "amount": payment_data.get("refund_amount"),
            "currency": payment_data.get("currency", "USD")
        }
    
    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Verify DoDo webhook signature"""
        try:
            expected_signature = hmac.new(
                self.webhook_secret.encode(),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(f"sha256={expected_signature}", signature)
        except Exception as e:
            print(f"❌ Error verifying DoDo webhook signature: {e}")
            return False
            
    async def get_payment(self, payment_id: str) -> Optional[Dict]:
        """Get payment details from DoDo"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.api_url}/payment/{payment_id}",
                    headers=headers
                )
                
                if response.status_code != 200:
                    return None
                
                payment_data = response.json()
                return {
                    "payment_id": payment_id,
                    "status": payment_data.get("status"),
                    "amount": payment_data.get("amount"),
                    "currency": payment_data.get("currency", "USD")
                }
                
        except Exception as e:
            print(f"❌ Error getting DoDo payment: {e}")
            return None 