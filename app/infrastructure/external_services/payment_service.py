"""Payment service for processing payments via LemonSqueezy"""

import httpx
from typing import Dict, Optional
from datetime import datetime, timedelta

from ...core.config import settings


class PaymentService:
    
    def __init__(self):
        self.api_key = settings.LEMONSQUEEZY_API_KEY
        self.store_id = settings.LEMONSQUEEZY_STORE_ID
        self.api_url = settings.LEMONSQUEEZY_API_URL
        self.webhook_secret = settings.LEMONSQUEEZY_WEBHOOK_SECRET
        self.product_id_audio = settings.LEMONSQUEEZY_PRODUCT_ID_AUDIO
        self.product_id_video = settings.LEMONSQUEEZY_PRODUCT_ID_VIDEO
    
    async def create_checkout_session(self, 
                                    customer_email: str,
                                    product_type: str,  # "audio" or "video"
                                    custom_data: Dict = None) -> Dict:
        """Create checkout session with LemonSqueezy"""
        try:
            print(f"💳 Creating LemonSqueezy checkout for {product_type}...")
            
            # Determine product ID and price
            if product_type == "audio":
                product_id = self.product_id_audio
                price = settings.AUDIO_PRICE
            elif product_type == "video":
                product_id = self.product_id_video  
                price = settings.VIDEO_PRICE
            else:
                raise ValueError(f"Invalid product type: {product_type}")
            
            # Prepare checkout data
            checkout_data = {
                "data": {
                    "type": "checkouts",
                    "attributes": {
                        "product_id": int(product_id),
                        "custom_price": price,  # Price in cents
                        "custom_data": {
                            "customer_email": customer_email,
                            "product_type": product_type,
                            **(custom_data or {})
                        },
                        "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat() + "Z",
                        "preview": False,
                        "test_mode": settings.ENVIRONMENT != "production"
                    },
                    "relationships": {
                        "store": {
                            "data": {
                                "type": "stores",
                                "id": self.store_id
                            }
                        }
                    }
                }
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/checkouts",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/vnd.api+json",
                        "Accept": "application/vnd.api+json"
                    },
                    json=checkout_data
                )
                
                if response.status_code == 201:
                    data = response.json()
                    checkout = data["data"]
                    
                    result = {
                        "checkout_id": checkout["id"],
                        "checkout_url": checkout["attributes"]["url"],
                        "expires_at": checkout["attributes"]["expires_at"],
                        "product_type": product_type,
                        "price": price,
                        "currency": "USD"
                    }
                    
                    print(f"✅ Checkout created successfully: {result['checkout_url']}")
                    return result
                else:
                    error_msg = f"LemonSqueezy API error: {response.status_code} - {response.text}"
                    print(f"❌ {error_msg}")
                    raise Exception(error_msg)
                    
        except Exception as e:
            print(f"❌ Error creating checkout: {e}")
            raise Exception(f"Failed to create checkout: {e}")
    
    async def get_checkout_status(self, checkout_id: str) -> Dict:
        """Get checkout status from LemonSqueezy"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_url}/checkouts/{checkout_id}",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Accept": "application/vnd.api+json"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    checkout = data["data"]
                    
                    return {
                        "checkout_id": checkout["id"],
                        "status": checkout["attributes"]["status"],
                        "url": checkout["attributes"]["url"],
                        "expires_at": checkout["attributes"]["expires_at"],
                        "custom_data": checkout["attributes"].get("custom_data", {})
                    }
                else:
                    return {"status": "error", "error": response.text}
                    
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def verify_webhook(self, payload: bytes, signature: str) -> bool:
        """Verify webhook signature from LemonSqueezy"""
        try:
            import hmac
            import hashlib
            
            # LemonSqueezy sends signature as hex HMAC-SHA256
            expected_signature = hmac.new(
                self.webhook_secret.encode(),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected_signature)
            
        except Exception as e:
            print(f"❌ Webhook verification error: {e}")
            return False
    
    async def process_webhook(self, webhook_data: Dict) -> Dict:
        """Process webhook from LemonSqueezy"""
        try:
            event_name = webhook_data.get("meta", {}).get("event_name")
            webhook_id = webhook_data.get("meta", {}).get("webhook_id")
            
            print(f"📨 Processing webhook: {event_name} (ID: {webhook_id})")
            
            if event_name == "order_created":
                return await self._handle_order_created(webhook_data)
            elif event_name == "order_refunded":
                return await self._handle_order_refunded(webhook_data)
            elif event_name == "subscription_created":
                return await self._handle_subscription_created(webhook_data)
            else:
                print(f"⚠️ Unhandled webhook event: {event_name}")
                return {"status": "ignored", "event": event_name}
                
        except Exception as e:
            print(f"❌ Error processing webhook: {e}")
            return {"status": "error", "error": str(e)}
    
    async def _handle_order_created(self, webhook_data: Dict) -> Dict:
        """Handle successful order creation"""
        try:
            order_data = webhook_data["data"]
            order_id = order_data["id"]
            
            attributes = order_data["attributes"]
            customer_email = attributes["user_email"]
            order_number = attributes["order_number"]
            total = attributes["total"]
            currency = attributes["currency"]
            status = attributes["status"]
            
            # Extract custom data
            custom_data = attributes.get("first_order_item", {}).get("custom_data", {})
            product_type = custom_data.get("product_type", "unknown")
            
            print(f"💰 Order created: #{order_number} - {customer_email} - ${total/100:.2f} {currency}")
            print(f"🎵 Product type: {product_type}")
            
            return {
                "status": "processed",
                "order_id": order_id,
                "order_number": order_number,
                "customer_email": customer_email,
                "total": total,
                "currency": currency,
                "product_type": product_type,
                "payment_status": status,
                "custom_data": custom_data
            }
            
        except Exception as e:
            print(f"❌ Error handling order created: {e}")
            return {"status": "error", "error": str(e)}
    
    async def _handle_order_refunded(self, webhook_data: Dict) -> Dict:
        """Handle order refund"""
        try:
            order_data = webhook_data["data"]
            order_id = order_data["id"]
            
            attributes = order_data["attributes"]
            order_number = attributes["order_number"]
            refunded_amount = attributes.get("refunded_amount", 0)
            
            print(f"💸 Order refunded: #{order_number} - ${refunded_amount/100:.2f}")
            
            return {
                "status": "refunded",
                "order_id": order_id,
                "order_number": order_number,
                "refunded_amount": refunded_amount
            }
            
        except Exception as e:
            print(f"❌ Error handling refund: {e}")
            return {"status": "error", "error": str(e)}
    
    async def _handle_subscription_created(self, webhook_data: Dict) -> Dict:
        """Handle subscription creation (for future premium features)"""
        try:
            subscription_data = webhook_data["data"]
            subscription_id = subscription_data["id"]
            
            attributes = subscription_data["attributes"]
            customer_email = attributes["user_email"]
            status = attributes["status"]
            
            print(f"🔄 Subscription created: {subscription_id} - {customer_email} - {status}")
            
            return {
                "status": "subscription_created",
                "subscription_id": subscription_id,
                "customer_email": customer_email,
                "subscription_status": status
            }
            
        except Exception as e:
            print(f"❌ Error handling subscription: {e}")
            return {"status": "error", "error": str(e)}
    
    async def create_customer(self, email: str, name: str = None) -> Dict:
        """Create customer in LemonSqueezy (for future use)"""
        try:
            customer_data = {
                "data": {
                    "type": "customers",
                    "attributes": {
                        "email": email,
                        "name": name or email.split("@")[0]
                    },
                    "relationships": {
                        "store": {
                            "data": {
                                "type": "stores",
                                "id": self.store_id
                            }
                        }
                    }
                }
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/customers",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/vnd.api+json",
                        "Accept": "application/vnd.api+json"
                    },
                    json=customer_data
                )
                
                if response.status_code == 201:
                    data = response.json()
                    customer = data["data"]
                    
                    return {
                        "customer_id": customer["id"],
                        "email": customer["attributes"]["email"],
                        "name": customer["attributes"]["name"]
                    }
                else:
                    print(f"⚠️ Customer creation failed: {response.text}")
                    return {"error": response.text}
                    
        except Exception as e:
            print(f"❌ Error creating customer: {e}")
            return {"error": str(e)}
    
    async def get_order(self, order_id: str) -> Optional[Dict]:
        """Get order details from LemonSqueezy"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_url}/orders/{order_id}",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Accept": "application/vnd.api+json"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    order = data["data"]
                    
                    attributes = order["attributes"]
                    return {
                        "order_id": order["id"],
                        "order_number": attributes["order_number"],
                        "customer_email": attributes["user_email"],
                        "total": attributes["total"],
                        "currency": attributes["currency"],
                        "status": attributes["status"],
                        "created_at": attributes["created_at"],
                        "custom_data": attributes.get("first_order_item", {}).get("custom_data", {})
                    }
                else:
                    print(f"⚠️ Order not found: {order_id}")
                    return None
                    
        except Exception as e:
            print(f"❌ Error getting order: {e}")
            return None 