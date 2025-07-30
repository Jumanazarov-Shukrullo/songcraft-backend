"""Gumroad payment service for processing payments via Gumroad API"""

import httpx
import uuid
import hmac
import hashlib
from typing import Dict, Optional
from datetime import datetime, timedelta

from ...core.config import settings


class GumroadPaymentService:
    """Gumroad payment service implementation"""
    
    def __init__(self):
        self.api_key = settings.GUMROAD_API_KEY
        self.webhook_secret = settings.GUMROAD_WEBHOOK_SECRET
        self.api_url = settings.GUMROAD_API_URL
        
    async def create_checkout_session(self, 
                                    customer_email: str,
                                    product_type: str,  # "audio_only" or "audio_video"
                                    custom_data: Dict = None) -> Dict:
        """Create Gumroad checkout session"""
        try:
            print(f"🛒 Creating Gumroad checkout session for {product_type}...")
            
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
            
            print(f"🔗 Creating Gumroad checkout session for {product_name}")
            print(f"👤 Customer: {customer_email}")
            print(f"💰 Amount: ${amount/100:.2f}")
            
            # Create Gumroad product/checkout request
            payment_data = {
                "name": product_name,
                "price": amount / 100,  # Gumroad expects price in dollars
                "currency": "USD",
                "description": f"Personalized AI-generated song - {product_type.replace('_', ' ').title()}",
                "return_url": f"{settings.FRONTEND_URL}/payment/success?session_id={checkout_id}",
                "cancel_url": f"{settings.FRONTEND_URL}/payment/cancel",
                "webhook_url": f"{settings.BACKEND_URL}/api/v1/payments/gumroad-webhook",
                "custom_fields": {
                    "user_id": user_id or '',
                    "order_id": order_id or '',
                    "product_type": product_type,
                    "checkout_id": checkout_id
                },
                "variants": [
                    {
                        "name": product_name,
                        "price": amount / 100,
                        "options": {}
                    }
                ]
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.api_url}/v2/products",
                    json=payment_data,
                    headers=headers
                )
                
                if response.status_code not in [200, 201]:
                    raise Exception(f"Gumroad API error: {response.status_code} - {response.text}")
                
                gumroad_response = response.json()
                product_id = gumroad_response.get("product", {}).get("id")
                
                if not product_id:
                    raise Exception("Failed to create Gumroad product")
            
            # Generate checkout URL
            checkout_url = f"https://gumroad.com/l/{product_id}"
            
            result = {
                "checkout_id": checkout_id,
                "checkout_url": checkout_url,
                "payment_id": checkout_id,
                "product_id": product_id,
                "expires_at": (datetime.now() + timedelta(hours=24)).isoformat() + "Z",
                "product_type": product_type,
                "currency": "USD"
            }
            
            print(f"✅ Gumroad checkout session created successfully")
            print(f"🆔 Session ID: {checkout_id}")
            print(f"🆔 Product ID: {product_id}")
            print(f"🔗 Checkout URL: {checkout_url}")
            return result
                    
        except Exception as e:
            print(f"❌ Error creating Gumroad checkout: {e}")
            raise Exception(f"Failed to create Gumroad checkout: {e}")
    
    async def get_checkout_status(self, checkout_id: str) -> Dict:
        """Get payment status from Gumroad"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Gumroad doesn't have direct checkout status, we check sales
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.api_url}/v2/sales",
                    headers=headers,
                    params={"per_page": 50}  # Get recent sales
                )
                
                if response.status_code != 200:
                    return {"status": "error", "error": f"Gumroad API error: {response.status_code}"}
                
                sales_data = response.json()
                sales = sales_data.get("sales", [])
                
                # Look for sale with our checkout_id in custom fields
                for sale in sales:
                    custom_fields = sale.get("custom_fields", {})
                    if custom_fields.get("checkout_id") == checkout_id:
                        return {
                            "payment_id": checkout_id,
                            "status": "completed" if sale.get("refunded", False) == False else "refunded",
                            "currency": "USD",
                            "sale_id": sale.get("id")
                        }
                
                # If not found in recent sales, assume pending
                return {
                    "payment_id": checkout_id,
                    "status": "pending",
                    "currency": "USD"
                }
                    
        except Exception as e:
            print(f"❌ Error getting Gumroad checkout status: {e}")
            return {"status": "error", "error": str(e)}
    
    async def process_webhook(self, webhook_data: Dict) -> Dict:
        """Process webhook from Gumroad"""
        try:
            # Gumroad sends direct sale data in webhook
            sale_data = webhook_data
            
            print(f"📨 Processing Gumroad webhook for sale: {sale_data.get('sale_id')}")
            
            custom_fields = sale_data.get("custom_fields", {})
            checkout_id = custom_fields.get("checkout_id")
            
            if not checkout_id:
                print("⚠️ No checkout_id found in Gumroad webhook")
                return {"status": "ignored", "reason": "no_checkout_id"}
            
            # Determine event type based on sale status
            if sale_data.get("refunded", False):
                return await self._handle_payment_refunded(sale_data)
            elif sale_data.get("sale_id"):
                return await self._handle_payment_completed(sale_data)
            else:
                return await self._handle_payment_failed(sale_data)
                
        except Exception as e:
            print(f"❌ Error processing Gumroad webhook: {e}")
            return {"status": "error", "error": str(e)}
    
    async def _handle_payment_completed(self, sale_data: Dict) -> Dict:
        """Handle completed payment"""
        custom_fields = sale_data.get("custom_fields", {})
        checkout_id = custom_fields.get("checkout_id")
        
        print(f"✅ Gumroad payment completed: {checkout_id}")
        
        return {
            "status": "completed",
            "payment_id": checkout_id,
            "amount": int(float(sale_data.get("price", 0)) * 100),  # Convert to cents
            "currency": "USD",
            "sale_id": sale_data.get("sale_id"),
            "metadata": {
                "user_id": custom_fields.get("user_id", ""),
                "order_id": custom_fields.get("order_id", ""),
                "product_type": custom_fields.get("product_type", "")
            }
        }
    
    async def _handle_payment_failed(self, sale_data: Dict) -> Dict:
        """Handle failed payment"""
        custom_fields = sale_data.get("custom_fields", {})
        checkout_id = custom_fields.get("checkout_id")
        
        print(f"❌ Gumroad payment failed: {checkout_id}")
        return {
            "status": "failed",
            "payment_id": checkout_id,
            "error": "Payment failed or cancelled"
        }
    
    async def _handle_payment_refunded(self, sale_data: Dict) -> Dict:
        """Handle refunded payment"""
        custom_fields = sale_data.get("custom_fields", {})
        checkout_id = custom_fields.get("checkout_id")
        
        print(f"🔄 Gumroad payment refunded: {checkout_id}")
        return {
            "status": "refunded",
            "payment_id": checkout_id,
            "amount": int(float(sale_data.get("price", 0)) * 100),  # Convert to cents
            "currency": "USD",
            "sale_id": sale_data.get("sale_id")
        }
    
    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Verify Gumroad webhook signature"""
        try:
            # Gumroad uses different signature verification
            # Check if webhook_secret is provided in the webhook data itself
            # Or verify based on Gumroad's specific method
            if not self.webhook_secret:
                return True  # Skip verification if no secret is configured
                
            expected_signature = hmac.new(
                self.webhook_secret.encode(),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(expected_signature, signature)
        except Exception as e:
            print(f"❌ Error verifying Gumroad webhook signature: {e}")
            return False
            
    async def get_payment(self, payment_id: str) -> Optional[Dict]:
        """Get payment details from Gumroad"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Search for sale by checkout_id in custom fields
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.api_url}/v2/sales",
                    headers=headers,
                    params={"per_page": 100}  # Search more sales
                )
                
                if response.status_code != 200:
                    return None
                
                sales_data = response.json()
                sales = sales_data.get("sales", [])
                
                # Look for sale with our payment_id
                for sale in sales:
                    custom_fields = sale.get("custom_fields", {})
                    if custom_fields.get("checkout_id") == payment_id:
                        return {
                            "payment_id": payment_id,
                            "status": "completed" if not sale.get("refunded", False) else "refunded",
                            "amount": int(float(sale.get("price", 0)) * 100),
                            "currency": "USD",
                            "sale_id": sale.get("id")
                        }
                
                return None
                
        except Exception as e:
            print(f"❌ Error getting Gumroad payment: {e}")
            return None 