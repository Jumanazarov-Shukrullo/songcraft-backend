"""Payment manager for handling multiple payment providers with distribution logic"""

import hashlib
from typing import Dict, Optional, Union
from enum import Enum

from ...core.config import settings
from .payment_service import PaymentService
from .dodo_payment_service import DodoPaymentService
from .gumroad_payment_service import GumroadPaymentService


class PaymentProvider(Enum):
    STRIPE = "stripe"
    DODO = "dodo"
    GUMROAD = "gumroad"


class PaymentManager:
    """Manages multiple payment providers with distribution logic"""
    
    def __init__(self):
        self.stripe_service = PaymentService()
        self.dodo_service = DodoPaymentService()
        self.gumroad_service = GumroadPaymentService()
        
    def get_payment_provider_for_user(self, user_id: str) -> PaymentProvider:
        """Determine payment provider for user based on distribution logic"""
        
        # If provider rotation is disabled, use configured provider
        if not settings.ENABLE_PROVIDER_ROTATION:
            provider_name = settings.PAYMENT_PROVIDER.lower()
            if provider_name == "dodo":
                return PaymentProvider.DODO
            elif provider_name == "gumroad":
                return PaymentProvider.GUMROAD
            else:
                return PaymentProvider.STRIPE
        
        # Use user ID hash to deterministically assign provider
        # This ensures the same user always gets the same provider
        user_hash = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
        provider_index = user_hash % 10
        
        # Distribution logic: 1/10 to DoDo, 1/10 to Gumroad, 8/10 to Stripe
        if provider_index == 0:  # 10% DoDo (user_hash % 10 == 0)
            return PaymentProvider.DODO
        elif provider_index == 1:  # 10% Gumroad (user_hash % 10 == 1)
            return PaymentProvider.GUMROAD
        else:  # 80% Stripe (user_hash % 10 in [2,3,4,5,6,7,8,9])
            return PaymentProvider.STRIPE
    
    def get_service_for_provider(self, provider: PaymentProvider) -> Union[PaymentService, DodoPaymentService, GumroadPaymentService]:
        """Get payment service instance for provider"""
        if provider == PaymentProvider.DODO:
            return self.dodo_service
        elif provider == PaymentProvider.GUMROAD:
            return self.gumroad_service
        else:
            return self.stripe_service
    
    async def create_checkout_session(self, 
                                    customer_email: str,
                                    product_type: str,
                                    user_id: str,
                                    custom_data: Dict = None) -> Dict:
        """Create checkout session using appropriate provider"""
        
        # Determine provider for this user
        provider = self.get_payment_provider_for_user(user_id)
        service = self.get_service_for_provider(provider)
        
        print(f"🎯 Selected payment provider: {provider.value} for user {user_id}")
        
        # Add provider info to custom data
        if custom_data is None:
            custom_data = {}
        custom_data["payment_provider"] = provider.value
        custom_data["user_id"] = user_id
        
        # Create checkout session
        result = await service.create_checkout_session(
            customer_email=customer_email,
            product_type=product_type,
            custom_data=custom_data
        )
        
        # Add provider info to result
        result["payment_provider"] = provider.value
        
        return result
    
    async def get_checkout_status(self, checkout_id: str, provider: PaymentProvider = None) -> Dict:
        """Get checkout status from appropriate provider"""
        
        if provider is None:
            # Try to determine provider from checkout_id or try all providers
            # For now, we'll need the provider to be specified
            raise ValueError("Provider must be specified for checkout status check")
        
        service = self.get_service_for_provider(provider)
        return await service.get_checkout_status(checkout_id)
    
    async def process_webhook(self, webhook_data: Dict, provider: PaymentProvider) -> Dict:
        """Process webhook from specified provider"""
        service = self.get_service_for_provider(provider)
        
        result = await service.process_webhook(webhook_data)
        
        # Add provider info to result
        result["payment_provider"] = provider.value
        
        return result
    
    def verify_webhook_signature(self, payload: bytes, signature: str, provider: PaymentProvider) -> bool:
        """Verify webhook signature for specified provider"""
        service = self.get_service_for_provider(provider)
        
        if hasattr(service, 'verify_webhook_signature'):
            return service.verify_webhook_signature(payload, signature)
        
        return True  # Skip verification if not implemented
    
    async def get_payment(self, payment_id: str, provider: PaymentProvider = None) -> Optional[Dict]:
        """Get payment details from appropriate provider"""
        
        if provider is None:
            # Try all providers to find the payment
            for prov in PaymentProvider:
                service = self.get_service_for_provider(prov)
                result = await service.get_payment(payment_id)
                if result is not None:
                    result["payment_provider"] = prov.value
                    return result
            return None
        
        service = self.get_service_for_provider(provider)
        result = await service.get_payment(payment_id)
        
        if result is not None:
            result["payment_provider"] = provider.value
        
        return result
    
    def get_provider_stats(self) -> Dict:
        """Get distribution statistics for debugging"""
        
        if not settings.ENABLE_PROVIDER_ROTATION:
            return {
                "rotation_enabled": False,
                "default_provider": settings.PAYMENT_PROVIDER,
                "distribution": "100% to default provider"
            }
        
        return {
            "rotation_enabled": True,
            "distribution": {
                "stripe": "80% (hash % 10 in [2-9])",
                "dodo": "10% (hash % 10 == 0)",
                "gumroad": "10% (hash % 10 == 1)"
            },
            "hash_method": "MD5 of user_id"
        } 