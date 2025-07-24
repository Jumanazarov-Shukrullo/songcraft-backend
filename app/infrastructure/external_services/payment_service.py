"""Payment service for processing payments via Stripe"""

import os
import stripe
from typing import Dict, Optional
from datetime import datetime, timedelta

from ...core.config import settings


class PaymentService:
    
    def __init__(self):
        # Initialize Stripe
        stripe.api_key = settings.STRIPE_SECRET_KEY
        self.webhook_secret = settings.STRIPE_WEBHOOK_SECRET
        self.audio_product_id = settings.STRIPE_AUDIO_PRODUCT_ID
        self.video_product_id = settings.STRIPE_VIDEO_PRODUCT_ID
    
    async def create_checkout_session(self, 
                                    customer_email: str,
                                    product_type: str,  # "audio_only" or "audio_video"
                                    custom_data: Dict = None) -> Dict:
        """Create Stripe checkout session using pre-configured products"""
        try:
            print(f"💳 Creating Stripe checkout session for {product_type}...")
            
            # Determine product ID based on type
            if product_type == "audio_only":
                product_id = self.audio_product_id
                product_name = "AI Song Generation - Audio Only"
            elif product_type == "audio_video":
                product_id = self.video_product_id
                product_name = "AI Song Generation - Audio + Video"
            else:
                raise ValueError(f"Invalid product type: {product_type}")
            
            # Extract custom data
            user_id = (custom_data or {}).get("user_id")
            order_id = (custom_data or {}).get("order_id")
            song_data = (custom_data or {}).get("song_data")
            
            print(f"🔗 Creating checkout session for {product_name}")
            print(f"👤 Customer: {customer_email}")
            print(f"🆔 Product ID: {product_id}")
            
            # Create Stripe checkout session using product ID
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price': product_id,  # Use the price ID from your Stripe product
                    'quantity': 1,
                }],
                mode='payment',
                success_url=f"{settings.FRONTEND_URL}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{settings.FRONTEND_URL}/payment/cancel",
                customer_email=customer_email,
                metadata={
                    'user_id': user_id or '',
                    'order_id': order_id or '',
                    'product_type': product_type
                    # Note: song_data removed due to Stripe 500 char limit per metadata value
                    # Song data can be retrieved using order_id when processing webhook
                }
            )
            
            result = {
                "checkout_id": session.id,
                "checkout_url": session.url,
                "payment_id": session.id,
                "expires_at": (datetime.now() + timedelta(hours=24)).isoformat() + "Z",
                "product_type": product_type,
                "currency": "USD"
            }
            
            print(f"✅ Stripe checkout session created successfully")
            print(f"🆔 Session ID: {session.id}")
            print(f"🔗 Checkout URL: {session.url}")
            return result
                    
        except stripe.error.StripeError as e:
            print(f"❌ Stripe error creating checkout: {e}")
            raise Exception(f"Failed to create checkout: {e}")
        except Exception as e:
            print(f"❌ Error creating Stripe checkout: {e}")
            raise Exception(f"Failed to create checkout: {e}")
    
    async def get_checkout_status(self, checkout_id: str) -> Dict:
        """Get payment status from Stripe"""
        try:
            session = stripe.checkout.Session.retrieve(checkout_id)
            
            # Map Stripe status to our status
            if session.payment_status == 'paid':
                status = 'completed'
            elif session.payment_status == 'unpaid':
                status = 'pending'
            else:
                status = 'failed'
            
            return {
                "payment_id": checkout_id,
                "status": status,
                "currency": session.currency.upper() if session.currency else "USD"
            }
                    
        except stripe.error.StripeError as e:
            print(f"❌ Stripe error getting checkout status: {e}")
            return {"status": "error", "error": str(e)}
        except Exception as e:
            print(f"❌ Error getting checkout status: {e}")
            return {"status": "error", "error": str(e)}
    
    def verify_webhook(self, payload: bytes, signature: str, request_headers: dict = None) -> bool:
        """Verify webhook signature from Stripe"""
        try:
            print(f"🔍 Verifying Stripe webhook signature...")
            print(f"🔧 Webhook secret configured: {bool(self.webhook_secret)}")
            print(f"🔧 Webhook secret (first 10 chars): {self.webhook_secret[:10] if self.webhook_secret else 'None'}...")
            print(f"🔧 Signature: {signature[:50] if signature else 'None'}...")
            
            if not self.webhook_secret:
                print("❌ No webhook secret configured")
                return False
            
            if not signature:
                print("❌ No signature header provided")
                return False
            
            # Verify the webhook signature using Stripe's library
            try:
                stripe.Webhook.construct_event(
                    payload, signature, self.webhook_secret
                )
                print("✅ Stripe webhook signature verified successfully")
                return True
            except stripe.error.SignatureVerificationError as e:
                print(f"❌ CRITICAL SECURITY ERROR: Stripe webhook signature verification failed")
                print(f"🔧 This could be an attack attempt or misconfigured webhook")
                print(f"🔧 Signature format expected: t=timestamp,v1=signature") 
                print(f"🔧 Received signature: {signature}")
                print(f"🔧 Webhook secret configured: {bool(self.webhook_secret)}")
                print(f"❌ WEBHOOK REJECTED FOR SECURITY")
                return False
            
        except stripe.error.SignatureVerificationError as e:
            print(f"❌ Stripe webhook signature verification failed: {e}")
            return False
        except Exception as e:
            print(f"❌ Stripe webhook verification error: {e}")
            return False
    
    async def process_webhook(self, webhook_data: Dict) -> Dict:
        """Process webhook from Stripe"""
        try:
            event_type = webhook_data.get("type")
            payment_data = webhook_data.get("data", {}).get("object", {})
            
            print(f"📨 Processing Stripe webhook: {event_type}")
            
            if event_type == "checkout.session.completed":
                return await self._handle_checkout_completed(payment_data)
            elif event_type == "payment_intent.succeeded":
                return await self._handle_payment_succeeded(payment_data)
            elif event_type == "payment_intent.payment_failed":
                return await self._handle_payment_failed(payment_data)
            elif event_type == "charge.dispute.created":
                return await self._handle_payment_disputed(payment_data)
            else:
                print(f"⚠️ Unhandled Stripe webhook event: {event_type}")
                return {"status": "ignored", "event": event_type}
                
        except Exception as e:
            print(f"❌ Error processing Stripe webhook: {e}")
            return {"status": "error", "error": str(e)}
    
    async def _handle_checkout_completed(self, session_data: Dict) -> Dict:
        """Handle completed checkout session"""
        try:
            session_id = session_data.get("id")
            customer_email = session_data.get("customer_details", {}).get("email") or session_data.get("customer_email")
            amount_total = session_data.get("amount_total", 0)
            metadata = session_data.get("metadata", {})
            
            print(f"✅ Checkout session completed: {session_id}")
            print(f"💰 Amount: ${amount_total/100:.2f}")
            print(f"👤 Customer: {customer_email}")
            print(f"📝 Metadata: {metadata}")
            
            return {
                "status": "success",
                "payment_id": session_id,
                "amount": amount_total,
                "customer_email": customer_email,
                "metadata": metadata
            }
            
        except Exception as e:
            print(f"❌ Error handling checkout completion: {e}")
            return {"status": "error", "error": str(e)}
    
    async def _handle_payment_succeeded(self, payment_data: Dict) -> Dict:
        """Handle successful payment intent"""
        try:
            payment_id = payment_data.get("id")
            customer_email = payment_data.get("receipt_email")
            amount = payment_data.get("amount", 0)
            
            print(f"✅ Payment intent succeeded: {payment_id}")
            print(f"💰 Amount: ${amount/100:.2f}")
            print(f"👤 Customer: {customer_email}")
            
            return {
                "status": "success",
                "payment_id": payment_id,
                "amount": amount,
                "customer_email": customer_email
            }
            
        except Exception as e:
            print(f"❌ Error handling payment success: {e}")
            return {"status": "error", "error": str(e)}
    
    async def _handle_payment_failed(self, payment_data: Dict) -> Dict:
        """Handle failed payment"""
        try:
            payment_id = payment_data.get("id")
            error_message = payment_data.get("last_payment_error", {}).get("message", "Unknown error")
            
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
    
    async def _handle_payment_disputed(self, dispute_data: Dict) -> Dict:
        """Handle payment dispute/chargeback"""
        try:
            dispute_id = dispute_data.get("id")
            charge_id = dispute_data.get("charge")
            amount = dispute_data.get("amount", 0)
            reason = dispute_data.get("reason", "Unknown")
            
            print(f"🔄 Payment disputed: {dispute_id}")
            print(f"💰 Dispute amount: ${amount/100:.2f}")
            print(f"💭 Reason: {reason}")
            
            return {
                "status": "disputed",
                "dispute_id": dispute_id,
                "charge_id": charge_id,
                "amount": amount,
                "reason": reason
            }
            
        except Exception as e:
            print(f"❌ Error handling payment dispute: {e}")
            return {"status": "error", "error": str(e)}
    
    async def create_customer(self, email: str, name: str = None) -> Dict:
        """Create Stripe customer"""
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name or email.split("@")[0]
            )
            
            return {
                "customer_id": customer.id,
                "email": customer.email,
                "name": customer.name
            }
        except stripe.error.StripeError as e:
            print(f"❌ Error creating Stripe customer: {e}")
            raise Exception(f"Failed to create customer: {e}")
    
    async def get_payment(self, payment_id: str) -> Optional[Dict]:
        """Get payment details from Stripe"""
        try:
            # Try to get as checkout session first, then as payment intent
            try:
                session = stripe.checkout.Session.retrieve(payment_id)
                return {
                    "payment_id": payment_id,
                    "status": session.payment_status,
                    "amount": session.amount_total,
                    "currency": session.currency
                }
            except:
                # Try as payment intent
                payment_intent = stripe.PaymentIntent.retrieve(payment_id)
                return {
                    "payment_id": payment_id,
                    "status": payment_intent.status,
                    "amount": payment_intent.amount,
                    "currency": payment_intent.currency
                }
        except stripe.error.StripeError as e:
            print(f"❌ Error getting Stripe payment: {e}")
            return None
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