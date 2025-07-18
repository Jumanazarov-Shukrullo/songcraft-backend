"""Payment service for processing payments via Dodo Payments SDK"""

import os
from typing import Dict, Optional
from datetime import datetime, timedelta

from dodopayments import DodoPayments
from ...core.config import settings


class PaymentService:
    
    def __init__(self):
        self.api_key = settings.DODO_PAYMENTS_API_KEY
        self.webhook_secret = settings.DODO_PAYMENTS_WEBHOOK_SECRET
        self.audio_product_id = settings.DODO_AUDIO_PRODUCT_ID
        self.video_product_id = settings.DODO_VIDEO_PRODUCT_ID
        
        # Initialize Dodo Payments client
        self.client = DodoPayments(
            bearer_token=self.api_key
        )
    
    async def create_checkout_session(self, 
                                    customer_email: str,
                                    product_type: str,  # "audio_only" or "audio_video"
                                    custom_data: Dict = None) -> Dict:
        """Create payment link with Dodo Payments SDK"""
        try:
            print(f"💳 Creating Dodo Payments checkout for {product_type}...")
            
            # Determine product ID based on type
            if product_type == "audio_only":
                product_id = self.audio_product_id
            elif product_type == "audio_video":
                product_id = self.video_product_id
            else:
                raise ValueError(f"Invalid product type: {product_type}")
            
            # Extract customer info - convert Email object to string first
            email_str = str(customer_email)
            customer_name = (custom_data or {}).get("customer_name", email_str.split("@")[0])
            payment_method = (custom_data or {}).get("payment_method", "international")
            
            print(f"🔗 Creating payment with product ID: {product_id}")
            print(f"👤 Customer: {email_str}")
            print(f"💳 Payment method: {payment_method}")
            
            # Determine billing country based on payment method
            if payment_method == "mir":
                billing_country = "RU"  # Russia for MIR cards
                print("🇷🇺 Using MIR payment method for Russian users")
            else:
                billing_country = "US"  # Default to US for international cards
            
            # Create payment using Dodo Payments SDK
            payment_data = {
                "payment_link": True,
                "billing": {
                    "city": "N/A",
                    "country": billing_country, 
                    "state": "N/A",
                    "street": "N/A",
                    "zipcode": 0
                },
                "customer": {
                    "email": email_str,
                    "name": customer_name
                },
                "product_cart": [{
                    "product_id": product_id,
                    "quantity": 1
                }],
                "return_url": f"{settings.FRONTEND_URL}/payment/success"
            }
            
            # Add payment method specific settings if needed
            if payment_method == "mir":
                # Add any MIR-specific configuration here
                payment_data["metadata"] = {
                    "payment_method": "mir",
                    "country": "RU"
                }
            
            payment = self.client.payments.create(**payment_data)
            
            # Extract payment link and ID from response
            payment_link = payment.payment_link
            payment_id = payment.payment_id
            
            if not payment_link:
                raise Exception("No payment_link in SDK response")
            
            result = {
                "checkout_id": payment_id,
                "checkout_url": payment_link,
                "payment_id": payment_id,
                "expires_at": (datetime.now() + timedelta(hours=24)).isoformat() + "Z",
                "product_type": product_type,
                "currency": "USD"
            }
            
            print(f"✅ Dodo Payments checkout created successfully")
            print(f"🆔 Payment ID: {payment_id}")
            print(f"🔗 Payment Link: {payment_link}")
            return result
                    
        except Exception as e:
            print(f"❌ Error creating Dodo Payments checkout: {e}")
            raise Exception(f"Failed to create checkout: {e}")
    
    async def get_checkout_status(self, checkout_id: str) -> Dict:
        """Get payment status from Dodo Payments"""
        try:
            # Use SDK to get payment information if available
            # Note: Check Dodo Payments SDK docs for payment retrieval method
            return {
                "payment_id": checkout_id,
                "status": "pending",  # This would come from SDK
                "currency": "USD"
            }
                    
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def verify_webhook(self, payload: bytes, signature: str) -> bool:
        """Verify webhook signature from Dodo Payments using Standard Webhooks spec"""
        try:
            import hmac
            import hashlib
            
            # Dodo Payments uses Standard Webhooks specification
            # The signature should be in format: v1,signature1,signature2...
            if not signature.startswith("v1,"):
                return False
            
            # Extract signatures (remove v1, prefix)
            signatures = signature[3:].split(",")
            
            # Generate expected signature using webhook secret
            expected_signature = hmac.new(
                self.webhook_secret.encode(),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            # Check if any signature matches
            return any(hmac.compare_digest(sig, expected_signature) for sig in signatures)
            
        except Exception as e:
            print(f"❌ Dodo webhook verification error: {e}")
            return False
    
    async def process_webhook(self, webhook_data: Dict) -> Dict:
        """Process webhook from Dodo Payments"""
        try:
            event_type = webhook_data.get("type")
            payment_data = webhook_data.get("data", {})
            
            print(f"📨 Processing Dodo webhook: {event_type}")
            
            if event_type == "payment.succeeded":
                return await self._handle_payment_succeeded(payment_data)
            elif event_type == "payment.failed":
                return await self._handle_payment_failed(payment_data)
            elif event_type == "payment.refunded":
                return await self._handle_payment_refunded(payment_data)
            else:
                print(f"⚠️ Unhandled Dodo webhook event: {event_type}")
                return {"status": "ignored", "event": event_type}
                
        except Exception as e:
            print(f"❌ Error processing Dodo webhook: {e}")
            return {"status": "error", "error": str(e)}
    
    async def _handle_payment_succeeded(self, payment_data: Dict) -> Dict:
        """Handle successful payment"""
        try:
            payment_id = payment_data.get("payment_id")
            customer_email = payment_data.get("customer_email")
            total_amount = payment_data.get("total_amount", 0)
            
            print(f"✅ Payment succeeded: {payment_id}")
            print(f"💰 Amount: ${total_amount}")
            print(f"👤 Customer: {customer_email}")
            
            return {
                "status": "success",
                "payment_id": payment_id,
                "amount": total_amount,
                "customer_email": customer_email
            }
            
        except Exception as e:
            print(f"❌ Error handling payment success: {e}")
            return {"status": "error", "error": str(e)}
    
    async def _handle_payment_failed(self, payment_data: Dict) -> Dict:
        """Handle failed payment"""
        try:
            payment_id = payment_data.get("payment_id")
            error_message = payment_data.get("error_message", "Unknown error")
            
            print(f"❌ Payment failed: {payment_id}")
            print(f"💭 Reason: {error_message}")
            
            return {
                "status": "failed",
                "payment_id": payment_id,
                "error": error_message
            }
            
        except Exception as e:
            print(f"❌ Error handling payment failure: {e}")
            return {"status": "error", "error": str(e)}
    
    async def _handle_payment_refunded(self, payment_data: Dict) -> Dict:
        """Handle refunded payment"""
        try:
            payment_id = payment_data.get("payment_id")
            refund_amount = payment_data.get("refund_amount", 0)
            
            print(f"🔄 Payment refunded: {payment_id}")
            print(f"💰 Refund amount: ${refund_amount}")
            
            return {
                "status": "refunded",
                "payment_id": payment_id,
                "refund_amount": refund_amount
            }
            
        except Exception as e:
            print(f"❌ Error handling payment refund: {e}")
            return {"status": "error", "error": str(e)}
    
    async def create_customer(self, email: str, name: str = None) -> Dict:
        """Create customer (if supported by SDK)"""
        return {
            "customer_id": email,  # Placeholder - check SDK docs
            "email": email,
            "name": name or email.split("@")[0]
        }
    
    async def get_payment(self, payment_id: str) -> Optional[Dict]:
        """Get payment details (if supported by SDK)"""
        try:
            # Check Dodo Payments SDK for payment retrieval method
            return {
                "payment_id": payment_id,
                "status": "unknown"  # This would come from SDK
            }
        except Exception as e:
            print(f"❌ Error getting payment: {e}")
            return None
    
    async def create_checkout(self, product_type: str, user_email: str, user_id: str) -> str:
        """Create checkout and return payment URL"""
        try:
            result = await self.create_checkout_session(
                customer_email=user_email,
                product_type=product_type,
                custom_data={
                    "user_id": user_id,
                    "customer_name": user_email.split("@")[0]
                }
            )
            return result["checkout_url"]
        except Exception as e:
            print(f"❌ Error in create_checkout: {e}")
            raise 